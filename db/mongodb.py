"""MongoDB database initialization"""
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from core.config import settings

# Import all models
from models.organization import Organization
from models.user import User
from models.product import Product
from models.supplier import Supplier
from models.vendor import Vendor
from models.warehouse import Warehouse
from models.purchase_order import PurchaseOrder
from models.sale import Sale
from models.stock_movement import StockMovement
from models.alert import Alert
from models.vendor_payment import VendorPayment
from models.location import Location


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
            "models.subscription_plan.SubscriptionPlan",
        ]
    )
