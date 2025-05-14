from pydantic import BaseModel, field_validator, EmailStr, StringConstraints
from datetime import date, datetime
from typing import Optional
import re
from typing import Annotated

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
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

    @field_validator("supplier_name")
    @classmethod
    def supplier_name_alpha(cls, v):
        if not re.match(r"^[A-Za-z ]+$", v):
            raise ValueError("Supplier name must contain only letters and spaces")
        return v

    @field_validator("po_date")
    @classmethod
    def validate_po_date(cls, v: date):
        today = date.today()
        # Determine current financial year start date
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
