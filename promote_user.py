
import asyncio
from app.db.mongodb import init_db
from app.models.user import User

async def promote_user():
    await init_db()
    user = await User.find_one({"username": "testuser"})
    if user:
        user.role = "admin"
        await user.save()
        print(f"User {user.username} promoted to admin")
    else:
        print("User not found")

if __name__ == "__main__":
    asyncio.run(promote_user())
