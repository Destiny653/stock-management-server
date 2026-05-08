"""OrganizationPayment model - Payment tracking for subscriptions/addons per organization"""

from typing import Annotated, Optional
from datetime import datetime

from beanie import Document, Indexed
from enum import Enum
from pydantic import Field


class OPaymentType(str, Enum):
    SUBSCRIPTION = "subscription"
    ADDON = "addon"
    UPGRADE = "upgrade"
    RENEWAL = "renewal"


class OPStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class OPaymentMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    OTHER = "other"


class OrganizationPayment(Document):
    organization_id: Annotated[str, Indexed()]
    subscription_plan_id: Optional[str] = None

    amount: float
    currency: str

    payment_method: OPaymentMethod = OPaymentMethod.BANK_TRANSFER
    payment_type: OPaymentType = OPaymentType.SUBSCRIPTION
    billing_period: Optional[str] = None  # "monthly" | "yearly"

    status: OPStatus = OPStatus.PENDING
    reference_number: Optional[str] = None
    invoice_number: Optional[str] = None

    payment_date: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None

    notes: Optional[str] = None
    proof_screenshot_url: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "organization_payments"

