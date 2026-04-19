from typing import Optional
from pydantic import BaseModel, Field

class CampayCollectRequest(BaseModel):
    amount: float
    currency: str = "XAF"
    from_phone: str = Field(..., description="Phone number with country code, e.g., 2376xxxxxxxx")
    description: Optional[str] = "Subscription Payment"
    external_reference: Optional[str] = None
    
    # Metadata for subscription activation
    organization_id: str
    subscription_plan_id: str
    billing_period: str  # "monthly" or "yearly"

class CampayResponse(BaseModel):
    reference: str
    status: str
    amount: float
    currency: str
    operator: Optional[str] = None
    code: Optional[str] = None

class CampayWebhookPayload(BaseModel):
    reference: str
    status: str
    amount: float
    currency: str
    external_reference: Optional[str] = None
    operator: Optional[str] = None
    operator_reference: Optional[str] = None
    signature: Optional[str] = None
