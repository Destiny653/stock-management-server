from typing import Optional, List
from beanie import Document
from pydantic import Field
from datetime import datetime

class PlatformSettings(Document):
    support_whatsapp: Optional[str] = None
    support_email: Optional[str] = None
    platform_name: str = "StockFlow"
    default_currency: str = "CFAF"
    allowed_payment_methods: List[str] = Field(default_factory=lambda: [
        "momo",
        "orange-money",
        "visa",
        "mastercard",
        "apple-pay",
        "google-pay",
        "paypal",
    ])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "platform_settings"
