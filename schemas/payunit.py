from typing import Optional
from pydantic import BaseModel, Field


class PayUnitCollectRequest(BaseModel):
    amount: float
    phone_number: str = Field(..., description="Phone number, e.g. 6xxxxxxxx or 237xxxxxxxx")
    gateway: str = Field(..., description="CM_MTN or CM_ORANGE")
    description: Optional[str] = "Subscription Payment"

    # Metadata for subscription activation
    organization_id: str
    subscription_plan_id: str
    billing_period: str  # "monthly" or "yearly"


class PayUnitResponse(BaseModel):
    transaction_id: str
    status: str
    message: Optional[str] = None


class PayUnitWebhookPayload(BaseModel):
    """
    Payload received from PayUnit via the notify_url callback.
    Fields are kept flexible with Optional to handle varying payloads.
    """
    transaction_id: Optional[str] = None
    t_id: Optional[str] = None  # alternative field name PayUnit may use
    status: Optional[str] = None
    transaction_status: Optional[str] = None  # alternative field name
    amount: Optional[float] = None
    transaction_amount: Optional[float] = None
    currency: Optional[str] = None
    provider_name: Optional[str] = None
    message: Optional[str] = None

    class Config:
        extra = "allow"  # Accept any extra fields PayUnit sends
