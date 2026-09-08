"""StockMovement model - Inventory movement tracking"""
from typing import Annotated, Optional, List
from datetime import datetime, date
from beanie import Document, Indexed
from pydantic import Field
from enum import Enum


class MovementType(str, Enum):
    RECEIVED = "received"
    DISPATCHED = "dispatched"
    ADJUSTED = "adjusted"
    TRANSFERRED = "transferred"
    RETURNED = "returned"
    STOCK_IN = "stock_in"
    STOCK_OUT = "stock_out"
    CUSTOMER_RETURN = "customer_return"
    SUPPLIER_RETURN = "supplier_return"
    DAMAGED = "damaged"
    EXPIRED = "expired"
    LOST = "lost"
    RESERVATION = "reservation"
    OPENING_STOCK = "opening_stock"
    CLOSING_STOCK = "closing_stock"
    POS_SALE = "pos_sale"
    TRANSFER_DISPATCH = "transfer_dispatch"
    TRANSFER_RECEIPT = "transfer_receipt"
    TRANSFER_DAMAGED = "transfer_damaged"
    PO_RECEIVED = "po_received"


class StockMovement(Document):
    organization_id: Annotated[str, Indexed()]
    product_id: Annotated[str, Indexed()]
    product_name: Optional[str] = None
    variant_id: Optional[str] = None
    sku: Optional[str] = None
    type: MovementType
    quantity: int  # Positive for in, negative for out
    before_quantity: int = 0
    after_quantity: int = 0
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    from_location_id: Optional[str] = None
    to_location_id: Optional[str] = None
    pos_terminal_id: Optional[str] = None
    reference: Optional[str] = None  # PO number, Sale receipt, or transfer ID
    notes: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    serial_numbers: List[str] = Field(default_factory=list)
    unit_cost: float = 0.0
    unit_price: float = 0.0
    total_cost: float = 0.0
    performed_by: Optional[str] = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "stock_movements"

