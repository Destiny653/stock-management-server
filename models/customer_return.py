"""CustomerReturn model - Customer returns, refunds, and credit notes"""
from typing import Annotated, Optional, List
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, BaseModel
from enum import Enum


class ReturnAction(str, Enum):
    RESTOCK = "restock"
    DAMAGE = "damage"
    DISCARD = "discard"


class CustomerReturnItem(BaseModel):
    product_id: str
    product_name: str
    sku: Optional[str] = None
    quantity: int
    unit_price: float
    refund_amount: float
    action: ReturnAction = ReturnAction.RESTOCK
    reason: Optional[str] = None


class CustomerReturnStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    COMPLETED = "completed"
    REJECTED = "rejected"


class CustomerReturn(Document):
    organization_id: Annotated[str, Indexed()]
    return_number: Annotated[str, Indexed(unique=True)]  # e.g. RET-2026-0001
    sale_id: Optional[str] = None
    sale_number: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    warehouse_id: Optional[str] = None
    items: List[CustomerReturnItem] = Field(default_factory=list)
    total_refund_amount: float = 0.0
    credit_note_number: Optional[str] = None
    status: CustomerReturnStatus = CustomerReturnStatus.COMPLETED
    notes: Optional[str] = None
    processed_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "customer_returns"
