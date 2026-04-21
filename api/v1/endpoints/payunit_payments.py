from typing import Any
from fastapi import APIRouter, HTTPException, Request
from beanie import PydanticObjectId
from datetime import datetime
import logging

from models.organization import Organization
from models.organization_payment import OrganizationPayment, OPStatus, OPaymentType, OPaymentMethod
from models.subscription_plan import SubscriptionPlan
from schemas.payunit import PayUnitCollectRequest, PayUnitWebhookPayload
from services.payunit import payunit_service, PayUnitService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/collect", response_model=dict)
async def initiate_payunit_collect(
    request_in: PayUnitCollectRequest,
) -> Any:
    """
    Step 1: User chooses a plan, provider, and provides phone number.
    This triggers a PayUnit mobile money collection.
    """
    # 1. Verify Organization exists
    org = await Organization.find_one({"_id": PydanticObjectId(request_in.organization_id)})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # 2. Verify Plan exists
    plan = await SubscriptionPlan.find_one({"code": request_in.subscription_plan_id})
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")

    # 3. Validate gateway
    if request_in.gateway not in ("CM_MTNMOMO", "CM_ORANGE"):
        raise HTTPException(status_code=400, detail="Invalid gateway. Use CM_MTNMOMO or CM_ORANGE.")

    # 4. Generate transaction_id encoding metadata
    # Format: orgId|planCode|billingPeriod__uniqueHash
    metadata_prefix = f"{org.id}|{plan.code}|{request_in.billing_period}"
    transaction_id = PayUnitService.generate_transaction_id(prefix=metadata_prefix)

    # 5. Format phone number
    phone = str(request_in.phone_number).replace(" ", "")
    if phone.startswith("+"):
        phone = phone[1:]
    if len(phone) == 9:
        phone = "237" + phone

    # 6. Trigger PayUnit Collection
    try:
        response = payunit_service.initiate_payment(
            amount=request_in.amount,
            phone_number=phone,
            gateway=request_in.gateway,
            transaction_id=transaction_id,
            description=request_in.description or f"Subscription for {org.name}",
        )

        # We intentionally do NOT save an OrganizationPayment here.
        # It will only be created on a SUCCESSFUL webhook callback.

        return {
            "status": "pending",
            "message": "Payment initiated. Please authorize on your phone.",
            "transaction_id": transaction_id,
        }
    except Exception as e:
        logger.error(f"PayUnit collection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate payment: {str(e)}")


@router.post("/webhook")
async def payunit_webhook(request: Request):
    """
    Webhook received from PayUnit when payment status changes (notify_url callback).
    """
    # Accept raw body to log it, then parse
    body = await request.json()
    logger.info(f"Received PayUnit webhook raw body: {body}")

    payload = PayUnitWebhookPayload(**body)

    # Resolve transaction_id from possible field names
    tx_id = payload.transaction_id or payload.t_id or body.get("transaction_id") or body.get("t_id", "")
    # Resolve status
    status = payload.status or payload.transaction_status or body.get("status") or body.get("transaction_status", "")
    # Resolve amount
    amount = payload.amount or payload.transaction_amount or body.get("amount") or body.get("transaction_amount", 0)

    if not tx_id:
        logger.warning(f"PayUnit webhook missing transaction_id: {body}")
        return {"status": "ignored", "reason": "missing_transaction_id"}

    # Only process successful payments
    status_upper = str(status).upper()
    if status_upper not in ["SUCCESS", "SUCCESSFUL"]:
        logger.info(f"PayUnit payment {status} for tx {tx_id}. No DB record created.")
        return {"status": "ignored", "reason": f"payment_status_{status}"}

    # Extract metadata from transaction_id  (format: orgId|planCode|billingPeriod__uniqueHash)
    if "__" in tx_id:
        metadata_part = tx_id.split("__")[0]
    else:
        metadata_part = tx_id

    parts = metadata_part.split("|")
    if len(parts) >= 3:
        org_id = parts[0]
        plan_code = parts[1]
        billing_period = parts[2]
    else:
        logger.warning(f"Invalid transaction_id metadata format: {tx_id}")
        return {"status": "ignored", "reason": "invalid_metadata"}

    # 1. Check if we already processed this transaction
    existing = await OrganizationPayment.find_one({"reference_number": tx_id})
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

    # 3. Create the COMPLETED payment record
    payment = OrganizationPayment(
        organization_id=org_id,
        subscription_plan_id=plan_code,
        amount=float(amount),
        currency="XAF",
        payment_method=OPaymentMethod.MOBILE_MONEY,
        payment_type=OPaymentType.SUBSCRIPTION,
        billing_period=billing_period,
        status=OPStatus.COMPLETED,
        reference_number=tx_id,
        payment_date=datetime.utcnow(),
        notes=f"PayUnit payment completed."
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
    logger.info(f"Organization {org.name} subscription activated via PayUnit webhook.")

    return {"status": "success", "message": "Subscription activated"}


@router.get("/status/{transaction_id}")
async def check_payment_status(transaction_id: str):
    """
    Manual status check (polling fallback).
    First checks local DB, then queries PayUnit API.
    """
    # Quick check: did the webhook already process this?
    payment = await OrganizationPayment.find_one({"reference_number": transaction_id})
    if payment and payment.status == OPStatus.COMPLETED:
        return {"status": "completed", "message": "Payment verified successfully."}

    try:
        payunit_status = payunit_service.get_transaction_status(transaction_id)
        raw_status = payunit_status.get("status") or payunit_status.get("transaction_status", "PENDING")

        # Normalize status
        normalized = raw_status.upper()
        if normalized in ["SUCCESS", "SUCCESSFUL"]:
            normalized = "SUCCESSFUL"

        return {
            "status": normalized,
            "transaction_id": transaction_id,
        }
    except Exception as e:
        logger.error(f"Failed to fetch PayUnit status for {transaction_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to retrieve payment status")
