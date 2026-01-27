"""
Seed script to populate subscription plans in the database.
Run this once to add the default subscription plans.
"""
import asyncio
from db.mongodb import init_db
from models.subscription_plan import SubscriptionPlan

async def seed_subscription_plans():
    await init_db()
    
    plans = [
        {
            "name": "Starter",
            "code": "starter",
            "description": "Perfect for small businesses",
            "price_monthly": 29.0,
            "price_yearly": 290.0,
            "features": [
                "Up to 5 vendors",
                "Up to 3 users",
                "Up to 100 products",
                "Basic reports",
                "Email support"
            ],
            "max_vendors": 5,
            "max_users": 3,
            "max_products": 100,
            "is_active": True
        },
        {
            "name": "Business",
            "code": "business",
            "description": "Best for growing companies",
            "price_monthly": 79.0,
            "price_yearly": 790.0,
            "features": [
                "Up to 25 vendors",
                "Up to 10 users",
                "Up to 1,000 products",
                "Advanced reports",
                "API access",
                "Priority support"
            ],
            "max_vendors": 25,
            "max_users": 10,
            "max_products": 1000,
            "is_active": True
        },
        {
            "name": "Enterprise",
            "code": "enterprise",
            "description": "For large organizations",
            "price_monthly": 199.0,
            "price_yearly": 1990.0,
            "features": [
                "Unlimited vendors",
                "Unlimited users",
                "Unlimited products",
                "Custom reports",
                "Dedicated support",
                "SLA guarantee",
                "Custom integrations"
            ],
            "max_vendors": 9999,
            "max_users": 9999,
            "max_products": 99999,
            "is_active": True
        }
    ]
    
    for plan_data in plans:
        # Check if plan already exists
        existing = await SubscriptionPlan.find_one(SubscriptionPlan.code == plan_data["code"])
        if existing:
            print(f"Plan '{plan_data['code']}' already exists, skipping...")
            continue
        
        plan = SubscriptionPlan(**plan_data)
        await plan.create()
        print(f"Created plan: {plan_data['name']} (${plan_data['price_monthly']}/mo)")
    
    print("\nSubscription plans seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_subscription_plans())
