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


async def create_org_approved_notification(
    *,
    organization: Organization,
    action_url: Optional[str] = None,
) -> bool:
    """
    Create a dashboard alert (and email) notifying an organization that they are approved.
    Returns True only when we created a new alert (idempotency).
    """
    title = "Organization approved"
    existing = await Alert.find_one(
        {
            "organization_id": str(organization.id),
            "type": AlertType.ORG_APPROVED,
            "title": title,
        }
    )
    if existing:
        return False

    message = (
        "Your organization has been approved and you can now start running transactions."
    )

    alert = Alert(
        organization_id=str(organization.id),
        type=AlertType.ORG_APPROVED,
        priority=AlertPriority.HIGH,
        title=title,
        message=message,
        action_url=action_url,
    )
    await alert.create()

    if organization.email:
        try:
            await send_email(
                email_to=[organization.email],
                subject="StockFlow: Your organization is approved",
                html_content=f"""
                <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <div style="max-width: 640px; margin: 0 auto; padding: 20px;">
                            <h2 style="color:#0d9488;">Organization Approved</h2>
                            <p>Hi {organization.name},</p>
                            <p>Your organization has been approved. You can now start using StockFlow to run transactions.</p>
                            <p style="margin-top: 18px; color:#64748b; font-size: 13px;">
                                If you have any issues accessing features, contact support.
                            </p>
                        </div>
                    </body>
                </html>
                """,
            )
        except Exception:
            pass

    return True


async def create_trial_extended_notification(
    *,
    organization: Organization,
    new_trial_end: datetime,
    days_added: int,
    action_url: Optional[str] = None,
) -> bool:
    title = f"Free trial extended by {days_added} day(s)"
    message = f"Your free trial now ends on {new_trial_end.date().isoformat()}."

    alert = Alert(
        organization_id=str(organization.id),
        type=AlertType.TRIAL_EXTENDED,
        priority=AlertPriority.HIGH,
        title=title,
        message=message,
        action_url=action_url,
    )
    await alert.create()

    if organization.email:
        try:
            await send_email(
                email_to=[organization.email],
                subject="StockFlow: Free trial extended",
                html_content=f"""
                <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <div style="max-width: 640px; margin: 0 auto; padding: 20px;">
                            <h2 style="color:#0d9488;">Free Trial Extended</h2>
                            <p>Hi {organization.name},</p>
                            <p>Your free trial has been extended by <strong>{days_added}</strong> day(s).</p>
                            <p>New trial expiry date: <strong>{new_trial_end.date().isoformat()}</strong></p>
                        </div>
                    </body>
                </html>
                """,
            )
        except Exception:
            pass
    return True


async def create_storage_capacity_changed_notification(
    *,
    organization: Organization,
    new_capacity_kb: int,
    action_url: Optional[str] = None,
) -> bool:
    title = "Storage capacity updated"
    message = f"Your organization storage capacity is now {new_capacity_kb} KB."

    alert = Alert(
        organization_id=str(organization.id),
        type=AlertType.STORAGE_QUOTA_CHANGED,
        priority=AlertPriority.MEDIUM,
        title=title,
        message=message,
        action_url=action_url,
    )
    await alert.create()

    if organization.email:
        try:
            await send_email(
                email_to=[organization.email],
                subject="StockFlow: Storage capacity updated",
                html_content=f"""
                <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <div style="max-width: 640px; margin: 0 auto; padding: 20px;">
                            <h2 style="color:#0284c7;">Storage Capacity Updated</h2>
                            <p>Hi {organization.name},</p>
                            <p>Your storage quota has been updated to <strong>{new_capacity_kb} KB</strong>.</p>
                        </div>
                    </body>
                </html>
                """,
            )
        except Exception:
            pass
    return True

