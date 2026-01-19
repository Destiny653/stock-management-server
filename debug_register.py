
import asyncio
from db.mongodb import init_db
from models.user import User
from schemas.user import UserCreate
from core import security
import json

async def test_register():
    await init_db()
    
    user_in = UserCreate(
        email="test_err@example.com",
        username="test_err_user",
        password="string",
        first_name="string",
        last_name="string",
        full_name="string",
        phone="string",
        avatar="string",
        role="staff",
        user_type="staff",
        permissions=[],
        warehouse_access=[],
        organization_id="string"
    )
    
    try:
        # Check if exists
        existing = await User.find_one(User.email == user_in.email)
        if existing:
            print("User already exists, deleting for test...")
            await existing.delete()
            
        hashed_password = security.get_password_hash(user_in.password)
        user_data = user_in.model_dump(exclude={"password"})
        user_data["hashed_password"] = hashed_password
        
        user = User(**user_data)
        await user.create()
        print("User created successfully")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_register())
