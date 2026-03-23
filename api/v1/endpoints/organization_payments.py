"""OrganizationPayment endpoints"""

from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from beanie import PydanticObjectId

from api import deps
from models.user import User
from models.organization import Organization
from models.organization_payment import OrganizationPayment
from schemas.organization_payment import (
    OrganizationPaymentCreate,
    OrganizationPaymentUpdate,
    OrganizationPaymentResponse,
)

router = APIRouter()


@router.get("/", response_model=List[OrganizationPaymentResponse])
async def read_organization_payments(
    skip: int = 0,
    limit: int = 100,
    subscription_plan_id: Optional[str] = None,
    status: Optional[str] = None,
    payment_method: Optional[str] = None,
    payment_type: Optional[str] = None,
    billing_period: Optional[str] = None,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve organization payments. Filtered by organization for non-superadmins.
    """
    query = {}
    if organization_id:
        query["organization_id"] = organization_id
    if subscription_plan_id:
        query["subscription_plan_id"] = subscription_plan_id
    if status:
        query["status"] = status
    if payment_method:
        query["payment_method"] = payment_method
    if payment_type:
        query["payment_type"] = payment_type
    if billing_period:
        query["billing_period"] = billing_period

    payments = await OrganizationPayment.find(query).skip(skip).limit(limit).to_list()
    return payments


@router.post("/", response_model=OrganizationPaymentResponse)
async def create_organization_payment(
    payment_in: OrganizationPaymentCreate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new organization payment within an organization.
    """
    data = payment_in.model_dump()
    if organization_id:
        data["organization_id"] = organization_id

    org_id = data.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_id is required")

    org = await Organization.find_one({"_id": PydanticObjectId(org_id)})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    payment = OrganizationPayment(**data)
    await payment.create()
    return payment


@router.get("/{payment_id}", response_model=OrganizationPaymentResponse)
async def read_organization_payment(
    payment_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get organization payment by ID within an organization.
    """
    query = {"_id": PydanticObjectId(payment_id)}
    if organization_id:
        query["organization_id"] = organization_id

    payment = await OrganizationPayment.find_one(query)
    if not payment:
        raise HTTPException(status_code=404, detail="Organization payment not found")
    return payment


@router.put("/{payment_id}", response_model=OrganizationPaymentResponse)
async def update_organization_payment(
    payment_id: str,
    payment_in: OrganizationPaymentUpdate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a organization payment within an organization.
    """
    query = {"_id": PydanticObjectId(payment_id)}
    if organization_id:
        query["organization_id"] = organization_id

    payment = await OrganizationPayment.find_one(query)
    if not payment:
        raise HTTPException(status_code=404, detail="Organization payment not found")

    update_data = payment_in.model_dump(exclude_unset=True)

    # Prevent organization_id modification
    if "organization_id" in update_data:
        del update_data["organization_id"]

    update_data["updated_at"] = datetime.utcnow()
    await payment.update({"$set": update_data})
    await payment.save()
    return payment


@router.delete("/{payment_id}", response_model=OrganizationPaymentResponse)
async def delete_organization_payment(
    payment_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete an organization payment within an organization.
    """
    query = {"_id": PydanticObjectId(payment_id)}
    if organization_id:
        query["organization_id"] = organization_id

    payment = await OrganizationPayment.find_one(query)
    if not payment:
        raise HTTPException(status_code=404, detail="Organization payment not found")

    await payment.delete()
    return payment

