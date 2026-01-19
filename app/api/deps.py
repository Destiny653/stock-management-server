"""API dependencies"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from app.core.config import settings
from app.models.user import User
from app.schemas.token import TokenPayload

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
    """Get current active superuser (admin)"""
    if current_user.role not in ["admin", "owner"]:
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_organization_id(
    organization_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
) -> str:
    """
    Get organization ID - either from query param or from user's organization.
    This can be used as a dependency for organization-scoped endpoints.
    """
    if organization_id:
        return organization_id
    if current_user.organization_id:
        return current_user.organization_id
    raise HTTPException(
        status_code=400,
        detail="Organization ID is required"
    )
