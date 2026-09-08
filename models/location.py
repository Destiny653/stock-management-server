"""Unified Location model for Stores, Warehouses, Branches, and Distribution Centers."""
from typing import Annotated, Optional
from datetime import datetime
from enum import Enum
from beanie import Document, Indexed
from pydantic import Field


class LocationType(str, Enum):
    STORE = "store"
    WAREHOUSE = "warehouse"
    BRANCH = "branch"
    DISTRIBUTION_CENTER = "distribution_center"
    FULFILLMENT_CENTER = "fulfillment_center"
    OFFICE = "office"
    OTHER = "other"


class LocationStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class Location(Document):
    organization_id: Annotated[str, Indexed()]
    name: Annotated[str, Indexed()]  # e.g. "Douala Main Warehouse" or "Yaoundé Store #1"
    code: Optional[Annotated[str, Indexed()]] = None  # e.g. "LOC-DLA-01"
    type: LocationType = Field(default=LocationType.STORE, description="Location type (store, warehouse, branch, distribution_center, etc.)")
    status: LocationStatus = Field(default=LocationStatus.ACTIVE)
    address: str = ""
    city: str = ""
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "Cameroon"
    phone: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    manager_id: Optional[str] = Field(default=None, description="Assigned Manager user ID")
    manager_name: Optional[str] = None
    is_central_hub: bool = False
    allow_pos: bool = Field(default=True, description="True if POS terminals can operate against this location")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "locations"
