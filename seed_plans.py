"""
Seed / reset subscription plans to the 3 canonical plans.
Run once:  python seed_plans.py
"""
import asyncio
from db.mongodb import init_db
from models.subscription_plan import SubscriptionPlan

PLANS = [
    {
        "name": "Starter",
        "code": "starter",
        "description": "Perfect for small shops just getting started",
        "price_monthly": 12000.0,
        "price_yearly": 10000.0,
        "currency": "XAF",
        "features": [
            "Up to 30 products",
            "1 vendor",
            "Basic reporting",
            "Email support",
        ],
        "max_vendors": 1,
        "max_users": 2,
        "max_products": 30,
        "max_locations": 1,
        "storage_capacity_kb": 512 * 1024,  # 512 MB
        "is_popular": False,
        "is_active": True,
    },
    {
        "name": "Business",
        "code": "business",
        "description": "For growing businesses with multiple vendors",
        "price_monthly": 15000.0,
        "price_yearly": 12000.0,
        "currency": "XAF",
        "features": [
            "Up to 100 products",
            "Up to 3 vendors",
            "Advanced reporting",
            "Priority support",
            "Multi-location",
        ],
        "max_vendors": 3,
        "max_users": 5,
        "max_products": 100,
        "max_locations": 3,
        "storage_capacity_kb": 2048 * 1024,  # 2 GB
        "is_popular": True,
        "is_active": True,
    },
    {
        "name": "Enterprise",
        "code": "enterprise",
        "description": "Unlimited growth for large organizations",
        "price_monthly": 20000.0,
        "price_yearly": 18000.0,
        "currency": "XAF",
        "features": [
            "Unlimited products (100+)",
            "3+ vendors (unlimited)",
            "Custom reporting",
            "Dedicated account manager",
            "API access",
            "Multi-warehouse",
        ],
        "max_vendors": 1_000_000,
        "max_users": 1_000_000,
        "max_products": 1_000_000,
        "max_locations": 1_000_000,
        "storage_capacity_kb": 20480 * 1024,  # 20 GB
        "is_popular": False,
        "is_active": True,
    },
]


async def seed():
    await init_db()

    # Delete all existing plans
    existing = await SubscriptionPlan.find_all().to_list()
    for p in existing:
        await p.delete()
    print(f"Deleted {len(existing)} existing plans.")

    for data in PLANS:
        plan = SubscriptionPlan(**data)
        await plan.create()
        print(f"Created: {plan.name}  (monthly={plan.price_monthly:,.0f} XAF, yearly={plan.price_yearly:,.0f} XAF)")

    print("Done ✓")


asyncio.run(seed())
