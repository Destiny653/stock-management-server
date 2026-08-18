"""Supplier model - Suppliers for purchase orders"""
from typing import Annotated, Optional
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, EmailStr
from enum import Enum


class PaymentTerms(str, Enum):
    NET_15 = "Net 15"
    NET_30 = "Net 30"
    NET_45 = "Net 45"
    NET_60 = "Net 60"
    COD = "COD"


class SupplierStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class Supplier(Document):
    organization_id: Annotated[str, Indexed()]
    user_id: Optional[str] = None  # Linked contact person
    name: Annotated[str, Indexed()]
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    location_id: Optional[str] = None
    payment_terms: PaymentTerms = PaymentTerms.NET_30
    credit_limit: float = 0.0
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    lead_time_days: Optional[int] = None
    rating: Optional[float] = None
    status: SupplierStatus = SupplierStatus.ACTIVE
    notes: Optional[str] = None
    # Performance analytics
    avg_lead_time_days: float = 0.0
    on_time_delivery_pct: float = 100.0
    total_purchases_count: int = 0
    total_purchases_value: float = 0.0
    outstanding_balance: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "suppliers"
