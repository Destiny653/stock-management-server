"""Alert schemas"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from models.alert import AlertType, AlertPriority


class AlertBase(BaseModel):
    type: AlertType
    priority: AlertPriority = AlertPriority.MEDIUM
    title: str
    message: str
    product_id: Optional[str] = None
    po_id: Optional[str] = None
    is_read: bool = False
    is_dismissed: bool = False
    action_url: Optional[str] = None


class AlertCreate(AlertBase):
    organization_id: str


class AlertUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_dismissed: Optional[bool] = None


from beanie import PydanticObjectId

class AlertResponse(AlertBase):
    id: PydanticObjectId
    organization_id: str
    created_at: datetime

    class Config:
        from_attributes = True
