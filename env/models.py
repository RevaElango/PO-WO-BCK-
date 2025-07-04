from sqlalchemy import Column, Integer, String, Date, Float, DateTime, Boolean, ForeignKey, Text, DECIMAL
from sqlalchemy.orm import relationship
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
    indent_date = Column(Date, nullable=True)  # ✅ Add this
    requester_name = Column(String(100))
    quotation_number = Column(String, nullable=True)
    quotation_date = Column(Date, nullable=True)  # ✅ New field
    email = Column(String(100), nullable=True)
    dated = Column(Date, nullable=True)
    total_cost = Column(Integer)  # 💰 Grand total of all items
    total_including_gst = Column(Float, nullable=False, default=0.0)  # 💡 Add this


    delivery_date = Column(Date, nullable=False)
    payment_terms = Column(String, nullable=False)
    additional_terms = Column(String, nullable=True)
    delivery_mode = Column(String, nullable=False)
    amendment = Column(String(10), default="No")  # or Boolean if preferred
    is_asset = Column(Boolean, default=False)  # ✅ New field for Yes/No
    asset_type = Column(String(100), nullable=True)  # ✅ Show only if is_asset is True
    project_keyword = Column(String, nullable=True)
    prefix = Column(String, nullable=True)
    suffix = Column(String, nullable=True)

    include_annexure = Column(Boolean, default=False)
    annexure_text = Column(String, nullable=True)
    annexure_file_path = Column(String, nullable=True)
    signed_po_path = Column(String(255), nullable=True)
    signed_po_uploaded_at = Column(DateTime, nullable=True)


    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("PurchaseOrderItem", back_populates="po", cascade="all, delete-orphan")
    project_no = Column(String, nullable=True)  # ✅ This is required


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"))

    item_description = Column(String(255), nullable=False)  # ✅ Add length
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Integer, nullable=False)
    item_total = Column(Integer, nullable=False)
    gst = Column(Float, nullable=False, default=0.0)  # ✅ Added GST field

    po = relationship("PurchaseOrder", back_populates="items")


class ProjectNoDetails(Base):
    __tablename__ = "project_no_details"

    id = Column(Integer, primary_key=True, index=True)
    project_keyword = Column(String, nullable=False)
    project_no = Column(String, nullable=False)
    pn_prefix = Column(String, nullable=False)   # updated from project_code
    pn_suffix = Column(String, nullable=False)   # updated from pi_code



class WorkOrder(Base):
    __tablename__ = "work_order"

    id = Column(Integer, primary_key=True, index=True)
    work_order_no = Column(String(100), nullable=False)
    date = Column(Date, nullable=False)
    quotation_no = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    quotation_date = Column(Date, nullable=False)
    requester_name = Column(String(100))
    indent_date = Column(Date, nullable=True)  # ✅ Add this
    scope_of_work = Column(String, nullable=False)
    value_of_service = Column(Integer, nullable=False)
    tax = Column(Integer, nullable=False)
    duration_of_service = Column(String, nullable=False)
    payment_term = Column(String, nullable=False)
    deliverables = Column(String, nullable=True)        # Optional
    additional_terms = Column(String, nullable=True)     # Optional
    amendment = Column(String(10), default="No")  # or Boolean if preferred


    # New fields for Annexure
    supplier_name = Column(String(255))
    address = Column(Text)
    include_annexure = Column(Boolean, default=False)
    annexure_text = Column(String, nullable=True)
    annexure_file_path = Column(String, nullable=True)
     
    project_keyword = Column(String(255), nullable=True)  # ✅ New column
    project_no = Column(String(100), nullable=True)  # ✅ New column to store project number
    signed_wo_path = Column(String(255), nullable=True)
    signed_wo_uploaded_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AmendmentOrder(Base):
    __tablename__ = "amendment_orders"

    id = Column(Integer, primary_key=True, index=True)
    reference_no = Column(String(100), nullable=True)
    date = Column(Date, nullable=False)
    company_name = Column(Text, nullable=False)
    address = Column(Text, nullable=False)
    req_rec_date = Column(Date)  # <-- New field
    subject = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    category_no = Column(String(100), nullable=False)
    category_date = Column(Date, nullable=False)
    email = Column(String(100), nullable=True)
    letter = Column(String(100), nullable=True)
    dated = Column(Date, nullable=False)
    content_text = Column(Text, nullable=False)
    existing = Column(Text, nullable=False)
    read_as = Column(Text, nullable=False)
    additional_items = Column(Text, nullable=True)
    signed_Am_path = Column(String(255), nullable=True)
    signed_Am_uploaded_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    supplier_name = Column(String(255), nullable=False)
    supplier_address = Column(String, nullable=False)
    type = Column(String(100), nullable=True)

class TotalOrder(Base):
    __tablename__ = "total_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    indent_date = Column(Date, nullable=True)
    orders_date = Column(Date, nullable=True)
    email = Column(String(255), nullable=True)
    Item_Description = Column(Text, nullable=True)
    Supplier_Name = Column(String(255), nullable=True)
    Quantity = Column(Integer, nullable=True)
    Total_Cost = Column(DECIMAL(18, 2), nullable=True)
    project_no = Column(String(100), nullable=True)
    Order_No = Column(String(100), nullable=True)
    requestor_name = Column(String(100), nullable=True)
    Payment_Term = Column(String(100), nullable=True)
    signed_po_path = Column(String(255), nullable=True)
    signed_po_uploaded_at = Column(DateTime, nullable=True)
    bp_date = Column(Date, nullable=True)


class UploadedOrder(Base):
    __tablename__ = "uploaded_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(100), nullable=False)
    file_name = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)
    uploaded_on = Column(DateTime, default=datetime.utcnow)
