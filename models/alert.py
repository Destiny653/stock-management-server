"""Alert model - System notifications"""
from typing import Optional
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field
from enum import Enum


class AlertType(str, Enum):
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    EXPIRING = "expiring"
    PENDING_APPROVAL = "pending_approval"
    PO_RECEIVED = "po_received"
    SYSTEM = "system"


class AlertPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(Document):
    organization_id: Indexed(str)
    type: AlertType
    priority: AlertPriority = AlertPriority.MEDIUM
    title: str
    message: str
    product_id: Optional[str] = None
    po_id: Optional[str] = None
    is_read: bool = False
    is_dismissed: bool = False
    action_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "alerts"
