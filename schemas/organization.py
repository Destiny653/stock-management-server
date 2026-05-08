"""Organization schemas"""
from typing import Optional, Dict, Any
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
    currency: Optional[str] = "CFAF"

    # Frontend-aligned billing fields
    subscription_plan: Optional[str] = None  # plan code
    billing_cycle: Optional[str] = "monthly"  # "monthly" | "yearly"
    trial_ends_at: Optional[datetime] = None
    storage_capacity_kb: Optional[int] = None

    # Backward-compatible naming (older)
    subscription_plan_id: Optional[str] = None
    subscription_interval: Optional[str] = "monthly"

    # Account setup wizard
    setup_completed: Optional[bool] = False
    setup_answers: Optional[Dict[str, Any]] = None


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
    currency: Optional[str] = None

    subscription_plan: Optional[str] = None
    billing_cycle: Optional[str] = None
    trial_ends_at: Optional[datetime] = None
    storage_capacity_kb: Optional[int] = None

    subscription_plan_id: Optional[str] = None
    subscription_interval: Optional[str] = None

    setup_completed: Optional[bool] = None
    setup_answers: Optional[Dict[str, Any]] = None


from beanie import PydanticObjectId

class OrganizationResponse(OrganizationBase):
    id: PydanticObjectId
    setup_completed: bool = False
    setup_answers: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
