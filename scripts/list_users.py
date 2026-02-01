
import asyncio
import sys
import os

# Add parent directory to path to allow importing from main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.mongodb import init_db
from models.user import User

async def list_users():
    print("Initializing database...")
    await init_db()
    
    print("Listing all users...")
    users = await User.find_all().to_list()
    
    for user in users:
        print(f"User: {user.username}, Type: {user.user_type}, Raw: {user.user_type.value}")

if __name__ == "__main__":
    asyncio.run(list_users())
