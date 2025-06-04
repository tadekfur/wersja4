from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QScrollArea, QWidget, QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from models.db import Session
from models.client import Client
from models.orderitem import OrderItem

class OrderDetailsDialog(QDialog):
    def __init__(self, order, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Szczegóły zamówienia: {order.order_number}")
        layout = QVBoxLayout(self)

        font_bold = QFont()
        font_bold.setBold(True)

        grid = QGridLayout()
        row = 0
        grid.addWidget(QLabel("Numer zamówienia:"), row, 0)
        lbl = QLabel(str(order.order_number))
        lbl.setFont(font_bold)
        grid.addWidget(lbl, row, 1)
        row += 1

        grid.addWidget(QLabel("Data zamówienia:"), row, 0)
        grid.addWidget(QLabel(order.order_date.strftime("%Y-%m-%d") if order.order_date else ""), row, 1)
        row += 1

        grid.addWidget(QLabel("Data wysyłki:"), row, 0)
        grid.addWidget(QLabel(order.delivery_date.strftime("%Y-%m-%d") if order.delivery_date else ""), row, 1)
        row += 1

        session = Session()
        client = session.query(Client).filter_by(id=order.client_id).first()
        grid.addWidget(QLabel("Numer klienta:"), row, 0)
        grid.addWidget(QLabel(client.client_number if client else ""), row, 1)
        row += 1

        grid.addWidget(QLabel("Nazwa klienta:"), row, 0)
        grid.addWidget(QLabel(client.name if client else ""), row, 1)
        row += 1

        grid.addWidget(QLabel("Miasto:"), row, 0)
        grid.addWidget(QLabel(client.city if client else ""), row, 1)
        row += 1

        grid.addWidget(QLabel("Osoba kontaktowa:"), row, 0)
        grid.addWidget(QLabel(client.contact_person if client else ""), row, 1)
        row += 1

        grid.addWidget(QLabel("Telefon:"), row, 0)
        grid.addWidget(QLabel(client.phone if client else ""), row, 1)
        row += 1

        grid.addWidget(QLabel("E-mail:"), row, 0)
        grid.addWidget(QLabel(client.email if client else ""), row, 1)
        row += 1

        order_items = session.query(OrderItem).filter_by(order_id=order.id).all()
        session.close()

        prod_label = QLabel("Pozycje zamówienia:")
        prod_label.setFont(font_bold)
        layout.addLayout(grid)
        layout.addWidget(prod_label)

        # TABELA Z POZYCJAMI
        table_headers = ["#", "Materiał", "Wymiar", "Ilość", "Rodzaj", "Nawój", "Rdzeń", "Pakowanie"]
        prod_items = [item for item in order_items if item.width not in (None, '', 0)]
        table = QTableWidget(len(prod_items), len(table_headers))
        table.setHorizontalHeaderLabels(table_headers)
        for row_idx, item in enumerate(prod_items):
            # Numer
            table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx+1)))
            # Materiał
            table.setItem(row_idx, 1, QTableWidgetItem(str(item.material or "")))
            # Wymiar
            wymiar = f"{item.width or ''} x {item.height or ''}" if item.height not in (None, '', 0) else f"{item.width or ''}"
            table.setItem(row_idx, 2, QTableWidgetItem(wymiar.strip()))
            # Ilość
            table.setItem(row_idx, 3, QTableWidgetItem(str(item.ordered_quantity or "")))
            # Rodzaj ilości
            table.setItem(row_idx, 4, QTableWidgetItem(str(item.quantity_type or "")))
            # Nawój
            table.setItem(row_idx, 5, QTableWidgetItem(str(item.roll_length or "")))
            # Rdzeń
            table.setItem(row_idx, 6, QTableWidgetItem(str(item.core or "")))
            # Pakowanie
            table.setItem(row_idx, 7, QTableWidgetItem(str(item.packaging or "")))
        table.verticalHeader().setVisible(False)
        table.setShowGrid(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSizePolicy(QWidget.SizePolicy.Expanding, QWidget.SizePolicy.Fixed)
        table.setStyleSheet("""
            QTableWidget {
                background: #fff;
                border: none;
                color: #111;
            }
            QTableWidget::item {
                background: #fff;
                border: 1px solid #333;
                color: #111;
                padding: 4px 8px;
            }
            QHeaderView::section {
                background: #fff;
                border: 1px solid #333;
                font-weight: bold;
                font-size: 9.5pt;
                color: #111;
            }
        """)
        table.resizeColumnsToContents()
        for i in range(table.columnCount()):
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        table.setMinimumWidth(530)
        table.setFixedHeight(32 + 28 * len(prod_items))
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(table)
        scroll_area.setWidget(table_container)
        layout.addWidget(scroll_area)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        # Automatyczne dopasowanie rozmiaru do zawartości:
        self.adjustSize()
        self.resize(self.sizeHint())
        self.setMinimumSize(self.sizeHint()) 