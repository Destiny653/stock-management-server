"""StockTransfer model – Tracks inter-location stock transfers across the 6-stage lifecycle."""
from typing import Annotated, Optional, List
from datetime import datetime
from enum import Enum
from beanie import Document, Indexed
from pydantic import Field, BaseModel


class TransferStatus(str, Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    DISPATCHED = "DISPATCHED"
    IN_TRANSIT = "IN_TRANSIT"
    RECEIVED = "RECEIVED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TransferItem(BaseModel):
    product_id: str
    product_name: str
    variant_id: Optional[str] = None
    sku: Optional[str] = None
    qty_requested: int
    qty_dispatched: int = 0
    qty_received: int = 0
    qty_damaged: int = 0
    qty_rejected: int = 0
    unit_cost: float = 0.0
    total_cost: float = 0.0
    notes: Optional[str] = None


class StockTransfer(Document):
    transfer_number: Annotated[str, Indexed(unique=True)]  # e.g., "TRF-2026-0001"
    organization_id: Annotated[str, Indexed()]
    from_location_id: Annotated[str, Indexed()]
    from_location_name: str
    to_location_id: Annotated[str, Indexed()]
    to_location_name: str
    status: TransferStatus = TransferStatus.REQUESTED
    items: List[TransferItem] = Field(default_factory=list)
    
    # User audit tracking
    requested_by_id: Optional[str] = None
    requested_by_name: Optional[str] = None
    approved_by_id: Optional[str] = None
    approved_by_name: Optional[str] = None
    dispatched_by_id: Optional[str] = None
    dispatched_by_name: Optional[str] = None
    received_by_id: Optional[str] = None
    received_by_name: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    dispatched_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    tracking_ref: Optional[str] = None
    carrier_notes: Optional[str] = None
    notes: Optional[str] = None

    class Settings:
        name = "stock_transfers"
