from pydantic import BaseModel, field_validator, EmailStr, StringConstraints,model_validator
from datetime import date, datetime
from typing import Optional, Annotated
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

class PurchaseOrderBase(BaseModel):
    po_number: str
    po_date: date
    supplier_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    supplier_address: str

    quotation_number: Optional[str] = None
    email: Optional[EmailStr] = None
    dated: Optional[date] = None
    additional_terms: Optional[str] = None

    item_description: str
    quantity: int
    unit_price: float
    total_cost: float
    delivery_date: date
    payment_terms: str
    delivery_mode: str

    # Validation: Supplier name should only contain letters/spaces
    @field_validator("supplier_name")
    @classmethod
    def supplier_name_alpha(cls, v):
        if not re.match(r"^[A-Za-z ]+$", v):
            raise ValueError("Supplier name must contain only letters and spaces")
        return v

    # Validation: PO date must be within current financial year
    @field_validator("po_date")
    @classmethod
    def validate_po_date(cls, v: date):
        today = date.today()
        fy_start = date(today.year - 1, 4, 1) if today.month < 4 else date(today.year, 4, 1)
        if v < fy_start:
            raise ValueError(f"PO date must not be earlier than financial year start: {fy_start}")
        if v > today:
            raise ValueError("PO date cannot be a future date")
        return v


class PurchaseOrderCreate(PurchaseOrderBase):
    pass

class PurchaseOrder(PurchaseOrderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


# ---------------------------
# Work Order Schemas
# ---------------------------

class WorkOrderBase(BaseModel):
    work_order_no: str
    date: date
    quotation_no: Optional[str]
    email: Optional[EmailStr]
    quotation_date: date
    scope_of_work: str
    value_of_service: int
    tax: int
    duration_of_service: str
    payment_term: str
    deliverables: Optional[str] = None
    additional_terms: Optional[str] = None

    # Validation: date should not be in the future
    @field_validator("date")
    @classmethod
    def validate_work_order_date(cls, v: date):
        today = date.today()
        if v > today:
            raise ValueError("Work order date cannot be a future date")
        return v

    # Validation: quotation date should not be in the future
    @field_validator("quotation_date")
    @classmethod
    def validate_quotation_date(cls, v: date):
        today = date.today()
        if v > today:
            raise ValueError("Quotation date cannot be a future date")
        return v

    # Validation: service value and tax must be non-negative
    @field_validator("value_of_service", "tax")
    @classmethod
    def validate_positive_numbers(cls, v: int, info):
        if v < 0:
            raise ValueError(f"{info.field_name.replace('_', ' ').capitalize()} must be a non-negative number")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        return v or None


class WorkOrderCreate(WorkOrderBase):
    pass

class WorkOrder(WorkOrderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }
# ---------------------------
# AM Order (Amendment Order) Schemas
# ---------------------------

class AMOrderBase(BaseModel):
    date: date
    company_name: str
    address: str
    subject: str
    category: str
    category_no: str
    category_date:date
    email: Optional[date] = None  # Changed from EmailStr to date
    letter: Optional[date] = None  # Changed from EmailStr to datesss
    content_text: str
    existing: str
    read_as: str
    additional_items: Optional[str] = None


class AMOrderCreate(AMOrderBase):
    pass

class AMOrder(AMOrderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class DashboardCounts(BaseModel):
    purchase_orders: int
    work_orders: int
    amendment_orders: int
    total_orders: int