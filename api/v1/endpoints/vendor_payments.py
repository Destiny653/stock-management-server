"""VendorPayment endpoints"""
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from beanie import PydanticObjectId
from api import deps
from models.user import User
from models.vendor_payment import VendorPayment
from models.vendor import Vendor
from schemas.vendor_payment import VendorPaymentCreate, VendorPaymentUpdate, VendorPaymentResponse

router = APIRouter()


@router.get("/", response_model=List[VendorPaymentResponse])
async def read_vendor_payments(
    skip: int = 0,
    limit: int = 100,
    vendor_id: Optional[str] = None,
    status: Optional[str] = None,
    payment_type: Optional[str] = None,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve vendor payments. Filtered by organization for non-superadmins.
    """
    query = {}
    if organization_id:
        query["organization_id"] = organization_id
    
    if vendor_id:
        query["vendor_id"] = vendor_id
    if status:
        query["status"] = status
    if payment_type:
        query["payment_type"] = payment_type
    
    payments = await VendorPayment.find(query).skip(skip).limit(limit).to_list()
    return payments


@router.post("/", response_model=VendorPaymentResponse)
async def create_vendor_payment(
    payment_in: VendorPaymentCreate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new vendor payment within an organization.
    """
    data = payment_in.model_dump()
    if organization_id:
        data["organization_id"] = organization_id

    # Verify vendor exists
    vendor = await Vendor.find_one({
        "_id": PydanticObjectId(payment_in.vendor_id),
        "organization_id": data["organization_id"]
    })
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    data["vendor_name"] = vendor.name
    
    payment = VendorPayment(**data)
    await payment.create()
    return payment


@router.get("/{payment_id}", response_model=VendorPaymentResponse)
async def read_vendor_payment(
    payment_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get vendor payment by ID within an organization.
    """
    query = {"_id": PydanticObjectId(payment_id)}
    if organization_id:
        query["organization_id"] = organization_id

    payment = await VendorPayment.find_one(query)
    if not payment:
        raise HTTPException(status_code=404, detail="Vendor payment not found")
    return payment


@router.put("/{payment_id}", response_model=VendorPaymentResponse)
async def update_vendor_payment(
    payment_id: str,
    payment_in: VendorPaymentUpdate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a vendor payment within an organization.
    """
    query = {"_id": PydanticObjectId(payment_id)}
    if organization_id:
        query["organization_id"] = organization_id

    payment = await VendorPayment.find_one(query)
    if not payment:
        raise HTTPException(status_code=404, detail="Vendor payment not found")
    
    update_data = payment_in.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    # Prevent organization_id modification
    if "organization_id" in update_data:
        del update_data["organization_id"]

    await payment.update({"$set": update_data})
    await payment.save()
    return payment


@router.delete("/{payment_id}", response_model=VendorPaymentResponse)
async def delete_vendor_payment(
    payment_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a vendor payment within an organization.
    """
    query = {"_id": PydanticObjectId(payment_id)}
    if organization_id:
        query["organization_id"] = organization_id

    payment = await VendorPayment.find_one(query)
    if not payment:
        raise HTTPException(status_code=404, detail="Vendor payment not found")
    await payment.delete()
    return payment


@router.post("/{payment_id}/confirm", response_model=VendorPaymentResponse)
async def confirm_vendor_payment(
    payment_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Confirm a vendor payment and update vendor payment status.
    """
    query = {"_id": PydanticObjectId(payment_id)}
    if organization_id:
        query["organization_id"] = organization_id

    payment = await VendorPayment.find_one(query)
    if not payment:
        raise HTTPException(status_code=404, detail="Vendor payment not found")
    
    if payment.status == "confirmed":
        raise HTTPException(status_code=400, detail="Payment already confirmed")
    
    # Update payment
    now = datetime.utcnow()
    await payment.update({
        "$set": {
            "status": "confirmed",
            "confirmed_by": str(current_user.id),
            "confirmed_date": now,
            "updated_at": now
        }
    })
    
    # Update vendor payment status
    vendor = await Vendor.find_one({
        "_id": PydanticObjectId(payment.vendor_id),
        "organization_id": payment.organization_id
    })
    if vendor:
        await vendor.update({
            "$set": {
                "payment_status": "paid",
                "last_payment_date": now.date(),
                "updated_at": now
            }
        })
    
    await payment.save()
    return payment


@router.get("/vendor/{vendor_id}/history", response_model=List[VendorPaymentResponse])
async def get_vendor_payment_history(
    vendor_id: str,
    skip: int = 0,
    limit: int = 50,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get payment history for a specific vendor.
    """
    query = {"vendor_id": vendor_id}
    if organization_id:
        query["organization_id"] = organization_id

    payments = await VendorPayment.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
    return payments
