import stripe
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class StripeService:
    @staticmethod
    def create_payment_intent(
        amount: int, 
        currency: str = "xaf", 
        order_id: str = "", 
        customer_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Payment Intent.
        Amount should be in the smallest currency unit (e.g., cents for USD, units for XAF).
        """
        try:
            # Stripe supports XAF (Cameroon) but has some limitations on certain payment methods
            # payment_method_types can include 'card', 'crypto' (via specific providers/integrations), etc.
            # But the 'automatic_payment_methods' is usually the best way now.
            
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency.lower(),
                automatic_payment_methods={
                    'enabled': True,
                },
                metadata={
                    "order_id": order_id
                },
                receipt_email=customer_email
            )
            return {
                "client_secret": intent.client_secret,
                "id": intent.id,
                "status": intent.status
            }
        except Exception as e:
            print(f"Stripe Payment Intent Error: {str(e)}")
            raise e

    @staticmethod
    def verify_webhook(payload: bytes, sig_header: str) -> Optional[Dict[str, Any]]:
        """Verify Stripe webhook signature and return the event."""
        endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
            return event
        except Exception as e:
            print(f"Stripe Webhook Verification Error: {str(e)}")
            return None
