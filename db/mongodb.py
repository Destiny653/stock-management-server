"""MongoDB database initialization"""
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import certifi
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
from models.organization_payment import OrganizationPayment
from models.subscription_plan import SubscriptionPlan
from models.auth_request import PasswordResetRequest
from models.category import Category
from models.storefront_config import StorefrontConfig
from models.product_review import ProductReview
from models.storefront_order import StorefrontOrder


async def init_db():
    """Initialize MongoDB connection and Beanie ODM"""
    kwargs = {
        "serverSelectionTimeoutMS": 60000,
        "connectTimeoutMS": 60000,
        "socketTimeoutMS": 60000,
    }
    
    if not settings.VALIDATE_CERTS:
        kwargs["tlsAllowInvalidCertificates"] = True
    else:
        kwargs["tlsCAFile"] = certifi.where()

    client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        **kwargs
    )

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
            OrganizationPayment,
            Location,
            SubscriptionPlan,
            PasswordResetRequest,
            Category,
            StorefrontConfig,
            ProductReview,
            StorefrontOrder,
        ]
    )
