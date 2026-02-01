
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend.env")

async def check_db_integrity():
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB_NAME", "stockflow_db")
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[db_name]
    collection = db["users"]
    
    valid_roles = ["owner", "admin", "manager", "vendor", "staff", "viewer", "user"]
    valid_types = ["platform-staff", "business-staff"]
    valid_statuses = ["active", "inactive", "suspended", "pending"]
    
    print(f"Checking collection: {collection.name}")
    
    cursor = collection.find({})
    users = await cursor.to_list(length=None)
    
    print(f"Total users: {len(users)}")
    
    invalid_users = []
    for u in users:
        issues = []
        if u.get("role") not in valid_roles:
            issues.append(f"Invalid role: {u.get('role')}")
        if u.get("user_type") not in valid_types:
            issues.append(f"Invalid user_type: {u.get('user_type')}")
        if u.get("status") not in valid_statuses:
            issues.append(f"Invalid status: {u.get('status')}")
            
        if issues:
            invalid_users.append({
                "username": u.get("username"),
                "email": u.get("email"),
                "issues": issues
            })
            
    if not invalid_users:
        print("All users are valid according to current enums.")
    else:
        print(f"Found {len(invalid_users)} invalid users:")
        for iu in invalid_users:
            print(f"- {iu['username']} ({iu['email']}): {', '.join(iu['issues'])}")

if __name__ == "__main__":
    asyncio.run(check_db_integrity())
