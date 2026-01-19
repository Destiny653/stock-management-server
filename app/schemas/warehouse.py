"""Warehouse schemas"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.warehouse import WarehouseStatus


class WarehouseBase(BaseModel):
    name: str
    code: str
    location_id: Optional[str] = None
    manager: Optional[str] = None
    capacity: Optional[int] = None
    current_utilization: Optional[float] = None
    status: WarehouseStatus = WarehouseStatus.ACTIVE


class WarehouseCreate(WarehouseBase):
    organization_id: str


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    location_id: Optional[str] = None
    manager: Optional[str] = None
    capacity: Optional[int] = None
    current_utilization: Optional[float] = None
    status: Optional[WarehouseStatus] = None


from beanie import PydanticObjectId

class WarehouseResponse(WarehouseBase):
    id: PydanticObjectId
    organization_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
