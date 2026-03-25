from typing import List, Optional
from datetime import datetime
from beanie import Document, PydanticObjectId
from pydantic import Field

class SubscriptionPlan(Document):
    name: str
    code: str  # e.g., 'starter', 'business'
    description: Optional[str] = None
    price_monthly: float
    price_yearly: float
    currency: str = "XAF"
    features: List[str] = []
    max_vendors: int
    max_users: int
    max_products: int
    max_locations: int = 10
    storage_capacity_kb: int = 0
    is_popular: bool = False
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "subscription_plans"
