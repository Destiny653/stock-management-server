"""Sale schemas"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from models.sale import PaymentMethod, SaleStatus


class SaleItemCreate(BaseModel):
    product_id: str
    product_name: str
    sku: Optional[str] = None
    barcode: Optional[str] = None
    variant_id: Optional[str] = None
    quantity: int
    unit_price: float
    discount: float = 0.0
    tax: float = 0.0
    total: float
    image_url: Optional[str] = None


class SaleBase(BaseModel):
    sale_number: Optional[str] = None
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = "POS Cashier"
    vendor_email: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = "Walk-in Customer"
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    items: List[SaleItemCreate] = []
    subtotal: float = 0.0
    tax: float = 0.0
    discount: float = 0.0
    total: float = 0.0
    payment_method: PaymentMethod = PaymentMethod.CASH
    status: SaleStatus = SaleStatus.COMPLETED
    notes: Optional[str] = None
    location: Optional[str] = None


class SaleCreate(SaleBase):
    organization_id: Optional[str] = None


class SaleUpdate(BaseModel):
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_email: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
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
