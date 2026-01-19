"""Product model - Updated with organization_id for multi-tenancy"""
from typing import Optional, List, Dict
from datetime import datetime, date
from beanie import Document, Indexed
from pydantic import Field, BaseModel
from enum import Enum


class ProductCategory(str, Enum):
    ELECTRONICS = "Electronics"
    CLOTHING = "Clothing"
    FOOD_BEVERAGE = "Food & Beverage"
    HOME_GARDEN = "Home & Garden"
    SPORTS = "Sports"
    BEAUTY = "Beauty"
    OFFICE_SUPPLIES = "Office Supplies"
    OTHER = "Other"


class ProductStatus(str, Enum):
    ACTIVE = "active"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


class ProductVariant(BaseModel):
    sku: str
    attributes: Dict[str, str]
    unit_price: float
    cost_price: float
    stock: int
    barcode: Optional[str] = None
    weight: Optional[float] = None
    dimensions: Optional[str] = None


class Product(Document):
    organization_id: Indexed(str)
    name: Indexed(str)
    category: ProductCategory = ProductCategory.OTHER
    description: Optional[str] = None
    reorder_point: Optional[int] = None
    reorder_quantity: Optional[int] = None
    location_id: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    status: ProductStatus = ProductStatus.ACTIVE
    image_url: Optional[str] = None
    expiry_date: Optional[date] = None
    last_restocked: Optional[date] = None
    variants: List[ProductVariant] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "products"
