"""MongoDB database initialization"""
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings

# Import all models
from app.models.organization import Organization
from app.models.user import User
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.vendor import Vendor
from app.models.warehouse import Warehouse
from app.models.purchase_order import PurchaseOrder
from app.models.sale import Sale
from app.models.stock_movement import StockMovement
from app.models.alert import Alert
from app.models.vendor_payment import VendorPayment
from app.models.location import Location


async def init_db():
    """Initialize MongoDB connection and Beanie ODM"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    await init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=[
            Organization,
            User,
            Product,
            Supplier,
            Vendor,
            Warehouse,
            PurchaseOrder,
            Sale,
            StockMovement,
            Alert,
            VendorPayment,
            Location,
        ]
    )
