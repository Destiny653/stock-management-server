from typing import Optional
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field

class Category(Document):
    organization_id: Indexed(str)
    name: Indexed(str)
    description: Optional[str] = None
    color: Optional[str] = "#3b82f6"
    icon: Optional[str] = "tag"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "categories"
