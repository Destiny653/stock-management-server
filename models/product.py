"""Product model - Updated with organization_id for multi-tenancy"""
from typing import Optional, List, Annotated, Dict
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


class ValuationMethod(str, Enum):
    FIFO = "fifo"
    WEIGHTED_AVERAGE = "weighted_average"
    MOVING_AVERAGE = "moving_average"
    STANDARD_COST = "standard_cost"


class StockRecord(BaseModel):
    warehouse_id: str
    warehouse_name: Optional[str] = None
    stock: int
    reserved_stock: int = 0
    damaged_stock: int = 0


class ProductVariant(BaseModel):
    variant_id: Optional[str] = None
    sku: str
    attributes: Dict[str, str]
    unit_price: float
    cost_price: float
    stock: int
    warehouse_stocks: List[StockRecord] = Field(default_factory=list)
    image_url: Optional[str] = None
    barcode: Optional[str] = None
    weight: Optional[float] = None
    dimensions: Optional[str] = None
    promotion_price: Optional[float] = None


class Product(Document):
    organization_id: Annotated[str, Indexed()]
    name: Annotated[str, Indexed()]
    sku: Optional[Annotated[str, Indexed()]] = None
    barcode: Optional[Annotated[str, Indexed()]] = None
    category: str = "Other"
    brand: Optional[str] = None
    description: Optional[str] = None
    unit_of_measure: str = "pcs"  # pcs, kg, ltr, box, pack, etc.
    cost_price: float = 0.0
    selling_price: float = 0.0
    tax_rate: float = 0.0  # Percentage e.g. 19.5 or 18.0
    min_stock: Optional[int] = 0
    max_stock: Optional[int] = None
    reorder_point: Optional[int] = None
    reorder_quantity: Optional[int] = None
    valuation_method: ValuationMethod = ValuationMethod.WEIGHTED_AVERAGE
    track_batches: bool = False
    track_serials: bool = False
    total_stock: int = 0
    reserved_stock: int = 0
    damaged_stock: int = 0
    location_id: Optional[str] = None
    warehouse_id: Optional[str] = None  # Direct warehouse/store reference
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    status: ProductStatus = ProductStatus.ACTIVE
    image_url: Optional[str] = None
    expiry_date: Optional[date] = None
    last_restocked: Optional[date] = None
    variants: List[ProductVariant] = Field(default_factory=list)
    warehouse_stocks: List[StockRecord] = Field(default_factory=list)
    is_on_promotion: bool = False
    promotion_start: Optional[datetime] = None
    promotion_end: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "products"
