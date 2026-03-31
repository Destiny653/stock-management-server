"""OrganizationPayment schemas"""

from typing import Optional
from datetime import datetime

from pydantic import BaseModel
from beanie import PydanticObjectId

from models.organization_payment import OPaymentType, OPStatus, OPaymentMethod


class OrganizationPaymentBase(BaseModel):
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


class OrganizationPaymentCreate(OrganizationPaymentBase):
    organization_id: str


class OrganizationPaymentUpdate(BaseModel):
    subscription_plan_id: Optional[str] = None

    amount: Optional[float] = None
    currency: Optional[str] = None

    payment_method: Optional[OPaymentMethod] = None
    payment_type: Optional[OPaymentType] = None
    billing_period: Optional[str] = None

    status: Optional[OPStatus] = None

    reference_number: Optional[str] = None
    invoice_number: Optional[str] = None

    payment_date: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None

    notes: Optional[str] = None
    proof_screenshot_url: Optional[str] = None


class OrganizationPaymentResponse(OrganizationPaymentBase):
    id: PydanticObjectId
    organization_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

