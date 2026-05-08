"""StorefrontOrder model – orders placed through the public storefront"""
from typing import Optional, List, Annotated
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, BaseModel
from enum import Enum


class StorefrontOrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PAID = "paid"
    CANCELLED = "cancelled"


class StorefrontOrderItem(BaseModel):
    product_id: str
    product_name: str
    sku: Optional[str] = None
    variant_label: Optional[str] = None
    quantity: int
    unit_price: float
    total: float
    image_url: Optional[str] = None


class StorefrontOrder(Document):
    organization_id: Annotated[str, Indexed()]
    order_ref: Annotated[str, Indexed(unique=True)]
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: str
    items: List[StorefrontOrderItem] = Field(default_factory=list)
    subtotal: float = 0.0
    total: float = 0.0
    payment_method: str = "mtn"           # "mtn", "orange", or "stripe"
    payment_phone: Optional[str] = None   # org's payment phone used
    ussd_string: Optional[str] = None     # generated USSD
    stripe_client_secret: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    status: StorefrontOrderStatus = StorefrontOrderStatus.PENDING
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "storefront_orders"
