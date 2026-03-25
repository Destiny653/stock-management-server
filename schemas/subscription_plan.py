from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from beanie import PydanticObjectId

class SubscriptionPlanBase(BaseModel):
    name: str
    code: str
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

class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass

class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    price_monthly: Optional[float] = None
    price_yearly: Optional[float] = None
    currency: Optional[str] = None
    features: Optional[List[str]] = None
    max_vendors: Optional[int] = None
    max_users: Optional[int] = None
    max_products: Optional[int] = None
    max_locations: Optional[int] = None
    storage_capacity_kb: Optional[int] = None
    is_popular: Optional[bool] = None
    is_active: Optional[bool] = None

class SubscriptionPlanResponse(SubscriptionPlanBase):
    id: PydanticObjectId
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
