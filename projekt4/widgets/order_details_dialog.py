from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QScrollArea, QWidget, QGridLayout
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
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        prod_widget = QWidget()
        prod_layout = QVBoxLayout(prod_widget)

        for idx, item in enumerate(order_items, 1):
            if item.width not in (None, '', 0):
                prod_parts = []
                if item.material: prod_parts.append(f"Materiał: {item.material}")
                prod_parts.append(f"Szerokość: {item.width} mm")
                if item.height not in (None, '', 0): prod_parts.append(f"Wysokość: {item.height} mm")
                if item.ordered_quantity: prod_parts.append(f"Ilość: {item.ordered_quantity}")
                if item.quantity_type: prod_parts.append(f"Rodzaj ilości: {item.quantity_type}")
                if item.roll_length: prod_parts.append(f"Nawój: {item.roll_length}")
                if item.core: prod_parts.append(f"Rdzeń: {item.core}")
                if item.packaging: prod_parts.append(f"Pakowanie: {item.packaging}")
                prod_str = f"{idx}.\n" + "\n".join(prod_parts)
                prod_label = QLabel(prod_str)
                prod_label.setWordWrap(True)
                prod_layout.addWidget(prod_label)

        scroll_area.setWidget(prod_widget)
        layout.addWidget(scroll_area)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.resize(650, 400)