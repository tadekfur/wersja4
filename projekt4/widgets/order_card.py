from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton, QMessageBox, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QByteArray, QDataStream, QIODevice, QMimeData, QDate
from PySide6.QtGui import QFont, QDrag
from datetime import datetime, date
from models.db import Session
from models.orderitem import OrderItem
from widgets.done_orders_store import done_orders_store

def get_gradient_for_shipping_days(days_left):
    """
    Returns a (start_color, end_color) tuple for gradient background
    based on number of days to shipping.
    """
    if days_left is None:
        # fallback gradient
        return "#e3f2fd", "#ffffff"

    if days_left > 4:
        # neutral, jasnoszary do białego
        return "#e0e0e0", "#ffffff"
    elif days_left == 4:
        # szary do białego
        return "#cccccc", "#ffffff"
    elif days_left == 3:
        # zielony do białego
        return "#b5e7b2", "#ffffff"
    elif days_left == 2:
        # niebieski do białego
        return "#b2d7ff", "#ffffff"
    elif days_left == 1:
        # pomarańczowy do białego
        return "#ffc966", "#ffffff"
    elif days_left == 0:
        # ostry żółty do białego
        return "#ffe600", "#ffffff"
    else:
        # po terminie - czerwony do białego
        return "#ff6666", "#ffffff"

