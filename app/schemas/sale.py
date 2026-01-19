"""Sale schemas"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from app.models.sale import PaymentMethod, SaleStatus, SaleItem


class SaleItemCreate(BaseModel):
    product_id: str
    product_name: str
    sku: Optional[str] = None
    quantity: int
    unit_price: float
    total: float


class SaleBase(BaseModel):
    sale_number: str
    vendor_id: Optional[str] = None
    vendor_name: str
    vendor_email: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    items: List[SaleItemCreate] = []
    subtotal: float = 0.0
    tax: float = 0.0
    discount: float = 0.0
    total: float
    payment_method: PaymentMethod = PaymentMethod.CASH
    status: SaleStatus = SaleStatus.COMPLETED
    notes: Optional[str] = None
    location: Optional[str] = None


class SaleCreate(SaleBase):
    organization_id: str


class SaleUpdate(BaseModel):
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_email: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    items: Optional[List[SaleItemCreate]] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    discount: Optional[float] = None
    total: Optional[float] = None
    payment_method: Optional[PaymentMethod] = None
    status: Optional[SaleStatus] = None
    notes: Optional[str] = None
    location: Optional[str] = None


from beanie import PydanticObjectId

class SaleResponse(SaleBase):
    id: PydanticObjectId
    organization_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
