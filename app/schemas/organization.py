"""Organization schemas"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.organization import OrganizationStatus, SubscriptionPlan


class OrganizationBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    location_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    status: OrganizationStatus = OrganizationStatus.ACTIVE
    subscription_plan: SubscriptionPlan = SubscriptionPlan.STARTER
    max_vendors: int = 10
    max_users: int = 5


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    status: Optional[OrganizationStatus] = None
    subscription_plan: Optional[SubscriptionPlan] = None
    max_vendors: Optional[int] = None
    max_users: Optional[int] = None


from beanie import PydanticObjectId

class OrganizationResponse(OrganizationBase):
    id: PydanticObjectId
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
