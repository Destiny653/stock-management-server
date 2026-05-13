from typing import Any
from fastapi import APIRouter, HTTPException, Request
from beanie import PydanticObjectId
from datetime import datetime
import logging

from models.organization import Organization, OrganizationStatus
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

    # 5. Format phone number — PayUnit expects 9 digits without country code (e.g. 67xxxxxxx)
    phone = str(request_in.phone_number).replace(" ", "")
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith("237") and len(phone) == 12:
        phone = phone[3:]  # Strip country code

    # 6. Create the PENDING payment record immediately
    # This gives us a solid DB ID to use as transaction_id
    payment = OrganizationPayment(
        organization_id=str(org.id),
        subscription_plan_id=plan.code,
        amount=float(request_in.amount),
        currency="XAF",
        payment_method=OPaymentMethod.MOBILE_MONEY,
        payment_type=OPaymentType.SUBSCRIPTION,
        billing_period=request_in.billing_period,
        status=OPStatus.PENDING,
        reference_number=None, # Will set to PayUnit tx_id
        payment_date=datetime.utcnow(),
        notes=f"PayUnit payment initiated for {plan.name} ({request_in.billing_period})"
    )
    await payment.create()

    # 7. Generate a short transaction_id (PayUnit requires < 20 chars)
    # We'll use a short hash/prefix + random string and store it in reference_number
    import uuid
    transaction_id = f"TX{uuid.uuid4().hex[:14]}".upper() # 2 + 14 = 16 chars
    payment.reference_number = transaction_id
    await payment.save()

    # 8. Trigger PayUnit Collection
    try:
        response = payunit_service.initiate_payment(
            amount=request_in.amount,
            phone_number=phone,
            gateway=request_in.gateway,
            transaction_id=transaction_id,
        )

        return {
            "status": "pending",
            "message": "Payment initiated. Please authorize on your phone.",
            "transaction_id": transaction_id,
        }
    except Exception as e:
        # Mark payment as failed if initiation fails
        payment.status = OPStatus.FAILED
        payment.notes = f"Initiation failed: {str(e)}"
        await payment.save()
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

    # 1. Find the payment record by transaction_id (which is our DB ID)
    payment = None
    try:
        # Try finding by ID first
        payment = await OrganizationPayment.get(PydanticObjectId(tx_id))
    except Exception:
        # Fallback to reference_number check
        payment = await OrganizationPayment.find_one({"reference_number": tx_id})

    if not payment:
        logger.error(f"PayUnit webhook: Payment {tx_id} not found in DB.")
        return {"status": "ignored", "reason": "payment_not_found"}

    if payment.status == OPStatus.COMPLETED:
        return {"status": "success", "message": "Already processed"}

    # 2. Fetch dependencies
    org = await Organization.get(PydanticObjectId(payment.organization_id))
    if not org:
        logger.error(f"Organization {payment.organization_id} not found during webhook.")
        return {"status": "failed", "reason": "org_not_found"}

    plan = await SubscriptionPlan.find_one({"code": payment.subscription_plan_id})
    if not plan:
        logger.error(f"Plan {payment.subscription_plan_id} not found during webhook.")
        return {"status": "failed", "reason": "plan_not_found"}

    # 3. Update the payment record to COMPLETED
    payment.status = OPStatus.COMPLETED
    payment.amount = float(amount)
    payment.payment_date = datetime.utcnow()
    payment.notes = f"PayUnit payment completed successfully. Gateway: {payload.provider_name or 'N/A'}"
    await payment.save()

    # 4. Update Organization subscription
    org.subscription_plan = plan.code
    org.subscription_plan_id = str(plan.id)
    org.billing_cycle = payment.billing_period or "monthly"
    org.subscription_interval = payment.billing_period or "monthly"
    org.storage_capacity_kb = plan.storage_capacity_kb
    org.max_vendors = plan.max_vendors
    org.max_users = plan.max_users
    org.status = OrganizationStatus.ACTIVE
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
