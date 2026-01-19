"""StockMovement model - Inventory movement tracking"""
from typing import Optional
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field
from enum import Enum


class MovementType(str, Enum):
    RECEIVED = "received"
    DISPATCHED = "dispatched"
    ADJUSTED = "adjusted"
    TRANSFERRED = "transferred"
    RETURNED = "returned"


class StockMovement(Document):
    organization_id: Indexed(str)
    product_id: Indexed(str)
    product_name: Optional[str] = None
    sku: Optional[str] = None
    type: MovementType
    quantity: int  # Positive for in, negative for out
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    reference: Optional[str] = None  # PO number or reference
    notes: Optional[str] = None
    performed_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "stock_movements"
