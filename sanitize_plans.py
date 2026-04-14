import asyncio
from db.mongodb import init_db
from models.organization import Organization
from models.subscription_plan import SubscriptionPlan

async def fix_org_plans():
    await init_db()

    # Get valid plan codes
    plans = await SubscriptionPlan.find_all().to_list()
    valid_plan_ids = [str(p.id) for p in plans]
    valid_plan_codes = [p.code for p in plans]
    
    valid_list = valid_plan_ids + valid_plan_codes
    
    orgs = await Organization.find_all().to_list()
    updated = 0
    for org in orgs:
        current_plan = org.subscription_plan
        # If it's empty, or null, or an object id that is not in the valid lists
        if not current_plan or (current_plan not in valid_list):
            org.subscription_plan = "starter"
            await org.save()
            updated += 1
            print(f"Updated org {org.name} - mapped invalid plan '{current_plan}' to 'starter'")
            
    print(f"Done. Updated {updated} organizations.")

if __name__ == "__main__":
    asyncio.run(fix_org_plans())
