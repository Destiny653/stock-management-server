"""VendorPayment endpoints"""
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from beanie import PydanticObjectId
from app.api import deps
from app.models.user import User
from app.models.vendor_payment import VendorPayment
from app.models.vendor import Vendor
from app.schemas.vendor_payment import VendorPaymentCreate, VendorPaymentUpdate, VendorPaymentResponse

router = APIRouter()


@router.get("/", response_model=List[VendorPaymentResponse])
async def read_vendor_payments(
    organization_id: str = Query(..., description="Organization ID to filter by"),
    skip: int = 0,
    limit: int = 100,
    vendor_id: Optional[str] = None,
    status: Optional[str] = None,
    payment_type: Optional[str] = None,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve vendor payments for a specific organization.
    """
    query = {"organization_id": organization_id}
    
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
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new vendor payment within an organization.
    """
    # Verify vendor exists
    vendor = await Vendor.find_one({
        "_id": PydanticObjectId(payment_in.vendor_id),
        "organization_id": payment_in.organization_id
    })
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    payment_data = payment_in.model_dump()
    payment_data["vendor_name"] = vendor.name
    
    payment = VendorPayment(**payment_data)
    await payment.create()
    return payment


@router.get("/{payment_id}", response_model=VendorPaymentResponse)
async def read_vendor_payment(
    payment_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get vendor payment by ID within an organization.
    """
    payment = await VendorPayment.find_one({
        "_id": PydanticObjectId(payment_id),
        "organization_id": organization_id
    })
    if not payment:
        raise HTTPException(status_code=404, detail="Vendor payment not found")
    return payment


@router.put("/{payment_id}", response_model=VendorPaymentResponse)
async def update_vendor_payment(
    payment_id: str,
    payment_in: VendorPaymentUpdate,
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a vendor payment within an organization.
    """
    payment = await VendorPayment.find_one({
        "_id": PydanticObjectId(payment_id),
        "organization_id": organization_id
    })
    if not payment:
        raise HTTPException(status_code=404, detail="Vendor payment not found")
    
    update_data = payment_in.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    await payment.update({"$set": update_data})
    await payment.save()
    return payment


@router.delete("/{payment_id}", response_model=VendorPaymentResponse)
async def delete_vendor_payment(
    payment_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a vendor payment within an organization.
    """
    payment = await VendorPayment.find_one({
        "_id": PydanticObjectId(payment_id),
        "organization_id": organization_id
    })
    if not payment:
        raise HTTPException(status_code=404, detail="Vendor payment not found")
    await payment.delete()
    return payment


@router.post("/{payment_id}/confirm", response_model=VendorPaymentResponse)
async def confirm_vendor_payment(
    payment_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Confirm a vendor payment and update vendor payment status.
    """
    payment = await VendorPayment.find_one({
        "_id": PydanticObjectId(payment_id),
        "organization_id": organization_id
    })
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
    vendor = await Vendor.find_one({"_id": PydanticObjectId(payment.vendor_id)})
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
    organization_id: str = Query(..., description="Organization ID"),
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get payment history for a specific vendor.
    """
    payments = await VendorPayment.find({
        "organization_id": organization_id,
        "vendor_id": vendor_id
    }).sort("-created_at").skip(skip).limit(limit).to_list()
    return payments
