
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend.env")

async def fix_user_types():
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB_NAME", "stockflow_db")
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[db_name]
    collection = db["users"]
    
    # Find and fix "admin" user_type
    result_admin = await collection.update_many(
        {"user_type": "admin"},
        {"$set": {"user_type": "business-staff", "role": "admin"}}
    )
    print(f"Updated {result_admin.modified_count} users with user_type='admin' to business-staff/admin")

    # Find and fix "vendor" user_type
    result_vendor = await collection.update_many(
        {"user_type": "vendor"},
        {"$set": {"user_type": "business-staff", "role": "vendor"}}
    )
    print(f"Updated {result_vendor.modified_count} users with user_type='vendor' to business-staff/vendor")

    # Find and fix "staff" user_type
    result_staff = await collection.update_many(
        {"user_type": "staff"},
        {"$set": {"user_type": "business-staff", "role": "staff"}}
    )
    print(f"Updated {result_staff.modified_count} users with user_type='staff' to business-staff/staff")

if __name__ == "__main__":
    asyncio.run(fix_user_types())
