"""Users endpoints"""
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from beanie import PydanticObjectId
from app.api import deps
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.core import security

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def read_users(
    organization_id: str = Query(..., description="Organization ID to filter by"),
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve users for a specific organization.
    """
    query = {"organization_id": organization_id}
    
    if role:
        query["role"] = role
    if status:
        query["status"] = status
    
    users = await User.find(query).skip(skip).limit(limit).to_list()
    return users


@router.post("/", response_model=UserResponse)
async def create_user(
    user_in: UserCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new user within an organization.
    """
    # Check if email exists
    existing_email = await User.find_one({"email": user_in.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if username exists
    existing_username = await User.find_one({"username": user_in.username})
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    user_data = user_in.model_dump(exclude={"password"})
    user_data["hashed_password"] = security.get_password_hash(user_in.password)
    user_data["invited_by"] = str(current_user.id)
    user_data["invited_at"] = datetime.utcnow()
    
    user = User(**user_data)
    await user.create()
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get user by ID within an organization.
    """
    user = await User.find_one({
        "_id": PydanticObjectId(user_id),
        "organization_id": organization_id
    })
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a user within an organization.
    """
    user = await User.find_one({
        "_id": PydanticObjectId(user_id),
        "organization_id": organization_id
    })
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_in.model_dump(exclude_unset=True)
    
    # Handle password update separately
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = security.get_password_hash(update_data.pop("password"))
    elif "password" in update_data:
        del update_data["password"]
    
    update_data["updated_at"] = datetime.utcnow()
    await user.update({"$set": update_data})
    await user.save()
    return user


@router.delete("/{user_id}", response_model=UserResponse)
async def delete_user(
    user_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a user within an organization.
    """
    user = await User.find_one({
        "_id": PydanticObjectId(user_id),
        "organization_id": organization_id
    })
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-deletion
    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    await user.delete()
    return user
