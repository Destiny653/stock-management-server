"""Storefront order schemas"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from beanie import PydanticObjectId


class OrderItemCreate(BaseModel):
    product_id: str
    product_name: str
    sku: Optional[str] = None
    variant_label: Optional[str] = None
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)
    image_url: Optional[str] = None


class StorefrontOrderCreate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100)
    customer_email: Optional[str] = None
    customer_phone: str = Field(min_length=9, max_length=20)
    items: List[OrderItemCreate] = Field(min_length=1)
    payment_method: str = "mtn"
    notes: Optional[str] = None


class OrderItemResponse(BaseModel):
    product_id: str
    product_name: str
    sku: Optional[str] = None
    variant_label: Optional[str] = None
    quantity: int
    unit_price: float
    total: float
    image_url: Optional[str] = None


class StorefrontOrderResponse(BaseModel):
    id: PydanticObjectId
    organization_id: str
    order_ref: str
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: str
    items: List[OrderItemResponse] = []
    subtotal: float
    total: float
    payment_method: str
    payment_phone: Optional[str] = None
    ussd_string: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
