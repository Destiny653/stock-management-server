"""VendorPayment schemas"""
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel
from app.models.vendor_payment import VPPaymentType, VPStatus, VPPaymentMethod


class VendorPaymentBase(BaseModel):
    vendor_id: str
    vendor_name: Optional[str] = None
    amount: float
    payment_type: VPPaymentType = VPPaymentType.SUBSCRIPTION
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    status: VPStatus = VPStatus.PENDING
    payment_method: VPPaymentMethod = VPPaymentMethod.BANK_TRANSFER
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class VendorPaymentCreate(VendorPaymentBase):
    organization_id: str


class VendorPaymentUpdate(BaseModel):
    vendor_name: Optional[str] = None
    amount: Optional[float] = None
    payment_type: Optional[VPPaymentType] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    status: Optional[VPStatus] = None
    payment_method: Optional[VPPaymentMethod] = None
    reference_number: Optional[str] = None
    confirmed_by: Optional[str] = None
    confirmed_date: Optional[datetime] = None
    notes: Optional[str] = None


from beanie import PydanticObjectId

class VendorPaymentResponse(VendorPaymentBase):
    id: PydanticObjectId
    organization_id: str
    confirmed_by: Optional[str] = None
    confirmed_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
