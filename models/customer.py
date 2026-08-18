"""Customer model - Customer profiles, credit limits, and sales history"""
from typing import Annotated, Optional
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, EmailStr
from enum import Enum


class CustomerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class Customer(Document):
    organization_id: Annotated[str, Indexed()]
    name: Annotated[str, Indexed()]
    code: Optional[str] = None  # e.g., CUST-001
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    credit_limit: float = 0.0
    current_balance: float = 0.0  # Accounts Receivable balance owed by customer
    loyalty_points: int = 0
    total_sales_count: int = 0
    total_sales_value: float = 0.0
    status: CustomerStatus = CustomerStatus.ACTIVE
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "customers"
