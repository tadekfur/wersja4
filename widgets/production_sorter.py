from collections import defaultdict
from models.order import Order
from models.orderitem import OrderItem
from models.db import Session

def get_weekly_production_summary(start_date=None, end_date=None):
    session = Session()
    query = session.query(Order, OrderItem).join(OrderItem, Order.id == OrderItem.order_id)
    if start_date:
        query = query.filter(Order.delivery_date >= start_date)
    if end_date:
        query = query.filter(Order.delivery_date <= end_date)

    summary = defaultdict(float)
    for order, item in query.all():
        week = order.delivery_date.isocalendar()[1]
        material = item.material
        width = item.width
        height = item.height

        qty = 0.0
        try:
            if item.quantity_type and item.quantity_type.lower().startswith('ty'):
                # typ tyś – liczymy 1:1
                qty = float(item.ordered_quantity)
            elif item.quantity_type and item.quantity_type.lower().startswith('rol'):
                # typ rolki – przeliczamy ilość rolek * nawój / 1000
                rolls = float(item.ordered_quantity)
                roll_length = float(item.roll_length)
                qty = rolls * roll_length / 1000.0
            else:
                # fallback - liczymy 1:1
                qty = float(item.ordered_quantity)
        except Exception:
            qty = 0.0

        key = (week, material, width, height)
        summary[key] += qty

    session.close()
    result = sorted(summary.items(), key=lambda x: (x[0][0], x[0][1], float(x[0][2]), float(x[0][3])))
    return result