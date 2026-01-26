"""Organization schemas"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
from models.organization import OrganizationStatus


class OrganizationBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    location_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    status: OrganizationStatus = OrganizationStatus.ACTIVE
    status: OrganizationStatus = OrganizationStatus.ACTIVE
    subscription_plan_id: Optional[str] = None


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

    status: Optional[OrganizationStatus] = None
    status: Optional[OrganizationStatus] = None
    subscription_plan_id: Optional[str] = None


from beanie import PydanticObjectId

class OrganizationResponse(OrganizationBase):
    id: PydanticObjectId
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
