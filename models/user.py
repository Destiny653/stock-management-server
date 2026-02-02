"""User model - Updated with organization_id for multi-tenancy"""
from typing import Optional, List, Dict
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, EmailStr, BaseModel
from enum import Enum
from core.privileges import Privilege


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    VENDOR = "vendor"
    USER = "user"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class UserType(str, Enum):
    PLATFORM_STAFF = "platform-staff"
    BUSINESS_STAFF = "business-staff"
    STAFF = "staff"


class NotificationPreferences(BaseModel):
    email: bool = True
    sms: bool = False
    push: bool = True
    low_stock_alerts: bool = True
    order_updates: bool = True
    weekly_reports: bool = True


class UserPreferences(BaseModel):
    language: str = "en"
    timezone: str = "UTC"
    notifications: NotificationPreferences = NotificationPreferences()
    dark_mode: bool = False
    compact_view: bool = False


class User(Document):
    organization_id: Optional[Indexed(str)] = None
    email: Indexed(EmailStr, unique=True)
    username: Indexed(str, unique=True)
    hashed_password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None  # Added
    job_title: Optional[str] = None   # Added
    bio: Optional[str] = None         # Added
    avatar: Optional[str] = None
    role: UserRole = UserRole.USER
    user_type: UserType = UserType.BUSINESS_STAFF
    permissions: List[Privilege] = []
    warehouse_access: List[str] = []  # IDs of warehouses user can access
    status: UserStatus = UserStatus.PENDING
    is_active: bool = True
    last_login: Optional[datetime] = None
    email_verified: bool = False
    two_factor_enabled: bool = False
    preferences: UserPreferences = UserPreferences()
    invited_by: Optional[str] = None
    invited_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
