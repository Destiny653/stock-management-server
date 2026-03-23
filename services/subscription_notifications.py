from __future__ import annotations

from datetime import datetime
from typing import Optional

from models.alert import Alert, AlertType, AlertPriority
from models.organization import Organization
from services.email import send_email


async def create_subscription_expiry_alert(
    *,
    organization: Organization,
    expiry_date: datetime,
    days_left: int,
    action_url: Optional[str] = None,
) -> bool:
    """
    Create a dashboard alert (and email) for a subscription/trial expiry.
    Returns True only when we created a new alert (idempotency).
    """
    title = f"Subscription expiring on {expiry_date.date().isoformat()}"

    existing = await Alert.find_one(
        {
            "organization_id": str(organization.id),
            "type": AlertType.SUBSCRIPTION_EXPIRING,
            "title": title,
        }
    )
    if existing:
        return False

    message = (
        f"Your subscription will expire on {expiry_date.date().isoformat()}. "
        f"Payment must be completed to keep using the platform."
    )

    alert = Alert(
        organization_id=str(organization.id),
        type=AlertType.SUBSCRIPTION_EXPIRING,
        priority=AlertPriority.CRITICAL if days_left <= 3 else AlertPriority.HIGH,
        title=title,
        message=message,
        action_url=action_url,
    )
    await alert.create()

    # Email notifications to the organization's contact email (if provided)
    if organization.email:
        try:
            await send_email(
                email_to=[organization.email],
                subject="StockFlow subscription expiry notice",
                html_content=f"""
                <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <div style="max-width: 640px; margin: 0 auto; padding: 20px;">
                            <h2 style="color:#dc2626;">Subscription Expiry Notice</h2>
                            <p>Hi {organization.name},</p>
                            <p>Your subscription will expire on <strong>{expiry_date.date().isoformat()}</strong>.</p>
                            <p>Please complete payment to avoid service interruption.</p>
                            <p style="margin-top: 18px; color:#64748b; font-size: 13px;">
                                Days left: {days_left}
                            </p>
                        </div>
                    </body>
                </html>
                """,
            )
        except Exception:
            # Avoid breaking API access if email fails; alert still exists in dashboard.
            pass

    return True

