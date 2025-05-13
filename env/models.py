from sqlalchemy import Column, Integer, String, Date, Float, DateTime
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    password_hash = Column(String(255))  # Using as plain password for now
    created_at = Column(DateTime, default=datetime.utcnow)

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String, index=True)
    po_date = Column(Date)
    supplier_name = Column(String)
    supplier_address = Column(String)
    quotation_number = Column(String, nullable=True)
    item_description = Column(String)
    quantity = Column(Integer)
    unit_price = Column(Float)
    total_cost = Column(Float)
    delivery_date = Column(Date, nullable=True)
    payment_terms = Column(String, nullable=True)
    delivery_mode = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


