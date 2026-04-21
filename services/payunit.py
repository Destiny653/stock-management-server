import requests
import base64
import uuid
import logging
import json
from core.config import settings

logger = logging.getLogger(__name__)

PAYUNIT_BASE_URL = "https://gateway.payunit.net"


class PayUnitService:
    def __init__(self):
        self.api_key = settings.PAYUNIT_API_KEY
        self.mode = settings.PAYUNIT_MODE  # "test" or "live"
        self.return_url = settings.PAYUNIT_RETURN_URL
        self.notify_url = settings.PAYUNIT_NOTIFY_URL

        # Basic Auth header
        auth_str = f"{settings.PAYUNIT_API_USER}:{settings.PAYUNIT_API_PASSWORD}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        self.headers = {
            "x-api-key": self.api_key,
            "mode": self.mode,
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_auth}",
        }

    @staticmethod
    def generate_transaction_id(prefix: str = "") -> str:
        """Generate a unique transaction ID, optionally with metadata prefix."""
        unique = uuid.uuid4().hex[:12]
        if prefix:
            return f"{prefix}__{unique}"
        return unique

    def initiate_payment(
        self,
        amount: float,
        phone_number: str,
        gateway: str,
        transaction_id: str,
        description: str = "Subscription Payment",
        return_url: str = None,
        notify_url: str = None,
    ) -> dict:
        """
        Initiate a mobile money collection via PayUnit.
        gateway should be 'CM_MTN' or 'CM_ORANGE'.
        Returns the PayUnit API response dict.
        """
        url = f"{PAYUNIT_BASE_URL}/api/gateway/makepayment"

        payload = {
            "gateway": gateway,
            "amount": int(amount),
            "transaction_id": transaction_id,
            "phone_number": str(phone_number),
            "currency": "XAF",
            "paymentType": "button",
            "description": description,
            "return_url": return_url or self.return_url,
            "notify_url": notify_url or self.notify_url,
        }

        logger.info(f"PayUnit initiate_payment: gateway={gateway}, amount={amount}, tx={transaction_id}")

        try:
            response = requests.post(url, headers=self.headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info(f"PayUnit response: {data}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"PayUnit initiate_payment error: {str(e)}")
            raise e

    def get_transaction_status(self, transaction_id: str) -> dict:
        """
        Query the status of an existing transaction.
        Returns dict with status info.
        """
        url = f"{PAYUNIT_BASE_URL}/api/gateway/paymentstatus/{transaction_id}"

        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            logger.info(f"PayUnit status for {transaction_id}: {data}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"PayUnit get_transaction_status error for {transaction_id}: {str(e)}")
            raise e


payunit_service = PayUnitService()
