"""StockMovement schemas"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from models.stock_movement import MovementType


class StockMovementBase(BaseModel):
    product_id: str
    product_name: Optional[str] = None
    sku: Optional[str] = None
    type: MovementType
    quantity: int
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
    performed_by: Optional[str] = None


class StockMovementCreate(StockMovementBase):
    organization_id: str


from beanie import PydanticObjectId

class StockMovementResponse(StockMovementBase):
    id: PydanticObjectId
    organization_id: str
    created_at: datetime

    class Config:
        from_attributes = True
