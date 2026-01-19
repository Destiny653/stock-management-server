"""Authentication endpoints"""
from datetime import timedelta
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from pydantic import ValidationError
from core import security
from core.config import settings
from models.user import User
from schemas.token import Token, TokenPayload
from schemas.user import UserCreate, UserResponse, UserUpdate
from api import deps
from core.privileges import Privilege, ROLE_PERMISSIONS

router = APIRouter()


@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = await User.find_one(User.username == form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        str(user.id), expires_delta=access_token_expires
    )
    # 2 days in seconds = 172800
    refresh_token = security.create_refresh_token(str(user.id))
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=172800,
        samesite="lax",
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(response: Response) -> Any:
    """
    Logout user by clearing cookies
    """
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}


@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
) -> Any:
    """
    Refresh access token using refresh token from cookie
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
        
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token type",
        )
        
    user = await User.get(token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = security.create_access_token(
        str(user.id), expires_delta=access_token_expires
    )
    new_refresh_token = security.create_refresh_token(str(user.id))
    
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        max_age=172800,
        samesite="lax",
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_in: UserCreate,
) -> Any:
    """
    Create new user without the need to be logged in
    """
    user = await User.find_one(User.email == user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    
    user_by_username = await User.find_one(User.username == user_in.username)
    if user_by_username:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system",
        )
        
    hashed_password = security.get_password_hash(user_in.password)
    user_data = user_in.model_dump(exclude={"password"})
    user_data["hashed_password"] = hashed_password
    
    # Assign default permissions if none provided
    if not user_data.get("permissions"):
        user_data["permissions"] = ROLE_PERMISSIONS.get(user_in.role.value, [])
    
    # Set default status to active if registering directly
    user_data["status"] = "active"
    
    user = User(**user_data)
    await user.create()
    return user


@router.get("/privileges", response_model=List[str])
async def get_available_privileges() -> Any:
    """
    Get all available privileges in the system.
    """
    return [p.value for p in Privilege]


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_users_me(
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update current user profile including preferences
    """
    from datetime import datetime
    from services.notification import send_push_notification_test
    
    update_data = user_in.model_dump(exclude_unset=True, exclude={"password"})
    
    # Handle password update separately
    if user_in.password:
        update_data["hashed_password"] = security.get_password_hash(user_in.password)
    
    # Check if push notifications were enabled and send a test email
    if user_in.preferences and user_in.preferences.notifications:
        old_push = current_user.preferences.notifications.push if current_user.preferences and current_user.preferences.notifications else False
        new_push = user_in.preferences.notifications.push
        
        if new_push and not old_push:
            # Send a welcome email when push notifications are enabled
            try:
                await send_push_notification_test(current_user)
            except Exception as e:
                # Log the error but don't fail the update
                print(f"Failed to send notification email: {e}")
    
    update_data["updated_at"] = datetime.utcnow()
    
    if update_data:
        await current_user.update({"$set": update_data})
        await current_user.save()
    
    return current_user
