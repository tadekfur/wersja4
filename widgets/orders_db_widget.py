from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QMessageBox, QSizePolicy, QDialog,
    QAbstractItemView, QToolButton, QFrame
)
from PySide6.QtGui import QFont, QColor, QDesktopServices
from PySide6.QtCore import Qt, QSettings, QUrl
import os

from models.db import Session
from models.client import Client
from models.order import Order
from models.orderitem import OrderItem
from widgets.order_details_dialog import OrderDetailsDialog
from printing.order_confirmation import export_order_to_pdf
from printing.production_ticket import export_production_ticket

class OrdersDBWidget(QWidget):
    SETTINGS_ORG = "twoja_aplikacja"
    SETTINGS_APP = "orders_db_widget"
    SETTINGS_COLUMNS = "column_widths"

    def __init__(self, order_entry_factory, refresh_dashboard_callback=None, show_order_entry_callback=None, main_window=None, parent=None):
        super().__init__(parent)
        self.order_entry_factory = order_entry_factory
        self.refresh_dashboard_callback = refresh_dashboard_callback
        self.show_order_entry_callback = show_order_entry_callback
        self.main_window = main_window
        self.selected_order_id = None

        layout = QVBoxLayout(self)
        title = QLabel("Baza zamówień")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        buttons_row = QHBoxLayout()

        self.button_green = """
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                min-height: 28px;
                border-radius: 7px;
                border: 2px solid #197a3d;
                background: #eaffea;
                color: #197a3d;
                padding: 7px 20px;
                margin: 0 6px;
            }
            QPushButton:disabled {
                background: #f4f4f4;
                color: #a0a0a0;
                border: 2px solid #cccccc;
            }
            QPushButton:pressed {
                background: #c5ffd7;
            }
        """
        self.button_red = self.button_green.replace('#197a3d', '#c60000').replace('#eaffea', '#ffeaea').replace('#c5ffd7', '#ffd2d2')
        self.button_orange = self.button_green.replace('#197a3d', '#d35400').replace('#eaffea', '#fff4e0').replace('#c5ffd7', '#ffe0b2')
        self.button_violet = self.button_green.replace('#197a3d', '#8e44ad').replace('#eaffea', '#f5e6ff').replace('#c5ffd7', '#e0cfff')

        self.button_view = QPushButton("Zobacz zamówienie")
        self.button_view.setStyleSheet(self.button_violet)
        self.button_view.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.button_view.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.button_edit = QPushButton("Edycja zamówienia")
        self.button_edit.setStyleSheet(self.button_green)
        self.button_edit.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.button_edit.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.button_copy = QPushButton("Wystaw jako nowe")
        self.button_copy.setStyleSheet(self.button_orange)
        self.button_copy.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.button_copy.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.button_delete = QPushButton("Usuń")
        self.button_delete.setStyleSheet(self.button_red)
        self.button_delete.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.button_delete.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.button_print = QPushButton("Drukuj wybrane zamówienie")
        self.button_print.setStyleSheet(self.button_green)
        self.button_print.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.button_print.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        for button in (self.button_view, self.button_edit, self.button_copy, self.button_delete, self.button_print):
            button.setEnabled(False)
            button.setMinimumWidth(button.sizeHint().width() + 18)
            buttons_row.addWidget(button)
        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Nr zamówienia", "Data zamówienia", "Data wysyłki",
            "Klient", "Telefon", "Miasto", "Dane produkcji", "Uwagi"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setFont(QFont("Segoe UI", 11))
        self.table.horizontalHeader().setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setStyleSheet("""
            QTableWidget::item:selected {
                background: #409cff;
                color: white;
            }
        """)

        layout.addWidget(self.table, stretch=1)

        self.table.itemSelectionChanged.connect(self.handle_selection)
        self.button_view.clicked.connect(self.view_selected_order)
        self.button_edit.clicked.connect(self.edit_selected_order)
        self.button_copy.clicked.connect(self.copy_selected_order)
        self.button_delete.clicked.connect(self.delete_selected_order)
        self.button_print.clicked.connect(self.show_print_dialog)

        self.setMinimumSize(1200, 700)
        self.resize(1400, 800)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.restore_column_widths()
        self.table.horizontalHeader().sectionResized.connect(self.save_column_widths)

        self.refresh_orders()

        self.button_styles = {
            "green": self.button_green,
            "red": self.button_red,
            "orange": self.button_orange,
            "violet": self.button_violet
        }

    def save_column_widths(self):
        settings = QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)
        widths = [self.table.columnWidth(i) for i in range(self.table.columnCount())]
        settings.setValue(self.SETTINGS_COLUMNS, widths)

    def restore_column_widths(self):
        settings = QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)
        widths = settings.value(self.SETTINGS_COLUMNS)
        if widths and len(widths) == self.table.columnCount():
            for i, width in enumerate(widths):
                try:
                    self.table.setColumnWidth(i, int(width))
                except Exception:
                    pass

    def refresh_orders(self):
        session = Session()
        def safe_order_number(order):
            try:
                return int(order.order_number)
            except Exception:
                return order.order_number or ""
        orders = session.query(Order).all()
        orders = sorted(orders, key=safe_order_number)

        self.table.setRowCount(0)
        for row_index, order in enumerate(orders):
            row = self.table.rowCount()
            self.table.insertRow(row)
            client = session.query(Client).filter_by(id=order.client_id).first()
            items = session.query(OrderItem).filter_by(order_id=order.id).all()
            production_items = [
                (item, index) for index, item in enumerate(items)
                if item.width is not None and str(item.width).strip() != ""
            ]

            order_number_item = QTableWidgetItem(order.order_number or "")
            order_number_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.table.setItem(row, 0, order_number_item)

            order_date_item = QTableWidgetItem(order.order_date.strftime("%Y-%m-%d") if order.order_date else "")
            order_date_item.setFont(QFont("Segoe UI", 10))
            self.table.setItem(row, 1, order_date_item)

            delivery_date_item = QTableWidgetItem(order.delivery_date.strftime("%Y-%m-%d") if order.delivery_date else "")
            delivery_date_item.setFont(QFont("Segoe UI", 10))
            self.table.setItem(row, 2, delivery_date_item)

            client_name_item = QTableWidgetItem(client.name if client else "")
            client_name_item.setFont(QFont("Segoe UI", 10))
            self.table.setItem(row, 3, client_name_item)

            client_phone_item = QTableWidgetItem(client.phone if client else "")
            client_phone_item.setFont(QFont("Segoe UI", 10))
            self.table.setItem(row, 4, client_phone_item)

            client_city_item = QTableWidgetItem(client.city if client else "")
            client_city_item.setFont(QFont("Segoe UI", 10))
            self.table.setItem(row, 5, client_city_item)

            if len(production_items) == 0:
                production_label = QLabel("Brak pozycji")
                production_label.setFont(QFont("Segoe UI", 10))
                self.table.setCellWidget(row, 6, production_label)
                self.table.setRowHeight(row, 28)
            elif len(production_items) == 1:
                item, index = production_items[0]
                production_label = QLabel(
                    f"{item.material}, {item.width}x{item.height} mm, {item.ordered_quantity} {item.quantity_type}, "
                    f"nawój: {item.roll_length}, rdzeń: {item.core}"
                )
                production_label.setFont(QFont("Segoe UI", 10))
                self.table.setCellWidget(row, 6, production_label)
                self.table.setRowHeight(row, 28)
            else:
                production_widget = QWidget()
                production_layout = QVBoxLayout(production_widget)
                production_layout.setContentsMargins(0, 0, 0, 0)
                production_layout.setSpacing(0)

                main_row = QHBoxLayout()
                main_row.setContentsMargins(0, 0, 0, 0)
                main_row.setSpacing(6)
                label_intro = QLabel(
                    f"{production_items[0][0].material}, {production_items[0][0].width}x{production_items[0][0].height} mm, "
                    f"{production_items[0][0].ordered_quantity} {production_items[0][0].quantity_type} ..."
                )
                label_intro.setFont(QFont("Segoe UI", 10))
                main_row.addWidget(label_intro)
                main_row.addStretch(1)
                button = QToolButton()
                button.setText("▼")
                button.setCheckable(True)
                button.setFont(QFont("Segoe UI", 11, QFont.Bold))
                button.setStyleSheet("""
                    QToolButton {
                        border: none;
                        background: transparent;
                        font-size: 16px;
                        min-width: 26px;
                        min-height: 18px;
                    }
                    QToolButton:checked { color: #197a3d; }
                """)
                main_row.addWidget(button)
                production_layout.addLayout(main_row)

                details_widget = QWidget()
                details_layout = QVBoxLayout(details_widget)
                details_layout.setContentsMargins(14, 2, 2, 2)
                details_layout.setSpacing(2)
                for (item, index) in production_items:
                    full_text = (
                        f"{index+1}. {item.material}, {item.width}x{item.height} mm, {item.ordered_quantity} {item.quantity_type}, "
                        f"nawój: {item.roll_length}, rdzeń: {item.core}"
                    )
                    label = QLabel(full_text)
                    label.setFont(QFont("Segoe UI", 10))
                    details_layout.addWidget(label)
                    if index < len(production_items)-1:
                        separator = QFrame()
                        separator.setFrameShape(QFrame.HLine)
                        separator.setFrameShadow(QFrame.Sunken)
                        separator.setStyleSheet("color: #e0e0e0;")
                        details_layout.addWidget(separator)

                details_widget.setVisible(False)
                production_layout.addWidget(details_widget)

                def toggle_details(checked, details_widget_ref, button_ref, table_ref, row_ref):
                    details_widget_ref.setVisible(checked)
                    button_ref.setText("▲" if checked else "▼")
                    base_height = 28
                    if checked:
                        label_count = len(production_items)
                        separator_count = max(0, label_count - 1)
                        label_height = 18
                        separator_height = 6
                        margin = 6
                        total_height = base_height + label_count * label_height + separator_count * separator_height + margin
                        table_ref.setRowHeight(row_ref, total_height)
                    else:
                        table_ref.setRowHeight(row_ref, base_height)
                button.toggled.connect(lambda checked, details_widget_ref=details_widget, button_ref=button, table_ref=self.table, row_ref=row: toggle_details(checked, details_widget_ref, button_ref, table_ref, row_ref))

                def mousePressEvent(event, button_ref=button):
                    if event.button() == Qt.LeftButton and not button_ref.underMouse():
                        button_ref.toggle()
                production_widget.mousePressEvent = mousePressEvent

                self.table.setCellWidget(row, 6, production_widget)
                self.table.setRowHeight(row, 28)

            notes_item = QTableWidgetItem(order.notes or "")
            notes_item.setFont(QFont("Segoe UI", 10))
            self.table.setItem(row, 7, notes_item)

            base_background = "#ffffff" if row_index % 2 == 0 else "#f2f2f2"
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item:
                    item.setBackground(QColor(base_background))
            cell_widget = self.table.cellWidget(row, 6)
            if cell_widget:
                cell_widget.setStyleSheet(f"background: {base_background};")
        session.close()
        self.button_view.setEnabled(False)
        self.button_edit.setEnabled(False)
        self.button_copy.setEnabled(False)
        self.button_delete.setEnabled(False)
        self.button_print.setEnabled(False)
        self.selected_order_id = None
        self.table.clearSelection()
        self.highlight_selected_row()

    def highlight_selected_row(self):
        pass

    def handle_selection(self):
        selected = self.table.selectedItems()
        if not selected:
            self.button_view.setEnabled(False)
            self.button_edit.setEnabled(False)
            self.button_copy.setEnabled(False)
            self.button_delete.setEnabled(False)
            self.button_print.setEnabled(False)
            self.selected_order_id = None
            self.table.clearSelection()
            self.highlight_selected_row()
            return
        row = self.table.currentRow()
        order_number = self.table.item(row, 0).text()
        session = Session()
        order = session.query(Order).filter_by(order_number=order_number).first()
        self.selected_order_id = order.id if order else None
        session.close()
        if self.selected_order_id:
            self.button_view.setEnabled(True)
            self.button_edit.setEnabled(True)
            self.button_copy.setEnabled(True)
            self.button_delete.setEnabled(True)
            self.button_print.setEnabled(True)
        else:
            self.button_view.setEnabled(False)
            self.button_edit.setEnabled(False)
            self.button_copy.setEnabled(False)
            self.button_delete.setEnabled(False)
            self.button_print.setEnabled(False)
        self.highlight_selected_row()

    def get_selected_order(self):
        if not self.selected_order_id:
            return None
        session = Session()
        order = session.query(Order).filter_by(id=self.selected_order_id).first()
        session.close()
        return order

    def view_selected_order(self):
        order = self.get_selected_order()
        if not order:
            return
        self.show_order_dialog_v4(order)

    def edit_selected_order(self):
        order = self.get_selected_order()
        if not order:
            return
        def after_edit():
            self.refresh_orders()
            if self.refresh_dashboard_callback:
                self.refresh_dashboard_callback()
        EditDialog = self._get_edit_dialog_class()
        edit_dialog = EditDialog(self.order_entry_factory, order, after_edit, self.button_styles)
        edit_dialog.exec()

    def _get_edit_dialog_class(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, QScrollArea
        class EditOrderDialog(QDialog):
            def __init__(self, order_entry_factory, order, after_save_callback, button_styles):
                super().__init__()
                self.setWindowTitle("WPROWADŹ DANE ZAMÓWIENIA")
                self.setMinimumSize(1100, 800)
                self.setMaximumSize(1600, 1200)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.setAttribute(Qt.WA_DeleteOnClose)
                layout = QVBoxLayout(self)
                self.setLayout(layout)
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                self.order_widget = order_entry_factory(edit_order=order, after_save_callback=self.accept)
                scroll.setWidget(self.order_widget)
                layout.addWidget(scroll)
                button_row = QHBoxLayout()
                button_row.addStretch(1)
                if hasattr(self.order_widget, "form_layout"):
                    for i in reversed(range(self.order_widget.form_layout.count())):
                        item = self.order_widget.form_layout.itemAt(i)
                        widget = item.widget()
                        if isinstance(widget, QPushButton) and "zapisz" in widget.text().lower():
                            self.save_button = widget
                            self.save_button.setParent(None)
                            self.save_button.setStyleSheet(button_styles["green"])
                            self.save_button.setMinimumWidth(160)
                            button_row.addWidget(self.save_button)
                            self.save_button.clicked.disconnect()
                            self.save_button.clicked.connect(self.save_and_close)
                            break
                    else:
                        self.save_button = QPushButton("💾 Zapisz zamówienie")
                        self.save_button.setStyleSheet(button_styles["green"])
                        self.save_button.setMinimumWidth(160)
                        button_row.addWidget(self.save_button)
                        self.save_button.clicked.connect(self.save_and_close)
                else:
                    self.save_button = QPushButton("💾 Zapisz zamówienie")
                    self.save_button.setStyleSheet(button_styles["green"])
                    self.save_button.setMinimumWidth(160)
                    button_row.addWidget(self.save_button)
                    self.save_button.clicked.connect(self.save_and_close)
                self.cancel_button = QPushButton("Anuluj")
                self.cancel_button.setStyleSheet(button_styles["red"])
                self.cancel_button.setMinimumWidth(120)
                button_row.addWidget(self.cancel_button)
                self.cancel_button.clicked.connect(self.reject)
                layout.addLayout(button_row)
            def save_and_close(self):
                if hasattr(self.order_widget, "save_order"):
                    self.order_widget.save_order()
                self.accept()
        return EditOrderDialog

    def copy_selected_order(self):
        order = self.get_selected_order()
        if not order:
            return
        if self.show_order_entry_callback:
            self.show_order_entry_callback(
                copy_order=order
            )
        else:
            order_widget = self.order_entry_factory(
                copy_order=order
            )
            order_widget.show()

    def _after_save_new_order(self):
        self.refresh_orders()
        if self.refresh_dashboard_callback:
            self.refresh_dashboard_callback()
        if self.main_window:
            self.main_window.switch_page(0, self.main_window.btn_dashboard, "dashboard")

    def delete_selected_order(self):
        order = self.get_selected_order()
        if not order:
            return
        session = Session()
        result = QMessageBox.question(self, "Potwierdź usunięcie", f"Czy na pewno usunąć zamówienie nr {order.order_number}?", QMessageBox.Yes | QMessageBox.No)
        if result != QMessageBox.Yes:
            session.close()
            return
        session.query(OrderItem).filter_by(order_id=order.id).delete()
        session.delete(order)
        session.commit()
        session.close()
        self.refresh_orders()
        if self.refresh_dashboard_callback:
            self.refresh_dashboard_callback()

    def show_order_dialog_v4(self, order):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QGridLayout, QLabel, QHBoxLayout
        session = Session()
        client = session.query(Client).filter_by(id=order.client_id).first()
        items = session.query(OrderItem).filter_by(order_id=order.id).all()
        session.close()
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Podgląd zamówienia {order.order_number}")
        dialog.resize(900, 700)
        layout = QVBoxLayout(dialog)
        groupbox_ordering = QGroupBox("Dane zamawiającego")
        grid = QGridLayout(groupbox_ordering)
        labels = [
            ("Firma:", client.name if client else ""),
            ("Nr klienta:", str(client.client_number) if client else ""),
            ("Osoba kontaktowa:", client.contact_person if client else ""),
            ("Telefon:", client.phone if client else ""),
            ("E-mail:", client.email if client else ""),
            ("Ulica i nr:", client.street if client else ""),
            ("Kod pocztowy:", client.postal_code if client else ""),
            ("Miasto:", client.city if client else ""),
            ("NIP:", client.nip if client else ""),
        ]
        for i, (label, value) in enumerate(labels):
            label_widget = QLabel(label)
            label_widget.setFont(QFont("Segoe UI", 11, QFont.Bold))
            grid.addWidget(label_widget, i, 0)
            value_widget = QLabel(value)
            value_widget.setFont(QFont("Segoe UI", 11))
            grid.addWidget(value_widget, i, 1)
        layout.addWidget(groupbox_ordering)
        groupbox_production = QGroupBox("Dane produkcji")
        production_layout = QVBoxLayout(groupbox_production)
        any_row = False
        for index, item in enumerate(items):
            if not item.width or str(item.width).strip() == "":
                continue
            label = QLabel(
                f"{index+1}. Szer: {item.width} mm, Wys: {item.height} mm, "
                f"Materiał: {item.material}, Ilość: {item.ordered_quantity} {item.quantity_type}, "
                f"Nawój: {item.roll_length}, Rdzeń: {item.core}"
            )
            label.setFont(QFont("Segoe UI", 11))
            production_layout.addWidget(label)
            any_row = True
        if not any_row:
            production_layout.addWidget(QLabel("Brak pozycji z wypełnioną szerokością"))
        layout.addWidget(groupbox_production)
        groupbox_address = QGroupBox("Adres dostawy")
        grid_address = QGridLayout(groupbox_address)
        address_labels = [
            ("Nazwa firmy:", client.delivery_company if client else ""),
            ("Ulica i nr:", client.delivery_street if client else ""),
            ("Kod pocztowy:", client.delivery_postal_code if client else ""),
            ("Miejscowość:", client.delivery_city if client else "")
        ]
        for i, (label, value) in enumerate(address_labels):
            label_widget = QLabel(label)
            label_widget.setFont(QFont("Segoe UI", 11, QFont.Bold))
            grid_address.addWidget(label_widget, i, 0)
            value_widget = QLabel(value)
            value_widget.setFont(QFont("Segoe UI", 11))
            grid_address.addWidget(value_widget, i, 1)
        layout.addWidget(groupbox_address)
        groupbox_notes = QGroupBox("Uwagi do zamówienia")
        notes_layout = QVBoxLayout(groupbox_notes)
        notes = QLabel(order.notes or "")
        notes.setFont(QFont("Segoe UI", 11))
        notes_layout.addWidget(notes)
        layout.addWidget(groupbox_notes)
        dialog.exec()

    def show_print_dialog(self):
        if not self.selected_order_id:
            QMessageBox.warning(self, "Brak zamówienia", "Nie wybrano zamówienia do wydruku.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Wybierz typ wydruku")
        dialog.resize(400, 120)
        layout = QVBoxLayout(dialog)
        info = QLabel("Wybierz rodzaj wydruku PDF:")
        info.setFont(QFont("Segoe UI", 11))
        layout.addWidget(info)
        row = QHBoxLayout()
        button_client = QPushButton("Dla klienta")
        button_production = QPushButton("Produkcja")
        button_client.setFont(QFont("Segoe UI", 12, QFont.Bold))
        button_production.setFont(QFont("Segoe UI", 12, QFont.Bold))
        button_client.setStyleSheet(self.button_green)
        button_production.setStyleSheet(self.button_orange)
        row.addWidget(button_client)
        row.addWidget(button_production)
        layout.addLayout(row)

        def print_for_client_action():
            dialog.accept()
            self.print_for_client()
        def print_for_production_action():
            dialog.accept()
            self.print_for_production()

        button_client.clicked.connect(print_for_client_action)
        button_production.clicked.connect(print_for_production_action)
        dialog.exec()

    def print_for_client(self):
        order = self.get_selected_order()
        if not order:
            QMessageBox.warning(self, "Brak zamówienia", "Nie wybrano zamówienia do wydruku.")
            return
        session = Session()
        client = session.query(Client).filter_by(id=order.client_id).first()
        items = session.query(OrderItem).filter_by(order_id=order.id).all()
        session.close()
        output_dir = r"c:\potwierdzenia dla klienta"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in client.name)
        safe_order = "".join(c for c in str(order.order_number) if c.isalnum() or c in "._-")
        filename = f"{safe_order}_{safe_name}.pdf"
        output_path = os.path.join(output_dir, filename)
        try:
            export_order_to_pdf(order, client, items, output_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_path))
        except Exception as e:
            QMessageBox.critical(self, "Błąd PDF", f"Wystąpił błąd podczas generowania PDF:\n{e}")

    def print_for_production(self):
        order = self.get_selected_order()
        if not order:
            QMessageBox.warning(self, "Brak zamówienia", "Nie wybrano zamówienia do wydruku.")
            return
        session = Session()
        client = session.query(Client).filter_by(id=order.client_id).first()
        items = session.query(OrderItem).filter_by(order_id=order.id).all()
        session.close()
        output_dir = r"c:\produkcja"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in client.name)
        safe_order = "".join(c for c in str(order.order_number) if c.isalnum() or c in "._-")
        filename = f"{safe_order}_{safe_name}_PRODUKCJA.pdf"
        output_path = os.path.join(output_dir, filename)
        try:
            export_production_ticket(order, client, items, output_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_path))
        except Exception as e:
            QMessageBox.critical(self, "Błąd PDF", f"Wystąpił błąd podczas generowania PDF:\n{e}")