"""Sale model - Sales transactions"""
from typing import Annotated, Optional, List
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, BaseModel
from enum import Enum


class PaymentMethod(str, Enum):
    CASH = "cash"
    MOBILE_MONEY = "mobile_money"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CREDIT = "credit"
    OTHER = "other"


class PaymentStatus(str, Enum):
    PAID = "paid"
    PARTIAL = "partial"
    UNPAID = "unpaid"
    REFUNDED = "refunded"


class SaleStatus(str, Enum):
    COMPLETED = "completed"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"
    VOIDED = "voided"


class SaleItem(BaseModel):
    """Embedded model for sale line items"""
    product_id: str
    product_name: str
    sku: Optional[str] = None
    barcode: Optional[str] = None
    variant_id: Optional[str] = None
    quantity: int
    unit_price: float
    unit_cost: float = 0.0
    discount: float = 0.0
    tax: float = 0.0
    total: float
    cogs: float = 0.0  # Cost of Goods Sold snapshot (quantity * unit_cost)
    image_url: Optional[str] = None


class Sale(Document):
    organization_id: Annotated[str, Indexed()]
    sale_number: Annotated[str, Indexed(unique=True)]
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None
    warehouse_id: Optional[str] = None
    warehouse_name: Optional[str] = None
    items: List[SaleItem] = []
    subtotal: float = 0.0
    tax: float = 0.0
    discount: float = 0.0
    total: float = 0.0
    amount_paid: float = 0.0
    amount_due: float = 0.0
    cogs_total: float = 0.0  # Total cost of goods sold for this sale
    gross_profit: float = 0.0  # total - cogs_total
    payment_method: PaymentMethod = PaymentMethod.CASH
    payment_status: PaymentStatus = PaymentStatus.PAID
    status: SaleStatus = SaleStatus.COMPLETED
    receipt_url: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    billing_address: Optional[str] = None
    cashier_id: Optional[str] = None
    cashier_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "sales"
