"""User schemas - Updated with organization support"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole, UserStatus, UserType, UserPreferences
from app.core.privileges import Privilege


class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None # Added
    job_title: Optional[str] = None  # Added
    bio: Optional[str] = None        # Added
    avatar: Optional[str] = None
    role: UserRole = UserRole.STAFF
    user_type: UserType = UserType.STAFF
    permissions: List[Privilege] = []
    warehouse_access: List[str] = []


class UserCreate(UserBase):
    password: str
    organization_id: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None # Added
    job_title: Optional[str] = None  # Added
    bio: Optional[str] = None        # Added
    avatar: Optional[str] = None
    role: Optional[UserRole] = None
    user_type: Optional[UserType] = None
    permissions: Optional[List[str]] = None
    warehouse_access: Optional[List[str]] = None
    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None
    preferences: Optional[UserPreferences] = None # Added


from beanie import PydanticObjectId

class UserResponse(UserBase):
    id: PydanticObjectId
    organization_id: Optional[str] = None
    status: UserStatus
    is_active: bool
    email_verified: bool
    two_factor_enabled: bool
    preferences: UserPreferences
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserInDB(UserBase):
    id: PydanticObjectId
    organization_id: Optional[str] = None
    hashed_password: str
    is_active: bool
