import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load env
load_dotenv(".env")
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "stock_management")

async def main():
    print(f"Connecting to MongoDB at {MONGODB_URL}")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    
    # 1. Update Subscription Plans
    print("Updating Subscription Plans...")
    plans_collection = db["subscription_plans"]
    
    plan_updates = {
        "starter": {"storage_capacity_kb": 512000, "is_popular": False},      # 500 MB
        "professional": {"storage_capacity_kb": 2097152, "is_popular": True}, # 2 GB
        "business": {"storage_capacity_kb": 5242880, "is_popular": True},     # 5 GB
        "enterprise": {"storage_capacity_kb": 20971520, "is_popular": False}  # 20 GB
    }
    
    for code, extra in plan_updates.items():
        result = await plans_collection.update_many(
            {"code": code},
            {"$set": extra}
        )
        print(f"Updated {result.modified_count} plans with code '{code}'")

    # 2. Update Organizations to ensure they map back to the plan
    print("Updating Organizations to rely on subscription_plan...")
    orgs_collection = db["organizations"]
    
    # Optional: we can unset the old hardcoded limits if we want strict schema
    # but for safety right now we'll just leave them and ignore them in frontend,
    # or we can unset them so they don't cause confusion.
    result = await orgs_collection.update_many(
        {}, 
        {"$unset": {"max_vendors": "", "max_users": "", "storage_capacity_kb": ""}}
    )
    print(f"Removed redundant limits from {result.modified_count} organizations")
    
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
