import asyncio
import sys
import os

# Add parent directory to path to allow importing from main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.mongodb import init_db
from models.user import User

async def migrate():
    print("Initializing database...")
    await init_db()
    
    # Mapping old roles to new roles
    role_mapping = {
        "owner": "admin",
        "staff": "user",
        "viewer": "user"
    }
    
    total_migrated = 0
    
    for old_role, new_role in role_mapping.items():
        print(f"Searching for users with role='{old_role}'...")
        # Use raw query to avoid Pydantic validation if enum values were already removed
        users_to_update = await User.find({"role": old_role}).to_list()
        
        count = len(users_to_update)
        print(f"Found {count} users with role '{old_role}' to migrate to '{new_role}'.")
        
        if count > 0:
            for user in users_to_update:
                print(f"Migrating user: {user.username} (ID: {user.id}) from {old_role} to {new_role}")
                # Update using direct database update to bypass model validation if needed
                await User.find({"_id": user.id}).update({"$set": {"role": new_role}})
                total_migrated += 1
            print(f"Migration for role '{old_role}' complete.")
        else:
            print(f"No users with role '{old_role}' needed migration.")
    
    print(f"All role migrations complete. Total users migrated: {total_migrated}")

if __name__ == "__main__":
    asyncio.run(migrate())
