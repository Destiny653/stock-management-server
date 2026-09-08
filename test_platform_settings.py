import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from models.platform_settings import PlatformSettings
from db.mongodb import init_db

async def run():
    await init_db()
    settings = await PlatformSettings.find_one()
    if settings:
        print(f"Platform allowed: {settings.allowed_payment_methods}")
    else:
        print("No platform settings")

asyncio.run(run())
