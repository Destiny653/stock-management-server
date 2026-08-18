"""SupplierReturn model - Returning goods to suppliers and receiving debit notes"""
from typing import Annotated, Optional, List
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, BaseModel
from enum import Enum


class SupplierReturnItem(BaseModel):
    product_id: str
    product_name: str
    sku: Optional[str] = None
    quantity: int
    unit_cost: float
    total_cost: float
    reason: Optional[str] = None


class SupplierReturnStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    REJECTED = "rejected"


class SupplierReturn(Document):
    organization_id: Annotated[str, Indexed()]
    return_number: Annotated[str, Indexed(unique=True)]  # e.g., SRET-2026-0001
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    po_id: Optional[str] = None
    po_number: Optional[str] = None
    warehouse_id: Optional[str] = None
    items: List[SupplierReturnItem] = Field(default_factory=list)
    total_amount: float = 0.0
    debit_note_number: Optional[str] = None
    status: SupplierReturnStatus = SupplierReturnStatus.DRAFT
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "supplier_returns"
