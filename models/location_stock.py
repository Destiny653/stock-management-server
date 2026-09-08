"""LocationStock model – Tracks inventory breakdown per product/variant per location."""
from typing import Annotated, Optional
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field


class LocationStock(Document):
    organization_id: Annotated[str, Indexed()]
    location_id: Annotated[str, Indexed()]
    product_id: Annotated[str, Indexed()]
    variant_id: Optional[str] = None
    sku: Optional[str] = None
    product_name: Optional[str] = None
    
    # Inventory bucket quantities
    on_hand: int = Field(default=0, description="Total physical inventory at location")
    available: int = Field(default=0, description="Quantity available for sale or transfer")
    reserved: int = Field(default=0, description="Quantity held for active sales orders/quotes")
    in_transit: int = Field(default=0, description="Quantity dispatched to/from location in transit")
    damaged: int = Field(default=0, description="Quantity damaged/unusable at location")
    expired: int = Field(default=0, description="Quantity past shelf life expiration")
    
    # Thresholds
    reorder_point: Optional[int] = None
    reorder_quantity: Optional[int] = None
    
    unit_cost: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "location_stocks"
