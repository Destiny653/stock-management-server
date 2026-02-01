"""API dependencies"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from core.config import settings
from models.user import User
from schemas.token import TokenPayload

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
    # Platform staff can manage the entire platform
    if current_user.user_type != "platform-staff":
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_organization_id(
    organization_id: Optional[str] = None,
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
        
    return current_user.organization_id
