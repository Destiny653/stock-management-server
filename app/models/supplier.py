"""Supplier model - Suppliers for purchase orders"""
from typing import Optional
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
    organization_id: Indexed(str)
    user_id: Optional[str] = None  # Linked contact person
    name: Indexed(str)
    location_id: Optional[str] = None
    payment_terms: PaymentTerms = PaymentTerms.NET_30
    lead_time_days: Optional[int] = None
    rating: Optional[float] = None
    status: SupplierStatus = SupplierStatus.ACTIVE
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "suppliers"
