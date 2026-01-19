"""Warehouse model - Storage locations"""
from typing import Optional
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field
from enum import Enum


class WarehouseStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class Warehouse(Document):
    organization_id: Indexed(str)
    name: Indexed(str)
    code: str
    location_id: Optional[str] = None
    manager: Optional[str] = None
    capacity: Optional[int] = None
    current_utilization: Optional[float] = None
    status: WarehouseStatus = WarehouseStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "warehouses"
