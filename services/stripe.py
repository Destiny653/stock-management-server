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
        customer_email: Optional[str] = None,
        stripe_account: Optional[str] = None,
        application_fee_amount: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Payment Intent.
        If stripe_account is provided, a Direct Charge is made on the connected account.
        Amount should be in the smallest currency unit (e.g., cents for USD, units for XAF).
        """
        try:
            kwargs = {
                "amount": amount,
                "currency": currency.lower(),
                "automatic_payment_methods": {'enabled': True},
                "metadata": {"order_id": order_id},
                "receipt_email": customer_email
            }
            
            if stripe_account:
                kwargs["stripe_account"] = stripe_account
                if application_fee_amount is not None and application_fee_amount > 0:
                    kwargs["application_fee_amount"] = application_fee_amount
                    
            intent = stripe.PaymentIntent.create(**kwargs)
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

    @staticmethod
    def create_connect_account() -> str:
        """Create a new Stripe Connect Standard account and return its ID."""
        account = stripe.Account.create(type="standard")
        return account.id

    @staticmethod
    def create_account_link(account_id: str, return_url: str, refresh_url: str) -> str:
        """Generate an onboarding link for the connected account."""
        account_link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
        )
        return account_link.url

    @staticmethod
    def check_account_status(account_id: str) -> bool:
        """Check if the connected account can receive charges."""
        try:
            account = stripe.Account.retrieve(account_id)
            return account.charges_enabled
        except Exception as e:
            print(f"Stripe Connect Check Error: {str(e)}")
            return False
