from pydantic import BaseModel
from datetime import date, datetime  # Add datetime here
from typing import Optional

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
class PurchaseOrderBase(BaseModel):
    po_number: str
    po_date: date
    supplier_name: str
    supplier_address: str
    quotation_number: Optional[str]
    item_description: str
    quantity: int
    unit_price: float
    total_cost: float
    delivery_date: Optional[date]
    payment_terms: Optional[str]
    delivery_mode: Optional[str]

class PurchaseOrderCreate(PurchaseOrderBase):
    pass

class PurchaseOrder(PurchaseOrderBase):
    id: int
    created_at: Optional[datetime]  # changed from str to datetime
    updated_at: Optional[datetime]  # changed from str to datetime

    class Config:
        orm_mode = True
