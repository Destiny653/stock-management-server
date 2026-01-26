
import asyncio
from models.subscription_plan import SubscriptionPlan
from db.mongodb import init_db

async def seed_plans():
    await init_db()
    
    plans = [
        {
            "name": "Starter",
            "code": "starter",
            "description": "Perfect for small businesses",
            "price_monthly": 29.0,
            "price_yearly": 290.0,
            "features": ["Up to 5 vendors", "Up to 3 users", "Up to 100 products", "Basic reports"],
            "max_vendors": 5,
            "max_users": 3,
            "max_products": 100
        },
        {
            "name": "Business",
            "code": "business",
            "description": "Best for growing companies",
            "price_monthly": 79.0,
            "price_yearly": 790.0,
            "features": ["Up to 25 vendors", "Up to 10 users", "Up to 1,000 products", "Advanced reports", "API access"],
            "max_vendors": 25,
            "max_users": 10,
            "max_products": 1000
        },
        {
            "name": "Enterprise",
            "code": "enterprise",
            "description": "For large organizations",
            "price_monthly": 199.0,
            "price_yearly": 1990.0,
            "features": ["Unlimited vendors", "Unlimited users", "Unlimited products", "Custom reports", "Dedicated support"],
            "max_vendors": 999999,
            "max_users": 999999,
            "max_products": 999999
        }
    ]
    
    for p in plans:
        existing = await SubscriptionPlan.find_one(SubscriptionPlan.code == p["code"])
        if not existing:
            await SubscriptionPlan(**p).create()
            print(f"Created plan: {p['name']}")
        else:
            print(f"Plan exists: {p['name']}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(seed_plans())
