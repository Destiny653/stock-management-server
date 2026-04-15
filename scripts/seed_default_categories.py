"""
Seed script to populate default categories for all existing organizations.
Run this once to add standard categories if they don't exist.
"""
import asyncio
import sys
import os

# Add the server directory to sys.path for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.mongodb import init_db
from models.organization import Organization
from models.category import Category

DEFAULT_CATEGORIES = [
    {"name": "Electronics", "description": "Devices, gadgets, and accessories", "color": "#3b82f6"},
    {"name": "Clothing", "description": "Apparel, footwear, and accessories", "color": "#ec4899"},
    {"name": "Food & Beverage", "description": "Groceries, snacks, and drinks", "color": "#10b981"},
    {"name": "Home & Garden", "description": "Furniture, decor, and tools", "color": "#f59e0b"},
    {"name": "Sports", "description": "Equipment and gear for sports", "color": "#6366f1"},
    {"name": "Beauty", "description": "Skincare, makeup, and personal care", "color": "#f43f5e"},
    {"name": "Office Supplies", "description": "Stationery, paper, and desk tools", "color": "#64748b"},
    {"name": "Other", "description": "General purpose category", "color": "#94a3b8"},
]

async def seed_default_categories():
    print("Starting category seeding...")
    await init_db()
    
    organizations = await Organization.find_all().to_list()
    print(f"Found {len(organizations)} organizations.")
    
    total_created = 0
    for org in organizations:
        org_id = str(org.id)
        # Check if organization already has any categories
        existing_count = await Category.find(Category.organization_id == org_id).count()
        
        if existing_count > 0:
            print(f"Organization '{org.name}' ({org.code}) already has {existing_count} categories. Skipping...")
            continue
            
        print(f"Seeding categories for organization '{org.name}' ({org.code})...")
        for cat_data in DEFAULT_CATEGORIES:
            category = Category(
                organization_id=org_id,
                name=cat_data["name"],
                description=cat_data["description"],
                color=cat_data["color"]
            )
            await category.create()
            total_created += 1
            
    print(f"\nSeeding complete! Created {total_created} categories across organizations.")

if __name__ == "__main__":
    asyncio.run(seed_default_categories())
