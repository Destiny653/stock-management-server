"""Organization model - Base entity for multi-tenancy"""
from typing import Optional, List
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, EmailStr
from enum import Enum


class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Organization(Document):
    name: Indexed(str)
    code: Indexed(str, unique=True)
    description: Optional[str] = None
    location_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    status: OrganizationStatus = OrganizationStatus.ACTIVE
    currency: str = "CFAF"

    # Subscription & billing fields (frontend expects these names)
    subscription_plan: Optional[str] = None  # plan code (e.g. starter/business/enterprise)
    billing_cycle: str = "monthly"  # "monthly" | "yearly"
    trial_ends_at: Optional[datetime] = None
    storage_capacity_kb: Optional[int] = None

    # Backward-compatible fields (older naming)
    subscription_plan_id: Optional[str] = None
    subscription_interval: str = "monthly" # monthly, yearly
    max_vendors: int = 10
    max_users: int = 5
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "organizations"
