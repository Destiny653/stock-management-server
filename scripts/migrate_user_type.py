
import asyncio
import sys
import os

# Add parent directory to path to allow importing from main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.mongodb import init_db
from models.user import User, UserType

async def migrate():
    print("Initializing database...")
    await init_db()
    
    print("Searching for users with user_type='staff'...")
    # Find users where user_type is "staff" (string comparison or enum if it still exists)
    # Since we haven't removed it from enum yet, we can query safely.
    
    # We use raw query to be safe against validation if we were running this AFTER removing from enum (but we are running BEFORE)
    users_to_update = await User.find({"user_type": "staff"}).to_list()
    
    count = len(users_to_update)
    print(f"Found {count} users to migrate.")
    
    if count > 0:
        for user in users_to_update:
            print(f"Migrating user: {user.username} (ID: {user.id})")
            user.user_type = UserType.BUSINESS_STAFF
            await user.save()
        print("Migration complete.")
    else:
        print("No users needed migration.")

if __name__ == "__main__":
    asyncio.run(migrate())
