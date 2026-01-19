
import asyncio
from app.db.mongodb import init_db
from app.models.user import User

async def check_users():
    await init_db()
    users = await User.find_all().to_list()
    for u in users:
        print(f"Username: {u.username}, Role: {u.role}, Email: {u.email}")

if __name__ == "__main__":
    asyncio.run(check_users())