class OrderCard(QFrame):
    def __init__(self, order, dashboard, parent=None):
        super().__init__(parent)
        self.order = order
        self.dashboard = dashboard

        # Oblicz dni do wysyłki
        today = date.today()
        delivery_date = None
        if hasattr(order, "delivery_date") and order.delivery_date is not None:
            if isinstance(order.delivery_date, datetime):
                delivery_date = order.delivery_date.date()
            elif isinstance(order.delivery_date, date):
                delivery_date = order.delivery_date
            else:
                # fallback (np. string z bazy)
                try:
                    delivery_date = datetime.strptime(str(order.delivery_date), "%Y-%m-%d").date()
                except Exception:
                    delivery_date = None

        days_left = (delivery_date - today).days if delivery_date else None
        grad_start, grad_end = get_gradient_for_shipping_days(days_left)

        # Minimalne zaokrąglenie rogów, gradient tła zależny od dni do wysyłki
        self.setFrameShape(QFrame.Box)
        self.setLineWidth(2)
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {grad_start}, stop:1 {grad_end});
                border: 2px solid #7eb7e6;
                border-radius: 4px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumHeight(60)
        self.setMaximumHeight(150)
        self.setAcceptDrops(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        client_name = order.client.name if hasattr(order, 'client') and order.client else "—"

        # Mniejsza czcionka nazwy firmy
        klient_label = QLabel(client_name)
        klient_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        klient_label.setStyleSheet("color: #2574a9")
        klient_label.setWordWrap(True)
        klient_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Mniejsza czcionka numeru zamówienia, kontrastowy styl
        nr_label = QLabel(f"Zamówienie: {order.order_number}")
        nr_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        nr_label.setStyleSheet("""
            QLabel {
                background: #111;
                color: #fff;
                border-radius: 3px;
                padding: 2px 8px;
                font-weight: bold;
            }
        """)
        nr_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        top_row.addWidget(klient_label, stretch=2)
        top_row.addWidget(nr_label, stretch=1)
        top_row.addStretch(1)

        # Przycis strzałki
        self.arrow_btn = QToolButton()
        self.arrow_btn.setArrowType(Qt.DownArrow)
        self.arrow_btn.setStyleSheet("QToolButton { border: none; font-size:12px; }")
        self.arrow_btn.setCheckable(True)
        self.arrow_btn.setChecked(False)
        self.arrow_btn.clicked.connect(self.toggle_details)
        top_row.addWidget(self.arrow_btn)
        layout.addLayout(top_row)

        self.details = QWidget()
        details_layout = QVBoxLayout(self.details)
        details_layout.setContentsMargins(2, 2, 2, 2)
        details_layout.setSpacing(4)
        session = Session()
        items = session.query(OrderItem).filter_by(order_id=order.id).all()
        session.close()
        displayed_any = False
        if items:
            for idx, item in enumerate(items):
                if item.width is not None and str(item.width).strip() != "":
                    width_height_str = ""
                    if item.width is not None and item.height is not None:
                        width_height_str = f"{item.width} x {item.height}"
                    elif item.width is not None:
                        width_height_str = f"{item.width}"
                    elif item.height is not None:
                        width_height_str = f"x {item.height}"

                    prod_line = QLabel(
                        f"{idx+1}. {item.material}, {width_height_str} mm, {item.ordered_quantity} {item.quantity_type}, "
                        f"nawój: {item.roll_length}, rdzeń: {item.core}, pakowanie: {item.packaging}"
                    )
                    prod_line.setFont(QFont("Segoe UI", 8))
                    prod_line.setWordWrap(True)
                    prod_line.setStyleSheet("color:#444; padding:2px 0;")
                    prod_line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                    details_layout.addWidget(prod_line)
                    displayed_any = True
        if not displayed_any:
            prod_line = QLabel("Brak pozycji produkcyjnych")
            font = QFont("Segoe UI", 8)
            font.setItalic(True)
            prod_line.setFont(font)
            prod_line.setStyleSheet("color:#888;")
            details_layout.addWidget(prod_line)
        self.details.setVisible(False)
        layout.addWidget(self.details)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.done_btn = QPushButton("zrobione")
        self.done_btn.setStyleSheet("background:#2bbd5c; color:white; font-weight:bold; border-radius:7px; padding:3px 10px; font-size:10px;")
        self.done_btn.setMinimumWidth(80)
        btn_row.addWidget(self.done_btn)
        self.done_btn.clicked.connect(self.remove_from_dashboard)
        self.restore_btn = None
        if hasattr(dashboard, "show_done_checkbox") and dashboard.show_done_checkbox and dashboard.show_done_checkbox.isChecked():
            self.restore_btn = QPushButton("Przywróć")
            self.restore_btn.setStyleSheet("background:#eebb22; color:white; font-weight:bold; border-radius:7px; padding:3px 10px; font-size:10px;")
            self.restore_btn.setMinimumWidth(80)
            btn_row.addWidget(self.restore_btn)
            self.restore_btn.clicked.connect(self.restore_to_dashboard)
        layout.addLayout(btn_row)
        self.setMouseTracking(True)

    def remove_from_dashboard(self):
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy chcesz oznaczyć to zamówienie jako zrobione i usunąć z tablicy głównej?\n\nNr: {self.order.order_number}\nKlient: {self.order.client.name if self.order.client else ''}",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            done_orders_store.mark_done(self.order.id)
            self.dashboard.refresh_cards()

    def restore_to_dashboard(self):
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy chcesz przywrócić to zamówienie na tablicę główną?\n\nNr: {self.order.order_number}\nKlient: {self.order.client.name if self.order.client else ''}",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            done_orders_store.remove(self.order.id)
            self.dashboard.refresh_cards()

    def toggle_details(self):
        expanded = self.arrow_btn.isChecked()
        if expanded:
            self.arrow_btn.setArrowType(Qt.UpArrow)
        else:
            self.arrow_btn.setArrowType(Qt.DownArrow)
        self.details.setVisible(expanded)
        parent = self.parent()
        while parent and not hasattr(parent, "orders_container"):
            parent = parent.parent()
        if parent:
            parent.orders_container.adjustSize()
            parent.adjustSize()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.position() if hasattr(event, 'position') else event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            curr_pos = event.position() if hasattr(event, 'position') else event.pos()
            if (curr_pos - self._drag_start_pos).manhattanLength() > 5:
                drag = QDrag(self)
                data = QByteArray()
                stream = QDataStream(data, QIODevice.WriteOnly)
                stream.writeInt32(self.order.id)
                mime = QMimeData()
                mime.setData("application/x-order-id", data)
                drag.setMimeData(mime)
                drag.exec(Qt.MoveAction)
        super().mouseMoveEvent(event)