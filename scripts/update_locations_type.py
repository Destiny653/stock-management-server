import asyncio
import os
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from models.location import Location
from core.config import settings

async def update_locations():
    # Use the URL from the environment or settings
    mongo_url = os.getenv("MONGODB_URL", "mongodb+srv://fokundemcom_db_user:fokundem653%40@cluster0.wvczxnq.mongodb.net/?appName=Cluster0")
    db_name = os.getenv("MONGODB_DB_NAME", "stockflow_db")
    
    print(f"Connecting to {db_name}...")
    client = AsyncIOMotorClient(mongo_url)
    database = client[db_name]
    
    await init_beanie(database=database, document_models=[Location])
    
    # Update all locations to have a type if missing, and set some to 'store'
    locations = await Location.find_all().to_list()
    print(f"Found {len(locations)} locations.")
    
    for loc in locations:
        # Update existing ones to have a type
        loc.type = "store"
        await loc.save()
        print(f"Updated {loc.name} type to {loc.type}")

    print("Update complete.")

if __name__ == "__main__":
    asyncio.run(update_locations())
