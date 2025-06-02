from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .db import Base

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    width = Column(String)
    height = Column(String)
    material = Column(String)
    ordered_quantity = Column(String)
    quantity_type = Column(String)
    roll_length = Column(String)
    core = Column(String)
    packaging = Column(String)
    order = relationship("Order", back_populates="items")