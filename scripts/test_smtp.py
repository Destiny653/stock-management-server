import asyncio
import os
import sys
from typing import List
from pydantic import EmailStr
import logging

# Add the server directory to sys.path to import core settings
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.config import settings
from services.email import send_email

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_connectivity():
    """
    Test SMTP connectivity by attempting to send a test email.
    Usage: python scripts/test_smtp.py [recipient@example.com]
    """
    recipient = sys.argv[1] if len(sys.argv) > 1 else settings.MAIL_FROM
    
    logger.info("--- SMTP Connectivity Diagnostic ---")
    logger.info(f"Server: {settings.MAIL_SERVER}")
    logger.info(f"Port: {settings.MAIL_PORT}")
    logger.info(f"User: {settings.MAIL_USERNAME}")
    logger.info(f"From: {settings.MAIL_FROM}")
    logger.info(f"STARTTLS: {settings.MAIL_STARTTLS}")
    logger.info(f"SSL/TLS: {settings.MAIL_SSL_TLS}")
    logger.info(f"Recipient: {recipient}")
    logger.info("-------------------------------------")
    
    try:
        logger.info("Attempting to send test email...")
        await send_email(
            email_to=[recipient],
            subject="StockFlow SMTP Test",
            html_content="<h1>StockFlow SMTP Test</h1><p>If you are reading this, your SMTP configuration is working correctly from this environment.</p>"
        )
        logger.info("✅ SUCCESS: Test email sent successfully!")
    except Exception as e:
        logger.error("❌ FAILURE: Could not send test email.")
        logger.error(f"Error Type: {type(e).__name__}")
        logger.error(f"Error Detail: {str(e)}")
        
        if "Connection refused" in str(e):
            logger.warning("Suggestion: The SMTP server is refusing the connection. This often happens if Render blocks the outbound port (e.g. port 25) or if the server address is incorrect.")
        elif "Authentication" in str(e) or "credentials" in str(e).lower():
            logger.warning("Suggestion: Authentication failed. If using Gmail, make sure you are using an 'App Password', not your regular login password.")
        elif "timeout" in str(e).lower():
            logger.warning("Suggestion: Connection timed out. This likely indicates a firewall or network blocking issue in the current environment.")
            
if __name__ == "__main__":
    if not settings.MAIL_USERNAME or settings.MAIL_USERNAME == "user@example.com":
        logger.error("Error: MAIL_USERNAME is not configured correctly in .env. Please update it before running this test.")
        sys.exit(1)
        
    asyncio.run(test_connectivity())
