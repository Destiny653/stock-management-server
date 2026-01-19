"""Vendor model - Vendors who sell products"""
from typing import Optional
from datetime import datetime, date
from beanie import Document, Indexed
from pydantic import Field, EmailStr
from enum import Enum


class VendorStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


class VendorSubscriptionPlan(str, Enum):
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"


class VendorPaymentStatus(str, Enum):
    PAID = "paid"
    PENDING = "pending"
    OVERDUE = "overdue"
    GRACE_PERIOD = "grace_period"


class Vendor(Document):
    organization_id: Indexed(str)
    user_id: Optional[str] = None  # Linked user account (stores contact info: name, email, phone)
    store_name: Indexed(str)  # Trading/Display name for the vendor's store
    name: Optional[str] = None  # Legal/Business Name
    location_id: Optional[str] = None
    status: VendorStatus = VendorStatus.PENDING
    subscription_plan: VendorSubscriptionPlan = VendorSubscriptionPlan.BASIC
    monthly_fee: Optional[float] = None
    commission_rate: Optional[float] = None
    join_date: Optional[date] = None
    last_payment_date: Optional[date] = None
    next_payment_due: Optional[date] = None
    payment_status: VendorPaymentStatus = VendorPaymentStatus.PENDING
    total_sales: float = 0.0
    total_orders: int = 0
    logo_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "vendors"
