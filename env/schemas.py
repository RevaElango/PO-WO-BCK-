from pydantic import BaseModel, EmailStr, field_validator
from datetime import date, datetime
from typing import List, Optional
import re

# ---------------------------
# User Authentication Schemas
# ---------------------------

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------
# Purchase Order Schemas
# ---------------------------

class PurchaseOrderItemCreate(BaseModel):
    item_description: str
    quantity: int
    unit_price: int
    item_total: int
    gst: float  # ✅ Added GST as mandatory

class PurchaseOrderItem(PurchaseOrderItemCreate):
    id: int

    class Config:
        orm_mode = True

class PurchaseOrderCreate(BaseModel):
    po_number: str
    po_date: date
    supplier_name: str
    supplier_address: str
    indent_date: date
    requester_name: str
    quotation_number: Optional[str] = None
    quotation_date: Optional[date] = None  # Optional if needed
    email: Optional[str] = None
    created_by: str
    dated: Optional[date] = None
    total_cost: int
    total_including_gst: float  # 💡 Add this
    delivery_date: date
    payment_terms: str
    additional_terms: Optional[str] = None
    delivery_mode: str
    signed_po_path :Optional[str] = None
    signed_po_uploaded_at: Optional[datetime] = None
    is_asset: Optional[bool] = False
    asset_type: Optional[str] = None
    project_keyword: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    include_annexure: bool = False
    annexure_text: Optional[str] = None
    annexure_file_path: Optional[str] = None
    items: List[PurchaseOrderItemCreate]  # ✅ Make sure this comes *after* the class is defined
    preview_file_path: Optional[str] = None


    @field_validator("supplier_name", check_fields=False)
    @classmethod
    def supplier_name_valid(cls, v):
        # Allow letters, spaces, dots, hyphens, commas, ampersands
        if not re.match(r"^[A-Za-z0-9 .,&-]+$", v):
            raise ValueError("Supplier name must contain only letters, numbers, spaces, dots, commas, ampersands, and hyphens")
        return v

    @field_validator("po_date", check_fields=False)
    @classmethod
    def validate_po_date(cls, v: date):
        today = date.today()
        fy_start = date(today.year - 1, 4, 1) if today.month < 4 else date(today.year, 4, 1)
        if v < fy_start:
            raise ValueError(f"PO date must not be earlier than financial year start: {fy_start}")
        if v > today:
            raise ValueError("PO date cannot be a future date")
        return v

class PurchaseOrderItem(BaseModel):
    id: int
    item_description: str
    quantity: int
    unit_price: int
    item_total: int
    gst: float  # ✅ Added GST field here as well

    class Config:
        orm_mode = True


class PurchaseOrder(BaseModel):
    id: int
    po_number: str
    po_date: Optional[date]
    supplier_name: Optional[str]
    supplier_address: Optional[str]
    quotation_number: Optional[str]
    quotation_date: Optional[date]
    email: Optional[str]
    created_by: Optional[str]
    dated: Optional[date]
    additional_terms: Optional[str]
    delivery_date: Optional[date]
    payment_terms: Optional[str]
    delivery_mode: Optional[str]
    total_cost: int
    signed_po_path: Optional[str]
    items: List[PurchaseOrderItem]
    created_at: datetime
    updated_at: datetime
    preview_file_path: Optional[str]
    class Config:
        orm_mode = True



# ---------------------------
# Work Order Schemas
# ---------------------------

class WorkOrderBase(BaseModel):
    work_order_no: str
    date: date
    quotation_no: Optional[str]
    email: Optional[EmailStr]
    quotation_date: date
    requester_name: str
    indent_date: date
    scope_of_work: str
    value_of_service: int
    tax: int
    duration_of_service: str
    payment_term: str
    supplier_name: str
    address: str
    deliverables: Optional[str] = None
    additional_terms: Optional[str] = None
    include_annexure: Optional[bool] = False
    annexure_text: Optional[str] = None
    annexure_file_path: Optional[str] = None
    signed_wo_path :Optional[str] = None
    signed_wo_uploaded_at: Optional[datetime] = None # ✅ Correct type
    project_keyword: Optional[str] = None  # ✅ New field
    preview_file_path: Optional[str] = None
 
    @field_validator("date", check_fields=False)
    @classmethod
    def validate_work_order_date(cls, v: date):
        if v > date.today():
            raise ValueError("Work order date cannot be a future date")
        return v

    @field_validator("quotation_date", check_fields=False)
    @classmethod
    def validate_quotation_date(cls, v: date):
        if v > date.today():
            raise ValueError("Quotation date cannot be a future date")
        return v

    @field_validator("value_of_service", "tax", check_fields=False)
    @classmethod
    def validate_positive_numbers(cls, v: int, info):
        if v < 0:
            raise ValueError(f"{info.field_name.replace('_', ' ').capitalize()} must be a non-negative number")
        return v

    @field_validator("email", mode="before", check_fields=False)
    @classmethod
    def empty_string_to_none(cls, v):
        return v or None

class WorkOrderCreate(WorkOrderBase):
    created_by: str  # ✅ Add this line
    pass

class WorkOrder(WorkOrderBase):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
 
    class Config:
        orm_mode = True


# ---------------------------
# AM Order (Amendment Order) Schemas
# ---------------------------

class AMOrderBase(BaseModel):
    reference_no: str
    date: date
    company_name: str
    address: str
    req_rec_date: date
    subject: str
    category: str
    category_no: str
    category_date: date
    email: Optional[date] = None  # <-- Change only if really needed (should usually be EmailStr)
    letter: Optional[date] = None
    content_text: str
    existing: str
    read_as: str
    additional_items: Optional[str] = None
    signed_Am_path :Optional[str] = None
    signed_Am_uploaded_at: Optional[datetime] = None # ✅ Correct type

class AMOrderCreate(AMOrderBase):
    pass

class AMOrder(AMOrderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# ---------------------------
# Dashboard
# ---------------------------

class DashboardCounts(BaseModel):
    purchase_orders: int
    work_orders: int
    amendment_orders: int
    total_orders: int

class TotalOrder(BaseModel):
    id: int
    indent_date: Optional[date]
    orders_date: Optional[date]
    created_by: Optional[str]
    Item_Description: Optional[str]
    Supplier_Name: Optional[str]
    Quantity: Optional[int]
    Total_Cost: Optional[float]
    project_no: Optional[str]
    Order_No: Optional[str]
    requestor_name: Optional[str]
    Payment_Term: Optional[str]

    signed_po_path: Optional[str]
    signed_po_uploaded_at: Optional[datetime]
    bp_date: Optional[date]
    preview_files: Optional[str]
 
    class Config:
        orm_mode = True
