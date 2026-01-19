"""Product schemas - Updated with organization support"""
from typing import Optional, List, Dict
from datetime import datetime, date
from pydantic import BaseModel
from app.models.product import ProductCategory, ProductStatus


class ProductVariant(BaseModel):
    sku: str
    attributes: Dict[str, str]
    unit_price: float
    cost_price: float
    stock: int
    barcode: Optional[str] = None
    weight: Optional[float] = None
    dimensions: Optional[str] = None


class ProductBase(BaseModel):
    name: str
    category: ProductCategory = ProductCategory.OTHER
    description: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    reorder_point: Optional[int] = None
    reorder_quantity: Optional[int] = None
    location_id: Optional[str] = None
    status: ProductStatus = ProductStatus.ACTIVE
    image_url: Optional[str] = None
    expiry_date: Optional[date] = None
    last_restocked: Optional[date] = None
    variants: List[ProductVariant] = []


class ProductCreate(ProductBase):
    organization_id: str


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[ProductCategory] = None
    description: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    reorder_point: Optional[int] = None
    reorder_quantity: Optional[int] = None
    location_id: Optional[str] = None
    status: Optional[ProductStatus] = None
    image_url: Optional[str] = None
    expiry_date: Optional[date] = None
    last_restocked: Optional[date] = None
    variants: Optional[List[ProductVariant]] = None


from beanie import PydanticObjectId

class ProductResponse(ProductBase):
    id: PydanticObjectId
    organization_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
