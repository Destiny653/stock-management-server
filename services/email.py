import logging
from typing import List, Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from core.config import settings

logger = logging.getLogger(__name__)

def _get_mail_config() -> ConnectionConfig:
    """Build mail config at call-time so env changes are picked up."""
    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=settings.USE_CREDENTIALS,
        VALIDATE_CERTS=settings.VALIDATE_CERTS
    )

async def send_email(
    email_to: List[EmailStr], 
    subject: str, 
    html_content: str, 
    raise_on_failure: bool = True
) -> bool:
    """
    Send an email using configured SMTP settings.
    Returns True if successful, False otherwise (if raise_on_failure is False).
    """
    try:
        message = MessageSchema(
            subject=subject,
            recipients=email_to,
            body=html_content,
            subtype=MessageType.html
        )
        conf = _get_mail_config()
        fm = FastMail(conf)
        await fm.send_message(message)
        logger.info(f"Successfully sent email to {email_to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {email_to}: {str(e)}", exc_info=True)
        if raise_on_failure:
            raise e
        return False
