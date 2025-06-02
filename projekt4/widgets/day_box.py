from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QWidget, QLabel, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, QByteArray, QDataStream
from PySide6.QtGui import QFont
from .order_card import OrderCard

class DayBox(QGroupBox):
    def __init__(self, day, dashboard):
        super().__init__()
        self.day = day
        self.dashboard = dashboard
        self.setAcceptDrops(True)
        # Kluczowa zmiana: pozwól boxowi rosnąć w pionie z zawartością
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        weekday_idx = day.weekday()
        WEEKDAYS_PL = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]
        dayname = WEEKDAYS_PL[weekday_idx]
        date_str = day.strftime("%d.%m.%Y")

        week_colors = [
            {"bg": "#e3f6fc", "fg": "#1985a1"},
            {"bg": "#eafbe4", "fg": "#236c29"},
            {"bg": "#fff5dc", "fg": "#a6842e"},
        ]
        week_idx = 0
        if hasattr(dashboard, "get_days"):
            days_all = dashboard.get_days()
            try:
                idx_in_all = [d.strftime("%Y-%m-%d") for d in days_all].index(day.strftime("%Y-%m-%d"))
                week_idx = idx_in_all // 5
            except Exception:
                week_idx = 0
        color = week_colors[week_idx % 3]

        # Szare do białego pionowe cieniowanie tła DayBoxa
        self.setStyleSheet("""
            QGroupBox {
                border: 2px solid #ccc;
                border-radius: 10px;
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e0e0e0, stop:1 #ffffff
                );
                margin-top: 6px;
            }
        """)

        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(4, 4, 4, 4)

        name_label = QLabel(dayname)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet(f"background-color: {color['bg']}; color: {color['fg']}; padding: 4px 0;")
        name_label.setFont(QFont("Segoe UI", 13, QFont.Bold))

        date_label = QLabel(date_str)
        date_label.setAlignment(Qt.AlignCenter)
        date_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        date_label.setStyleSheet(f"background-color: {color['bg']}; color: {color['fg']}; padding-bottom:2px;")

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(header)
        header_layout.addWidget(name_label)
        header_layout.addWidget(date_label)

        self.orders = []
        self.max_orders = 20

        self.orders_container = QWidget(self)
        self.orders_layout = QVBoxLayout(self.orders_container)
        self.orders_layout.setSpacing(10)
        self.orders_layout.setContentsMargins(2, 2, 2, 2)
        self.orders_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.orders_container)
        layout.addStretch(1)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-order-id"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-order-id"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        data = event.mimeData().data("application/x-order-id")
        stream = QDataStream(data)
        order_id = stream.readInt32()
        if len(self.orders) >= self.max_orders:
            reply = QMessageBox.question(self, "Potwierdź",
                f"W tym dniu jest już {self.max_orders} zamówień. Czy dodać kolejne?",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                event.ignore()
                return
        self.dashboard.handle_drop(order_id, self.day)
        event.acceptProposedAction()

    def add_order(self, card):
        self.orders.append(card)
        self.orders_layout.addWidget(card)
        self.orders_container.adjustSize()
        self.adjustSize()
        parent = self.parent()
        if parent:
            parent.adjustSize()

    def clear_orders(self):
        for card in self.orders:
            card.setParent(None)
            card.deleteLater()
        self.orders = []
        self.orders_container.adjustSize()
        self.adjustSize()
        parent = self.parent()
        if parent:
            parent.adjustSize()