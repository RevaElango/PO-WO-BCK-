from sqlalchemy import Column, Integer, String, Date, Float, DateTime
from database import Base
from datetime import datetime
from sqlalchemy import Text

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
    email = Column(String(100), nullable=True)
    dated = Column(Date, nullable=True)
    item_description = Column(String)
    quantity = Column(Integer)
    unit_price = Column(Float)
    total_cost = Column(Float)
    delivery_date = Column(Date, nullable=False)
    payment_terms = Column(String, nullable=False)
    additional_terms = Column(String, nullable=True)
    delivery_mode = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
class WorkOrder(Base):
    __tablename__ = "work_order"

    id = Column(Integer, primary_key=True, index=True)
    work_order_no = Column(String(100), nullable=False)
    date = Column(Date, nullable=False)
    quotation_no = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    quotation_date = Column(Date, nullable=False)
    scope_of_work = Column(String, nullable=False)
    value_of_service = Column(Integer, nullable=False)
    tax = Column(Integer, nullable=False)
    duration_of_service = Column(String, nullable=False)
    payment_term = Column(String, nullable=False)
    deliverables = Column(String, nullable=True)        # Optional
    additional_terms = Column(String, nullable=True)     # Optional
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
class AmendmentOrder(Base):
    __tablename__ = "amendment_orders"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    company_name = Column(Text, nullable=False)
    address = Column(Text, nullable=False)
    subject = Column(Text, nullable=False)
    quotation_no = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    dated = Column(Date, nullable=False)
    existing = Column(Text, nullable=False)
    read_as = Column(Text, nullable=False)
    additional_items = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



