"""CommercialPayment model - Payment recording for commercial invoices"""

from typing import Annotated, Optional
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field
from enum import Enum


class CommercialPaymentMethod(str, Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_MONEY = "mobile_money"
    CARD = "card"
    ONLINE = "online"
    OTHER = "other"


class CommercialPayment(Document):
    payment_number: Annotated[str, Indexed(unique=True)]  # e.g. PAY-2026-0001
    invoice_id: Annotated[str, Indexed()]
    invoice_number: str
    organization_id: Annotated[str, Indexed()]
    customer_name: Optional[str] = None

    amount: float
    currency: str = "XAF"

    payment_method: CommercialPaymentMethod = CommercialPaymentMethod.BANK_TRANSFER
    payment_date: datetime = Field(default_factory=datetime.utcnow)

    reference_number: Optional[str] = None
    notes: Optional[str] = None
    recorded_by: Optional[str] = None  # User ID / User Name

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "commercial_payments"
