"""AuditLog model - System-wide audit trail for compliance and security"""
from typing import Annotated, Optional, Dict, Any
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field


class AuditLog(Document):
    organization_id: Annotated[str, Indexed()]
    user_id: Optional[Annotated[str, Indexed()]] = None
    user_name: Optional[str] = None
    action: Annotated[str, Indexed()]  # e.g., "stock.adjust", "product.create", "po.approve"
    resource_type: str  # e.g., "Product", "PurchaseOrder", "Sale", "StockMovement"
    resource_id: Optional[str] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "audit_logs"
