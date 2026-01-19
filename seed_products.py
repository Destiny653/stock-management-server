import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.models.product import Product, ProductCategory, ProductVariant, ProductStatus
from app.models.organization import Organization
from app.core.config import settings
from datetime import datetime

async def seed_data():
    # Initialize Beanie
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    
    # Drop old SKU index if it exists on the products collection
    try:
        await db.products.drop_index("sku_1")
        print("Dropped old SKU index from products collection")
    except Exception as e:
        print(f"Index 'sku_1' not found or already dropped: {e}")

    await init_beanie(database=db, document_models=[Product, Organization])

    # Ensure we have an organization to link products to
    org = await Organization.find_one({"code": "SF-DEMO"})
    if not org:
        org = Organization(
            name="StockFlow Demo",
            code="SF-DEMO",
            description="Demo organization for testing",
            email="demo@stockflow.com"
        )
        await org.create()
    
    org_id = str(org.id)

    # Clear existing products for this org
    await Product.find({"organization_id": org_id}).delete()

    products_to_create = [
        # 1. Clothing with multiple configurations (Size/Color)
        Product(
            organization_id=org_id,
            name="Premium Cotton T-Shirt",
            category=ProductCategory.CLOTHING,
            description="High-quality 100% cotton t-shirt in various sizes and colors.",
            status=ProductStatus.ACTIVE,
            reorder_point=20,
            variants=[
                ProductVariant(sku="TS-WHT-S", attributes={"color": "White", "size": "S"}, unit_price=19.99, cost_price=8.50, stock=50, weight=0.2, dimensions="20x15x2", barcode="1000101"),
                ProductVariant(sku="TS-WHT-M", attributes={"color": "White", "size": "M"}, unit_price=19.99, cost_price=8.50, stock=75, weight=0.22, dimensions="20x15x2.5", barcode="1000102"),
                ProductVariant(sku="TS-BLK-S", attributes={"color": "Black", "size": "S"}, unit_price=21.99, cost_price=9.00, stock=40, weight=0.2, dimensions="20x15x2", barcode="1000103"),
                ProductVariant(sku="TS-BLK-M", attributes={"color": "Black", "size": "M"}, unit_price=21.99, cost_price=9.00, stock=60, weight=0.22, dimensions="20x15x2.5", barcode="1000104"),
            ]
        ),
        # 2. Electronics with different models/specs
        Product(
            organization_id=org_id,
            name="UltraView Monitor",
            category=ProductCategory.ELECTRONICS,
            description="Professional 4K monitor with adjustable stand.",
            status=ProductStatus.ACTIVE,
            reorder_point=5,
            variants=[
                ProductVariant(sku="MON-27-4K", attributes={"size": "27\"", "resolution": "4K"}, unit_price=399.99, cost_price=250.00, stock=15, weight=5.5, dimensions="62x45x20", barcode="2000101"),
                ProductVariant(sku="MON-32-4K", attributes={"size": "32\"", "resolution": "4K"}, unit_price=549.99, cost_price=380.00, stock=10, weight=7.2, dimensions="75x50x22", barcode="2000102"),
            ]
        ),
        # 3. Food/Beverage with different packaging
        Product(
            organization_id=org_id,
            name="Organic Coffee Beans",
            category=ProductCategory.FOOD_BEVERAGE,
            description="Fair-trade certified roasted coffee beans.",
            status=ProductStatus.ACTIVE,
            reorder_point=15,
            variants=[
                ProductVariant(sku="COF-250G", attributes={"weight": "250g"}, unit_price=12.50, cost_price=5.00, stock=100, weight=0.25, dimensions="15x10x5", barcode="3000101"),
                ProductVariant(sku="COF-1KG", attributes={"weight": "1kg"}, unit_price=42.00, cost_price=18.00, stock=45, weight=1.0, dimensions="30x20x10", barcode="3000102"),
            ]
        ),
        # 4. Single-variant item (Default variant)
        Product(
            organization_id=org_id,
            name="Wireless Optical Mouse",
            category=ProductCategory.ELECTRONICS,
            description="Ergonomic wireless mouse with USB receiver.",
            status=ProductStatus.ACTIVE,
            reorder_point=10,
            variants=[
                ProductVariant(
                    sku="MSE-WRLS-01", 
                    attributes={"model": "Standard"}, 
                    unit_price=24.99, 
                    cost_price=12.00, 
                    stock=8, # Low stock trigger
                    weight=0.15, 
                    dimensions="10x6x4", 
                    barcode="2000201"
                )
            ]
        ),
        # 5. Out of stock item
        Product(
            organization_id=org_id,
            name="Vintage Leather Notebook",
            category=ProductCategory.OFFICE_SUPPLIES,
            description="Handcrafted leather-bound notebook.",
            status=ProductStatus.OUT_OF_STOCK,
            reorder_point=10,
            variants=[
                ProductVariant(
                    sku="NBK-LTH-01", 
                    attributes={"color": "Tan"}, 
                    unit_price=35.00, 
                    cost_price=15.00, 
                    stock=0, 
                    weight=0.6, 
                    dimensions="22x15x3", 
                    barcode="4000101"
                )
            ]
        )
    ]

    for product in products_to_create:
        # Calculate status based on total stock
        total_stock = sum(v.stock for v in product.variants)
        if total_stock == 0:
            product.status = ProductStatus.OUT_OF_STOCK
        elif total_stock <= (product.reorder_point or 0):
            product.status = ProductStatus.LOW_STOCK
        else:
            product.status = ProductStatus.ACTIVE
            
        await product.create()

    print(f"Successfully seeded {len(products_to_create)} products for organization {org.name} ({org_id})")

if __name__ == "__main__":
    asyncio.run(seed_data())
