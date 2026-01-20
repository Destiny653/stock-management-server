"""Location model for reuse across warehouses, suppliers, etc."""
from typing import Optional
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field

class Location(Document):
    name: Indexed(str)  # Friendly name like "New York Warehouse" or "Main Office"
    address: str
    city: str
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    organization_id: Optional[str] = Field(default=None, description="The organization that owns this location")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "locations"
