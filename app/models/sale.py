"""Sale model - Sales transactions"""
from typing import Optional, List
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, BaseModel
from enum import Enum


class PaymentMethod(str, Enum):
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    OTHER = "other"


class SaleStatus(str, Enum):
    COMPLETED = "completed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class SaleItem(BaseModel):
    """Embedded model for sale line items"""
    product_id: str
    product_name: str
    sku: Optional[str] = None
    quantity: int
    unit_price: float
    total: float


class Sale(Document):
    organization_id: Indexed(str)
    sale_number: Indexed(str, unique=True)
    vendor_id: Optional[str] = None
    vendor_name: str
    vendor_email: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    items: List[SaleItem] = []
    subtotal: float = 0.0
    tax: float = 0.0
    discount: float = 0.0
    total: float
    payment_method: PaymentMethod = PaymentMethod.CASH
    status: SaleStatus = SaleStatus.COMPLETED
    notes: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "sales"
