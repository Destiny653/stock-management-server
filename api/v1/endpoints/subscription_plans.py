from typing import Any, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from api import deps
from models.user import User
from models.subscription_plan import SubscriptionPlan
from schemas.subscription_plan import SubscriptionPlanCreate, SubscriptionPlanResponse, SubscriptionPlanUpdate

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
                "currency": "XAF",
                "features": ["Single user", "Up to 5 vendors", "Basic reporting", "Email support"],
                "max_vendors": 5,
                "max_users": 1,
                "max_products": 100,
                "max_locations": 1,
            },
            {
                "name": "Professional",
                "code": "professional",
                "description": "For growing businesses",
                "price_monthly": 15000.0,
                "price_yearly": 150000.0,
                "currency": "XAF",
                "features": ["Up to 5 users", "Unlimited vendors", "Advanced reporting", "Priority support", "Multi-warehouse"],
                "max_vendors": 1000,
                "max_users": 5,
                "max_products": 5000,
                "max_locations": 5,
            },
            {
                "name": "Enterprise",
                "code": "enterprise",
                "description": "For large organizations",
                "price_monthly": 50000.0,
                "price_yearly": 500000.0,
                "currency": "XAF",
                "features": ["Unlimited users", "Unlimited vendors", "Custom reporting", "Dedicated account manager", "API access"],
                "max_vendors": 1000000,
                "max_users": 1000000,
                "max_products": 1000000,
                "max_locations": 1000000,
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
async def create_subscription_plan(
    plan_in: SubscriptionPlanCreate,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
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


@router.put("/{plan_id}", response_model=SubscriptionPlanResponse)
async def update_subscription_plan(
    plan_id: str,
    plan_in: SubscriptionPlanUpdate,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    plan = await SubscriptionPlan.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")

    update_data = plan_in.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    await plan.update({"$set": update_data})
    await plan.save()
    return plan
