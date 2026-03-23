"""API dependencies"""
from typing import Optional
from datetime import datetime
import calendar
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from core.config import settings
from models.user import User, UserRole
from schemas.token import TokenPayload
from models.organization import Organization, OrganizationStatus
from models.organization_payment import OrganizationPayment
from services.subscription_notifications import create_subscription_expiry_alert

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token",
    auto_error=False
)


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(reusable_oauth2)
) -> User:
    """Get current user from JWT token"""
    if not token:
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    user = await User.get(token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active superuser (platform-staff with admin role)"""
    if current_user.user_type != "platform-staff" or current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user


async def get_organization_id(
    organization_id: Optional[str] = None,
    request: Request,
    current_user: User = Depends(get_current_active_user),
) -> Optional[str]:
    """
    Get organization ID - either from query param or from user's organization.
    Enforces that business-staff can only access their own organization.
    Platform-staff can access any organization.
    """
    # Platform staff can access any organization
    if current_user.user_type == "platform-staff":
        return organization_id

    # For non-superadmins, they MUST have an organization_id
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to any organization"
        )
    
    # If they provided an organization_id, it MUST match their own
    if organization_id and organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this organization's data"
        )

    org_id = current_user.organization_id

    # Always allow access to alerts so organizations can see billing/expiry messages
    # even if their subscription is expired.
    if request and request.url and request.url.path and request.url.path.startswith(f"{settings.API_V1_STR}/alerts"):
        return org_id

    # Enforce paywall/approval for business-staff requests.
    org = await Organization.get(org_id)
    now = datetime.utcnow()

    # Approval gate (must be approved by platform-staff before services start)
    if org.status == OrganizationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is awaiting approval",
        )

    # Hard blocks (suspended/inactive)
    if org.status in (OrganizationStatus.SUSPENDED, OrganizationStatus.INACTIVE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization subscription is not active",
        )

    # Trial gate
    trial_expiry = org.trial_ends_at
    if trial_expiry and now <= trial_expiry:
        days_left = (trial_expiry.date() - now.date()).days
        if days_left <= 7:
            await create_subscription_expiry_alert(
                organization=org,
                expiry_date=trial_expiry,
                days_left=days_left,
                action_url=f"OrganizationMembers?id={org.id}",
            )
        return org_id

    # Subscription gate based on latest completed organization payment.
    # Note: frontend sets billing cycle, but payments can still be used to compute next billing.
    last_completed = await OrganizationPayment.find(
        {"organization_id": org_id, "status": "completed"}
    ).sort("-created_at").limit(1).to_list()

    subscription_expiry: Optional[datetime] = None
    if last_completed:
        last_payment = last_completed[0]
        base_date = last_payment.payment_date or last_payment.created_at
        next_billing_date: Optional[datetime] = None

        if org.billing_cycle == "yearly":
            # Keep same month/day when possible.
            year = base_date.year + 1
            day = min(base_date.day, calendar.monthrange(year, base_date.month)[1])
            next_billing_date = base_date.replace(year=year, day=day)
        else:
            # monthly - keep same day when possible
            months = 1
            month_index = base_date.month - 1 + months
            year = base_date.year + month_index // 12
            month = (month_index % 12) + 1
            day = min(base_date.day, calendar.monthrange(year, month)[1])
            next_billing_date = base_date.replace(year=year, month=month, day=day)

        if next_billing_date and now <= next_billing_date:
            subscription_expiry = next_billing_date
            days_left = (next_billing_date.date() - now.date()).days
            if days_left <= 7:
                await create_subscription_expiry_alert(
                    organization=org,
                    expiry_date=next_billing_date,
                    days_left=days_left,
                    action_url=f"OrganizationMembers?id={org.id}",
                )
            return org_id
        subscription_expiry = next_billing_date

    # Expired (trial + subscription). Mark suspended to keep everything in sync.
    if org.status != OrganizationStatus.SUSPENDED:
        org.status = OrganizationStatus.SUSPENDED
        org.updated_at = datetime.utcnow()
        await org.save()

    # If we can determine an expiry date, create an alert for the organization.
    expiry_for_alert = subscription_expiry or trial_expiry
    if expiry_for_alert:
        days_left = (expiry_for_alert.date() - now.date()).days
        await create_subscription_expiry_alert(
            organization=org,
            expiry_date=expiry_for_alert,
            days_left=max(days_left, 0),
            action_url=f"OrganizationMembers?id={org.id}",
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Organization subscription has expired",
    )
