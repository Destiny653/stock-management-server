from campay.sdk import Client as CamPayClient
from core.config import settings
import logging

logger = logging.getLogger(__name__)

class CampayService:
    def __init__(self):
        self.client = CamPayClient({
            "app_username": settings.CAMPAY_USERNAME,
            "app_password": settings.CAMPAY_PASSWORD,
            "environment": settings.CAMPAY_ENVIRONMENT
        })

    def collect_payment(self, amount: float, from_phone: str, description: str, external_reference: str = None):
        """
        Initiates a USSD collection.
        Returns the transaction reference.
        """
        try:
            # Ensure phone number is string and has country code
            phone = str(from_phone)
            if not phone.startswith("237"):
                # Default to Cameroon if missing and length is 9
                if len(phone) == 9:
                    phone = "237" + phone
            
            collect_data = {
                "amount": str(int(amount)), # Campay usually expects integer strings for XAF
                "currency": "XAF",
                "from": phone,
                "description": description,
                "external_reference": external_reference
            }
            
            logger.info(f"Initiating Campay collect: {collect_data}")
            response = self.client.collect(collect_data)
            logger.info(f"Campay collect response: {response}")
            
            return response
        except Exception as e:
            logger.error(f"Error in Campay collect_payment: {str(e)}")
            raise e

    def get_transaction_status(self, reference: str):
        """
        Check the status of a transaction using its reference.
        """
        try:
            status = self.client.get_transaction_status(reference)
            return status
        except Exception as e:
            logger.error(f"Error checking Campay transaction status: {str(e)}")
            raise e

campay_service = CampayService()
