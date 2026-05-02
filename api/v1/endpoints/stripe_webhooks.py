import logging
from typing import Any
from fastapi import APIRouter, Request, HTTPException, Header
from services.stripe import StripeService
from models.storefront_order import StorefrontOrder, StorefrontOrderStatus

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None)
) -> Any:
    """
    Handle Stripe webhooks for storefront payments.
    """
    payload = await request.body()
    
    try:
        event = StripeService.construct_event(payload, stripe_signature)
    except Exception as e:
        logger.error(f"Stripe webhook signature verification failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    logger.info(f"Received Stripe webhook: {event_type}")

    if event_type == "payment_intent.succeeded":
        await handle_payment_intent_succeeded(data_object)
    elif event_type == "payment_intent.payment_failed":
        await handle_payment_intent_failed(data_object)

    return {"status": "success"}


async def handle_payment_intent_succeeded(payment_intent: dict):
    """Update order status to PAID when payment succeeds."""
    order_id = payment_intent.get("metadata", {}).get("order_id")
    pi_id = payment_intent.get("id")
    
    if not order_id:
        logger.warning(f"PaymentIntent {pi_id} succeeded but missing order_id in metadata")
        return

    order = await StorefrontOrder.find_one({"order_ref": order_id})
    if order:
        order.status = StorefrontOrderStatus.PAID
        order.stripe_payment_intent_id = pi_id
        await order.save()
        logger.info(f"Order {order_id} updated to PAID via Stripe webhook")
    else:
        logger.error(f"Order {order_id} not found for successful payment intent {pi_id}")


async def handle_payment_intent_failed(payment_intent: dict):
    """Log payment failure."""
    order_id = payment_intent.get("metadata", {}).get("order_id")
    error_message = payment_intent.get("last_payment_error", {}).get("message")
    logger.warning(f"Payment failed for order {order_id}: {error_message}")
