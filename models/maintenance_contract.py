"""MaintenanceContract model - Recurring maintenance agreements with commercial customers"""

from typing import Annotated, Optional, List
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field
from enum import Enum


class ContractStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ContractBillingFrequency(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"


class ServiceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    TRIAL = "TRIAL"
    PAYMENT_DUE = "PAYMENT_DUE"
    OVERDUE = "OVERDUE"
    GRACE_PERIOD = "GRACE_PERIOD"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"


class MaintenanceContract(Document):
    contract_number: Annotated[str, Indexed(unique=True)]  # e.g. MNT-2026-0001
    organization_id: Annotated[str, Indexed()]  # Commercial customer / tenant ID
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None

    start_date: datetime
    end_date: Optional[datetime] = None

    billing_frequency: ContractBillingFrequency = ContractBillingFrequency.MONTHLY
    maintenance_amount: float = 0.0
    currency: str = "XAF"

    status: ContractStatus = ContractStatus.ACTIVE
    service_status: ServiceStatus = ServiceStatus.ACTIVE

    next_billing_date: Annotated[datetime, Indexed()]
    last_billed_date: Optional[datetime] = None

    auto_renewal: bool = True
    grace_period_days: int = 7
    payment_terms_days: int = 14

    included_services: List[str] = Field(default_factory=lambda: [
        "Bug fixes & security patches",
        "Database maintenance & backup monitoring",
        "Technical support & system monitoring",
        "Minor application updates"
    ])
    excluded_services: List[str] = Field(default_factory=lambda: [
        "Custom feature development",
        "Third-party integrations",
        "Hardware replacement"
    ])

    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "maintenance_contracts"
