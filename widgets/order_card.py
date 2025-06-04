from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton,
    QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, QByteArray, QDataStream, QIODevice, QMimeData, QPoint
from PySide6.QtGui import QFont, QDrag
from datetime import datetime, date
from models.db import Session
from models.orderitem import OrderItem
from widgets.done_orders_store import done_orders_store
from widgets.order_details_dialog import OrderDetailsDialog

class OrderCard(QFrame):
    def __init__(self, order, dashboard, parent=None):
        super().__init__(parent)
        self.order = order
        self.dashboard = dashboard
        self.details_dialog = None

        today = date.today()
        delivery_date = None
        if hasattr(order, "delivery_date") and order.delivery_date is not None:
            if isinstance(order.delivery_date, datetime):
                delivery_date = order.delivery_date.date()
            elif isinstance(order.delivery_date, date):
                delivery_date = order.delivery_date
            else:
                try:
                    delivery_date = datetime.strptime(str(order.delivery_date), "%Y-%m-%d").date()
                except Exception:
                    delivery_date = None

        days_left = (delivery_date - today).days if delivery_date else None

        def get_gradient_for_shipping_days(days_left):
            if days_left is None:
                return "#e3f2fd", "#ffffff"
            if days_left > 4:
                return "#e0e0e0", "#ffffff"
            elif days_left == 4:
                return "#cccccc", "#ffffff"
            elif days_left == 3:
                return "#b5e7b2", "#ffffff"
            elif days_left == 2:
                return "#b2d7ff", "#ffffff"
            elif days_left == 1:
                return "#ffc966", "#ffffff"
            elif days_left == 0:
                return "#ffe600", "#ffffff"
            else:
                return "#ff6666", "#ffffff"

        grad_start, grad_end = get_gradient_for_shipping_days(days_left)

        self.setFrameShape(QFrame.Box)
        self.setLineWidth(2)
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {grad_start}, stop:1 {grad_end});
                border: 2px solid #7eb7e6;
                border-radius: 4px;
                max-width: 100%;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        client_name = order.client.name if hasattr(order, 'client') and order.client else "—"

        klient_label = QLabel(client_name)
        klient_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        klient_label.setStyleSheet("color: #2574a9")
        klient_label.setWordWrap(True)
        klient_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        nr_label = QLabel(f"Zamówienie: {order.order_number}")
        nr_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        nr_label.setStyleSheet("""
            QLabel {
                background: #111;
                color: #fff;
                border-radius: 3px;
                padding: 2px 12px;
                min-width: 150px;
                font-weight: bold;
            }
        """)
        nr_label.setMinimumWidth(150)
        nr_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        header_row.addWidget(klient_label, stretch=2)
        header_row.addWidget(nr_label, stretch=0)
        header_row.addStretch(1)

        self.arrow_btn = QToolButton()
        self.arrow_btn.setArrowType(Qt.DownArrow)
        self.arrow_btn.setStyleSheet("QToolButton { border: none; font-size:12px; }")
        self.arrow_btn.setCheckable(True)
        self.arrow_btn.setChecked(False)
        self.arrow_btn.clicked.connect(self.toggle_details)
        header_row.addWidget(self.arrow_btn)
        layout.addLayout(header_row)

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

    def _dialog_closed(self):
        self.arrow_btn.setArrowType(Qt.DownArrow)
        self.arrow_btn.setChecked(False)
        self.details_dialog = None

    def toggle_details(self):
        if self.details_dialog and self.details_dialog.isVisible():
            self.details_dialog.close()
        else:
            self.details_dialog = OrderDetailsDialog(self.order, self, close_callback=self._dialog_closed)
            self.details_dialog.show()
            self.details_dialog.raise_()
            self.details_dialog.activateWindow()

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

    def resizeEvent(self, event):
        parent = self.parent()
        if parent:
            self.setMaximumWidth(parent.width())
        super().resizeEvent(event)

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