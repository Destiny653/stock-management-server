
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.models.organization import Organization
from app.models.location import Location
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.vendor import Vendor
from app.models.warehouse import Warehouse
from app.core.config import settings

async def test():
    print("Testing MongoDB connection and Beanie initialization...")
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    database = client["stockflow_test_db"]
    
    try:
        await init_beanie(
            database=database,
            document_models=[
                Organization,
                Location,
                Product,
                Supplier,
                Vendor,
                Warehouse
            ]
        )
        print("Initialization successful!")
        
        # 1. Create a test organization
        print("Creating test organization...")
        org = Organization(
            name="Product Test Org",
            code="PTORG",
        )
        await org.create()
        print(f"Organization created with ID: {org.id}")

        # 2. Create a test location
        print("Creating test location...")
        loc = Location(
            name="Main Shelf A1",
            address="123 Tech St",
            city="Douala",
            country="Cameroon"
        )
        await loc.create()
        print(f"Location created with ID: {loc.id}")
        
        # 3. Create a test product
        print("Creating test product...")
        product = Product(
            organization_id=str(org.id),
            name="Testing Laptop",
            category="Electronics",
            location_id=str(loc.id),
            variants=[
                {
                    "sku": "LAP-001",
                    "attributes": {"color": "Silver", "ram": "16GB"},
                    "unit_price": 1200.0,
                    "cost_price": 800.0,
                    "stock": 10
                }
            ]
        )
        await product.create()
        print(f"Product created with ID: {product.id}")
        
        # 4. Verify retrieval
        fetched_product = await Product.get(product.id)
        if fetched_product and fetched_product.name == "Testing Laptop":
            print("Product retrieval and data integrity: OK ✅")
            print(f"Variant SKU: {fetched_product.variants[0].sku}")
        else:
            print("Product retrieval: FAILED ❌")

        # Cleanup
        await product.delete()
        await loc.delete()
        await org.delete()
        print("Cleanup successful.")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test())
