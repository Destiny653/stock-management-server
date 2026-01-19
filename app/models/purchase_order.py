"""PurchaseOrder model - Purchase orders from suppliers"""
from typing import Optional, List
from datetime import datetime, date
from beanie import Document, Indexed
from pydantic import Field, BaseModel
from enum import Enum


class POStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ORDERED = "ordered"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class POItem(BaseModel):
    """Embedded model for PO line items"""
    product_id: str
    sku: Optional[str] = None
    product_name: str
    quantity_ordered: int
    quantity_received: int = 0
    unit_cost: float
    total: float


class PurchaseOrder(Document):
    organization_id: Indexed(str)
    po_number: Indexed(str, unique=True)
    supplier_id: Optional[str] = None
    supplier_name: str
    status: POStatus = POStatus.DRAFT
    items: List[POItem] = []
    subtotal: float = 0.0
    tax: float = 0.0
    shipping: float = 0.0
    total: float = 0.0
    expected_date: Optional[date] = None
    received_date: Optional[date] = None
    notes: Optional[str] = None
    approved_by: Optional[str] = None
    warehouse: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "purchase_orders"
