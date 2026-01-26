from typing import Any, List
from fastapi import APIRouter, HTTPException
from models.subscription_plan import SubscriptionPlan
from schemas.subscription_plan import SubscriptionPlanCreate, SubscriptionPlanResponse

router = APIRouter()

@router.get("/", response_model=List[SubscriptionPlanResponse])
async def read_subscription_plans() -> Any:
    """
    Get all active subscription plans (Public).
    """
    plans = await SubscriptionPlan.find(SubscriptionPlan.is_active == True).to_list()
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
