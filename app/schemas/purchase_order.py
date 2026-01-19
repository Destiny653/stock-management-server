"""PurchaseOrder schemas"""
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel
from app.models.purchase_order import POStatus, POItem


class POItemCreate(BaseModel):
    product_id: str
    sku: Optional[str] = None
    product_name: str
    quantity_ordered: int
    quantity_received: int = 0
    unit_cost: float
    total: float


class PurchaseOrderBase(BaseModel):
    po_number: str
    supplier_id: Optional[str] = None
    supplier_name: str
    status: POStatus = POStatus.DRAFT
    items: List[POItemCreate] = []
    subtotal: float = 0.0
    tax: float = 0.0
    shipping: float = 0.0
    total: float = 0.0
    expected_date: Optional[date] = None
    received_date: Optional[date] = None
    notes: Optional[str] = None
    approved_by: Optional[str] = None
    warehouse: Optional[str] = None


class PurchaseOrderCreate(PurchaseOrderBase):
    organization_id: str


class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    status: Optional[POStatus] = None
    items: Optional[List[POItemCreate]] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    shipping: Optional[float] = None
    total: Optional[float] = None
    expected_date: Optional[date] = None
    received_date: Optional[date] = None
    notes: Optional[str] = None
    approved_by: Optional[str] = None
    warehouse: Optional[str] = None


from beanie import PydanticObjectId

class PurchaseOrderResponse(PurchaseOrderBase):
    id: PydanticObjectId
    organization_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
