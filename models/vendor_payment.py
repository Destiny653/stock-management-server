"""VendorPayment model - Payment tracking for vendors"""
from typing import Optional
from datetime import datetime, date
from beanie import Document, Indexed
from pydantic import Field
from enum import Enum


class VPPaymentType(str, Enum):
    SUBSCRIPTION = "subscription"
    COMMISSION = "commission"
    OTHER = "other"


class VPStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REFUNDED = "refunded"


class VPPaymentMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    OTHER = "other"


class VendorPayment(Document):
    organization_id: Indexed(str)
    vendor_id: Indexed(str)
    vendor_name: Optional[str] = None
    amount: float
    payment_type: VPPaymentType = VPPaymentType.SUBSCRIPTION
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    status: VPStatus = VPStatus.PENDING
    payment_method: VPPaymentMethod = VPPaymentMethod.BANK_TRANSFER
    reference_number: Optional[str] = None
    confirmed_by: Optional[str] = None
    confirmed_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "vendor_payments"
