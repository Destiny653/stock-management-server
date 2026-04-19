from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request
from beanie import PydanticObjectId
from datetime import datetime, timedelta
import logging

from models.organization import Organization
from models.organization_payment import OrganizationPayment, OPStatus, OPaymentType, OPaymentMethod
from models.subscription_plan import SubscriptionPlan
from schemas.campay import CampayCollectRequest, CampayWebhookPayload
from services.campay import campay_service
from api import deps

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/collect", response_model=dict)
async def initiate_campay_collect(
    request_in: CampayCollectRequest,
    # public registration might not have a current user if they are just signing up
    # but we need the organization_id
) -> Any:
    """
    Step 1: User chooses a plan and provides phone number.
    This creates a pending payment and triggers USSD.
    """
    # 1. Verify Organization exists
    org = await Organization.find_one({"_id": PydanticObjectId(request_in.organization_id)})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # 2. Verify Plan exists
    plan = await SubscriptionPlan.find_one({"code": request_in.subscription_plan_id})
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")

    # 3. Trigger Campay Collection
    try:
        # Encode metadata into external_reference so webhook can process it
        encoded_ref = f"{org.id}|{plan.code}|{request_in.billing_period}"
        response = campay_service.collect_payment(
            amount=request_in.amount,
            from_phone=request_in.from_phone,
            description=request_in.description or f"Subscription for {org.name}",
            external_reference=encoded_ref
        )
        
        # Notice: We intentionally do NOT save an OrganizationPayment here.
        # It will only be created on a SUCCESSFUL webhook callback.
        
        return {
            "status": "pending",
            "message": "USSD prompt sent to your phone. Please authorize the payment.",
            "reference": response.get("reference")
        }
    except Exception as e:
        logger.error(f"Campay collection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate payment: {str(e)}")

@router.post("/webhook")
async def campay_webhook(payload: CampayWebhookPayload):
    """
    Webhook received from Campay when payment status changes.
    """
    logger.info(f"Received Campay webhook: {payload}")
    
    if payload.status not in ["SUCCESSFUL"]:
        logger.info(f"Campay payment {payload.status}. No DB record created.")
        return {"status": "ignored", "reason": "unconfirmed_payment"}

    # Extract metadata encoded into external_reference
    ext_ref = payload.external_reference
    if not ext_ref or "|" not in ext_ref:
        logger.warning(f"Invalid external_reference format in webhook: {ext_ref}")
        return {"status": "ignored", "reason": "invalid_metadata"}
        
    parts = ext_ref.split("|")
    if len(parts) >= 3:
        org_id = parts[0]
        plan_code = parts[1]
        billing_period = parts[2]
    else:
        logger.warning(f"Incomplete parameters in external_reference: {ext_ref}")
        return {"status": "ignored", "reason": "incomplete_metadata"}

    # 1. Check if we already processed this reference
    existing = await OrganizationPayment.find_one({"reference_number": payload.reference})
    if existing:
        return {"status": "success", "message": "Already processed"}

    # 2. Fetch dependencies
    org = await Organization.find_one({"_id": PydanticObjectId(org_id)})
    if not org:
        logger.error(f"Organization {org_id} not found during webhook.")
        return {"status": "failed", "reason": "org_not_found"}

    plan = await SubscriptionPlan.find_one({"code": plan_code})
    if not plan:
        logger.error(f"Plan {plan_code} not found during webhook.")
        return {"status": "failed", "reason": "plan_not_found"}

    # 3. Create the COMPLETED payment record directly
    payment = OrganizationPayment(
        organization_id=org_id,
        subscription_plan_id=plan_code,
        amount=payload.amount,
        currency=payload.currency or "XAF",
        payment_method=OPaymentMethod.MOBILE_MONEY,
        payment_type=OPaymentType.SUBSCRIPTION,
        billing_period=billing_period,
        status=OPStatus.COMPLETED,
        reference_number=payload.reference,
        payment_date=datetime.utcnow(),
        notes=f"Campay USSD completed."
    )
    await payment.create()

    # 4. Update Organization subscription
    org.subscription_plan = plan.code
    org.subscription_plan_id = str(plan.id)
    org.billing_cycle = billing_period
    org.subscription_interval = billing_period
    org.storage_capacity_kb = plan.storage_capacity_kb
    org.max_vendors = plan.max_vendors
    org.max_users = plan.max_users
    org.status = "active"
    org.updated_at = datetime.utcnow()
    await org.save()
    logger.info(f"Organization {org.name} subscription successfully updated via webhook.")

    return {"status": "success", "message": "Subscription activated"}

@router.get("/status/{reference}")
async def check_payment_status(reference: str):
    """
    Manual status check (polling fallback).
    Because we don't save pending transactions, we exclusively query the Campay API.
    """
    # Optional: Quick check the DB if the webhook already beat us to it
    payment = await OrganizationPayment.find_one({"reference_number": reference})
    if payment and payment.status == OPStatus.COMPLETED:
         return {"status": "completed", "message": "Payment verified successfully locally."}

    try:
        campay_status = campay_service.get_transaction_status(reference)
        return {
            "status": campay_status.get("status"),
            "reference": reference
        }
    except Exception as e:
        logger.error(f"Failed to fetch status from Campay for reference {reference}: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to retrieve payment status")
