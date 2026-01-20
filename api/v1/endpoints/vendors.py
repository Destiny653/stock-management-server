"""Vendor endpoints"""
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from beanie import PydanticObjectId
from api import deps
from models.user import User
from models.vendor import Vendor
from schemas.vendor import VendorCreate, VendorUpdate, VendorResponse

router = APIRouter()


@router.get("/", response_model=List[VendorResponse])
async def read_vendors(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    id: Optional[str] = None,
    search: Optional[str] = None,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve vendors. Filtered by organization for non-superadmins.
    """
    query = {}
    if organization_id:
        query["organization_id"] = organization_id
    
    if id:
        query["_id"] = PydanticObjectId(id)
    if status:
        query["status"] = status
    if payment_status:
        query["payment_status"] = payment_status
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"store_name": {"$regex": search, "$options": "i"}},
        ]
    
    vendors = await Vendor.find(query).skip(skip).limit(limit).to_list()
    return vendors


@router.post("/", response_model=VendorResponse)
async def create_vendor(
    vendor_in: VendorCreate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new vendor within an organization.
    """
    # Enforce organization_id from dependency for non-superadmins
    data = vendor_in.model_dump()
    if organization_id:
        data["organization_id"] = organization_id
    
    # Check if vendor user already exists in organization
    if vendor_in.user_id:
        existing = await Vendor.find_one({
            "organization_id": data["organization_id"],
            "user_id": vendor_in.user_id
        })
        if existing:
            raise HTTPException(
                status_code=400,
                detail="A vendor with this user account already exists in this organization",
            )
    vendor = Vendor(**data)
    await vendor.create()
    return vendor


@router.get("/{vendor_id}", response_model=VendorResponse)
async def read_vendor(
    vendor_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get vendor by ID within an organization.
    """
    query = {"_id": PydanticObjectId(vendor_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    vendor = await Vendor.find_one(query)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.put("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: str,
    vendor_in: VendorUpdate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a vendor within an organization.
    """
    query = {"_id": PydanticObjectId(vendor_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    vendor = await Vendor.find_one(query)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    update_data = vendor_in.model_dump(exclude_unset=True)
    # Prevent organization_id modification via update
    if "organization_id" in update_data:
        del update_data["organization_id"]
        
    update_data["updated_at"] = datetime.utcnow()
    await vendor.update({"$set": update_data})
    await vendor.save()
    return vendor


@router.delete("/{vendor_id}", response_model=VendorResponse)
async def delete_vendor(
    vendor_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a vendor within an organization.
    """
    query = {"_id": PydanticObjectId(vendor_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    vendor = await Vendor.find_one(query)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    await vendor.delete()
    return vendor


@router.get("/stats/summary", response_model=dict)
async def get_vendor_stats(
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get vendor statistics for an organization.
    """
    if not organization_id:
        # Superadmin with no org filter
        query = {}
    else:
        query = {"organization_id": organization_id}
        
    total = await Vendor.find(query).count()
    active = await Vendor.find({**query, "status": "active"}).count()
    pending = await Vendor.find({**query, "status": "pending"}).count()
    overdue_payments = await Vendor.find({
        **query,
        "payment_status": "overdue"
    }).count()
    
    return {
        "total_vendors": total,
        "active_vendors": active,
        "pending_vendors": pending,
        "overdue_payments": overdue_payments
    }
