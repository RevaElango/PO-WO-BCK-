from pydantic import BaseModel, EmailStr, field_validator,ConfigDict,condecimal,Field
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional, Union
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

class PurchaseOrderItemBase(BaseModel):
    item_description: str
    quantity: int
    unit_price: condecimal(max_digits=18, decimal_places=3)  # ✅ correct
    item_total: condecimal(max_digits=18, decimal_places=2)
    gst: condecimal(max_digits=5, decimal_places=2)

class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    pass

class PurchaseOrderItem(PurchaseOrderItemBase):
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
    quotation_date: Optional[date] = None
    email: Optional[str] = None
    created_by: str
    dated: Optional[date] = None
    total_cost: condecimal(max_digits=12, decimal_places=2)
    total_including_gst: condecimal(max_digits=12, decimal_places=2)
    delivery_date: date
    payment_terms: str
    additional_terms: Optional[str] = None
    delivery_mode: str
    signed_po_path: Optional[str] = None
    signed_po_uploaded_at: Optional[datetime] = None
    is_asset: Optional[bool] = False
    asset_type: Optional[str] = None
    project_keyword: Optional[str] = None

    budget_head: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    final_suffix: str  # ✅ Add this
    include_annexure: bool = False
    annexure_text: Optional[str] = None
    annexure_file_path: Optional[str] = None
    preview_file_path: Optional[str] = None
    items: List[PurchaseOrderItemCreate]

    class Config:
        orm_mode = True


class PurchaseOrder(PurchaseOrderCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    items: List[PurchaseOrderItem]  # override to include item IDs

    class Config:
        orm_mode = True



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
    unit_price: Decimal
    item_total: Decimal
    gst: float  # ✅ Added GST field here as well

    class Config:
        orm_mode = True


class PurchaseOrder(BaseModel):
    id: int
    po_number: str
    prefix: Optional[str]  # ✅ Add this
    suffix: Optional[str]  # ✅ Add this
    project_keyword: Optional[str]  # ✅ Add this
    project_no: Optional[str] 
    requester_name: Optional[str]  # ✅ Add this
    indent_date: Optional[date]
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
    total_cost: Union[int, float]
    total_including_gst: Optional[float] 
    signed_po_path: Optional[str]
    signed_po_uploaded_at: Optional[datetime]
    include_annexure: Optional[bool]
    annexure_text: Optional[str]
    annexure_file_path: Optional[str]
    is_asset: Optional[bool]
    asset_type: Optional[str]
    preview_file_path: Optional[str]
    created_at: datetime
    updated_at: datetime
    budget_head: Optional[str] 
    items: List[PurchaseOrderItem]

    class Config:
        orm_mode = True
# ---------------------------
# Work Order Item Schemas
# ---------------------------

class WorkOrderItemBase(BaseModel):
    item_description: str
    quantity: int
    # Prefer Decimal for currency; 2 decimal places
    unit_price: condecimal(max_digits=12, decimal_places=2)
    item_total: condecimal(max_digits=12, decimal_places=2)
    gst: condecimal(max_digits=5, decimal_places=2)  # e.g., 18.00

class WorkOrderItemCreate(WorkOrderItemBase):
    pass

class WorkOrderItem(WorkOrderItemBase):
    id: int
    model_config = ConfigDict(from_attributes=True)  # Pydantic v2 equivalent of orm_mode

# ---- Work Order ----
class WorkOrderBase(BaseModel):
    work_order_no: str
    date: date
    quotation_no: Optional[str]
    email: Optional[EmailStr]
    quotation_date: Optional[date] = None
    requester_name: str
    indent_date: date

    # If you've removed these in the UI/DB, you can delete these lines.
    # Keeping them optional avoids 422s if not sent.
    scope_of_work: Optional[str] = None
    value_of_service: Optional[condecimal(max_digits=14, decimal_places=2)] = Field(default=Decimal("0"))

    # Totals/tax
    tax: str | None = None 
    total_cost: condecimal(max_digits=14, decimal_places=2) = Field(default=Decimal("0"))
    total_including_gst: condecimal(max_digits=14, decimal_places=2) = Field(default=Decimal("0"))

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
    project_no: Optional[str] = None
    budget_head: Optional[str] = None
    preview_file_path: Optional[str] = None
    items: List[WorkOrderItemCreate]

    @field_validator("date")
    @classmethod
    def validate_work_order_date(cls, v: date):
        if v > date.today():
            raise ValueError("Work order date cannot be a future date")
        return v

    @field_validator("quotation_date")
    @classmethod
    def validate_quotation_date(cls, v: Optional[date]):
        if v is not None and v > date.today():
            raise ValueError("Quotation date cannot be in the future.")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        return v or None

class WorkOrderCreate(WorkOrderBase):
    created_by: str

class WorkOrder(WorkOrderBase):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    items: List[WorkOrderItem]
    model_config = ConfigDict(from_attributes=True)  # Pydantic v2

# AM Order (Amendment Order) Schemas
# ---------------------------

class AMOrderBase(BaseModel):
    amendment_no: Optional[str] = None
    reference_no: str
    reference_type: Optional[str]
    date: date
    company_name: str
    address: str
    req_rec_date: date
    subject: str
    # category: str
    # category_no: str
    category_date: date
    email: Optional[date] = None  # <-- Change only if really needed (should usually be EmailStr)
    # letter: Optional[date] = None
    content_text: str
    # existing: str
    read_as: str
    created_by: str
    preview_file_path: Optional[str] = None
    # additional_items: Optional[str] = None
    signed_Am_path :Optional[str] = None
    signed_Am_uploaded_at: Optional[datetime] = None # ✅ Correct type
    bp_date: Optional[date] = None


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
    Quantity: Optional[str]
    Total_Cost: Optional[float]
    project_no: Optional[str]
    Order_No: Optional[str]
    requestor_name: Optional[str]
    Payment_Term: Optional[str]
    budget_head: Optional[str]
    signed_po_path: Optional[str]
    signed_po_uploaded_at: Optional[datetime]
    bp_date: Optional[date]
    preview_files: Optional[str]
    order_type: Optional[str]
    amendment_no: Optional[str]
    project_keyword: Optional[str]
 
    class Config:
        orm_mode = True

class SupplierCreate(BaseModel):
    supplier_name: str
    supplier_address: str



class ProjectNoCreate(BaseModel):
    project_no: str
    project_keyword: str
    pn_prefix: str
    pn_suffix: str

class ProjectNoResponse(ProjectNoCreate):
    id: int

    class Config:
        from_attributes = True  # Pydantic v2

class ProjectNoCreateResponse(BaseModel):
    message: str
    data: ProjectNoResponse

    class Config:
        from_attributes = True  # Pydantic v2
