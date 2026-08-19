"""ServiceProduct model - Commercial catalogue items for software licenses, setup services, and recurring maintenance"""

from typing import Annotated, Optional
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field
from enum import Enum


class CommercialBillingType(str, Enum):
    ONE_TIME = "ONE_TIME"
    RECURRING = "RECURRING"


class ServiceProductCategory(str, Enum):
    SOFTWARE = "software"
    ONE_TIME_SERVICE = "one_time_service"
    RECURRING_SERVICE = "recurring_service"
    OTHER = "other"


class ServiceProduct(Document):
    name: Annotated[str, Indexed()]
    code: Optional[str] = None  # SKU / Service code e.g. SF-ENT-MNT
    category: ServiceProductCategory = ServiceProductCategory.RECURRING_SERVICE
    description: Optional[str] = None
    price: float = 0.0
    currency: str = "XAF"
    billing_type: CommercialBillingType = CommercialBillingType.RECURRING
    is_active: bool = True
    tax_rate: float = 0.0  # Optional specific tax rate percentage e.g. 19.25
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "service_products"
