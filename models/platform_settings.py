from typing import Optional
from beanie import Document
from pydantic import Field
from datetime import datetime

class PlatformSettings(Document):
    support_whatsapp: Optional[str] = None
    support_email: Optional[str] = None
    platform_name: str = "StockFlow"
    default_currency: str = "CFAF"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "platform_settings"
