"""Category endpoints"""
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from api import deps
from models.user import User
from models.category import Category
from schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter()

@router.get("/", response_model=List[CategoryResponse])
async def read_categories(
    skip: int = 0,
    limit: int = 100,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve categories. Filtered by organization for non-superadmins.
    """
    query = {}
    if organization_id:
        query["organization_id"] = organization_id
        
    categories = await Category.find(query).skip(skip).limit(limit).to_list()
    return categories


@router.post("/", response_model=CategoryResponse)
async def create_category(
    category_in: CategoryCreate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new category.
    """
    data = category_in.model_dump()
    if organization_id:
        data["organization_id"] = organization_id
    elif not data.get("organization_id"):
        raise HTTPException(status_code=400, detail="Organization ID is required")
        
    category = Category(**data)
    await category.create()
    return category


@router.get("/{category_id}", response_model=CategoryResponse)
async def read_category(
    category_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get category by ID within an organization.
    """
    query = {"_id": category_id}
    if organization_id:
        query["organization_id"] = organization_id
        
    category = await Category.find_one(query)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    category_in: CategoryUpdate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a category within an organization.
    """
    query = {"_id": category_id}
    if organization_id:
        query["organization_id"] = organization_id
        
    category = await Category.find_one(query)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = category_in.model_dump(exclude_unset=True)
    # Prevent organization_id modification
    if "organization_id" in update_data:
        del update_data["organization_id"]
        
    update_data["updated_at"] = datetime.utcnow()
    await category.update({"$set": update_data})
    await category.save()
    return category


@router.delete("/{category_id}", response_model=CategoryResponse)
async def delete_category(
    category_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a category within an organization.
    """
    query = {"_id": category_id}
    if organization_id:
        query["organization_id"] = organization_id
        
    category = await Category.find_one(query)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    await category.delete()
    return category
