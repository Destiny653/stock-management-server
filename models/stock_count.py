"""StockCount model - Physical inventory count and variance audit model"""
from typing import Annotated, Optional, List
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, BaseModel
from enum import Enum


class StockCountStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class StockCountItem(BaseModel):
    product_id: str
    product_name: str
    sku: Optional[str] = None
    barcode: Optional[str] = None
    system_quantity: int
    counted_quantity: int
    variance: int  # counted_quantity - system_quantity
    unit_cost: float = 0.0
    variance_value: float = 0.0  # variance * unit_cost
    notes: Optional[str] = None


class StockCount(Document):
    organization_id: Annotated[str, Indexed()]
    count_number: Annotated[str, Indexed(unique=True)]  # e.g., STK-CNT-2026-001
    warehouse_id: Optional[str] = None
    warehouse_name: Optional[str] = None
    status: StockCountStatus = StockCountStatus.DRAFT
    items: List[StockCountItem] = Field(default_factory=list)
    total_system_qty: int = 0
    total_counted_qty: int = 0
    total_variance_qty: int = 0
    total_variance_value: float = 0.0
    created_by_id: Optional[str] = None
    created_by_name: Optional[str] = None
    approved_by_id: Optional[str] = None
    approved_by_name: Optional[str] = None
    notes: Optional[str] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "stock_counts"
