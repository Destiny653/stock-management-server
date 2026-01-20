"""Supplier endpoints"""
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from beanie import PydanticObjectId
from api import deps
from models.user import User
from models.supplier import Supplier
from schemas.supplier import SupplierCreate, SupplierUpdate, SupplierResponse

router = APIRouter()


@router.get("/", response_model=List[SupplierResponse])
async def read_suppliers(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve suppliers. Filtered by organization for non-superadmins.
    """
    query = {}
    if organization_id:
        query["organization_id"] = organization_id
    
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
        ]
    
    suppliers = await Supplier.find(query).skip(skip).limit(limit).to_list()
    return suppliers


@router.post("/", response_model=SupplierResponse)
async def create_supplier(
    supplier_in: SupplierCreate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new supplier within an organization.
    """
    data = supplier_in.model_dump()
    if organization_id:
        data["organization_id"] = organization_id
        
    # Check if supplier user already exists in organization
    if supplier_in.user_id:
        existing = await Supplier.find_one({
            "organization_id": data["organization_id"],
            "user_id": supplier_in.user_id
        })
        if existing:
            raise HTTPException(
                status_code=400,
                detail="A supplier with this user account already exists in this organization",
            )
    else:
        # Check if supplier with same name already exists in organization
        existing_name = await Supplier.find_one({
            "organization_id": data["organization_id"],
            "name": supplier_in.name
        })
        if existing_name:
            raise HTTPException(
                status_code=400,
                detail="A supplier with this name already exists in this organization",
            )
    supplier = Supplier(**data)
    await supplier.create()
    return supplier


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def read_supplier(
    supplier_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get supplier by ID within an organization.
    """
    query = {"_id": PydanticObjectId(supplier_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    supplier = await Supplier.find_one(query)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: str,
    supplier_in: SupplierUpdate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a supplier within an organization.
    """
    query = {"_id": PydanticObjectId(supplier_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    supplier = await Supplier.find_one(query)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    update_data = supplier_in.model_dump(exclude_unset=True)
    # Prevent organization_id modification
    if "organization_id" in update_data:
        del update_data["organization_id"]
        
    update_data["updated_at"] = datetime.utcnow()
    await supplier.update({"$set": update_data})
    await supplier.save()
    return supplier


@router.delete("/{supplier_id}", response_model=SupplierResponse)
async def delete_supplier(
    supplier_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a supplier within an organization.
    """
    query = {"_id": PydanticObjectId(supplier_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    supplier = await Supplier.find_one(query)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    await supplier.delete()
    return supplier
