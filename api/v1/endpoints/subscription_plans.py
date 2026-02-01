from typing import Any, List
from fastapi import APIRouter, HTTPException
from models.subscription_plan import SubscriptionPlan
from schemas.subscription_plan import SubscriptionPlanCreate, SubscriptionPlanResponse

router = APIRouter()

@router.get("/", response_model=List[SubscriptionPlanResponse])
async def read_subscription_plans() -> Any:
    """
    Get all active subscription plans (Public).
    Auto-populates default plans if none exist.
    """
    plans = await SubscriptionPlan.find(SubscriptionPlan.is_active == True).to_list()
    
    if not plans:
        # Default plans data
        default_plans = [
            {
                "name": "Starter",
                "code": "starter",
                "description": "For small businesses just getting started",
                "price_monthly": 0.0,
                "price_yearly": 0.0,
                "features": ["Single user", "Up to 5 vendors", "Basic reporting", "Email support"],
                "max_vendors": 5,
                "max_users": 1,
                "max_products": 100
            },
            {
                "name": "Professional",
                "code": "professional",
                "description": "For growing businesses",
                "price_monthly": 29.0,
                "price_yearly": 290.0,
                "features": ["Up to 5 users", "Unlimited vendors", "Advanced reporting", "Priority support", "Multi-warehouse"],
                "max_vendors": 1000,
                "max_users": 5,
                "max_products": 5000
            },
            {
                "name": "Enterprise",
                "code": "enterprise",
                "description": "For large organizations",
                "price_monthly": 99.0,
                "price_yearly": 990.0,
                "features": ["Unlimited users", "Unlimited vendors", "Custom reporting", "Dedicated account manager", "API access"],
                "max_vendors": 1000000,
                "max_users": 1000000,
                "max_products": 1000000
            }
        ]
        
        # Create plans
        new_plans = []
        for plan_data in default_plans:
            plan = SubscriptionPlan(**plan_data)
            await plan.create()
            new_plans.append(plan)
            
        return new_plans
        
    return plans

@router.post("/", response_model=SubscriptionPlanResponse)
async def create_subscription_plan(plan_in: SubscriptionPlanCreate) -> Any:
    """
    Create a new subscription plan (Admin - made public for seed/dev).
    """
    plan = await SubscriptionPlan.find_one(SubscriptionPlan.code == plan_in.code)
    if plan:
        raise HTTPException(
            status_code=400,
            detail="Subscription plan with this code already exists",
        )
    plan = SubscriptionPlan(**plan_in.model_dump())
    await plan.create()
    return plan
