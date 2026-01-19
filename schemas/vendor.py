"""Vendor schemas"""
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel, EmailStr
from models.vendor import VendorStatus, VendorSubscriptionPlan, VendorPaymentStatus


class VendorBase(BaseModel):
    store_name: str  # Trading/Display name for the vendor's store
    location_id: Optional[str] = None
    status: VendorStatus = VendorStatus.PENDING
    subscription_plan: VendorSubscriptionPlan = VendorSubscriptionPlan.BASIC
    monthly_fee: Optional[float] = None
    commission_rate: Optional[float] = None
    join_date: Optional[date] = None
    last_payment_date: Optional[date] = None
    next_payment_due: Optional[date] = None
    payment_status: VendorPaymentStatus = VendorPaymentStatus.PENDING
    logo_url: Optional[str] = None
    notes: Optional[str] = None


class VendorCreate(VendorBase):
    organization_id: str
    user_id: Optional[str] = None


class VendorUpdate(BaseModel):
    store_name: Optional[str] = None
    location_id: Optional[str] = None
    status: Optional[VendorStatus] = None
    subscription_plan: Optional[VendorSubscriptionPlan] = None
    monthly_fee: Optional[float] = None
    commission_rate: Optional[float] = None
    join_date: Optional[date] = None
    last_payment_date: Optional[date] = None
    next_payment_due: Optional[date] = None
    payment_status: Optional[VendorPaymentStatus] = None
    logo_url: Optional[str] = None
    notes: Optional[str] = None
    user_id: Optional[str] = None


from beanie import PydanticObjectId

class VendorResponse(VendorBase):
    id: PydanticObjectId
    organization_id: str
    user_id: Optional[str] = None
    total_sales: float
    total_orders: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
