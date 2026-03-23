"""Organization endpoints"""
from typing import List, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from beanie import PydanticObjectId
from api import deps
from models.user import User
from models.organization import Organization
from schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse

router = APIRouter()


@router.get("/", response_model=List[OrganizationResponse])
async def read_organizations(
    skip: int = 0,
    limit: int = 100,
    id: Optional[str] = None,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Retrieve all organizations (admin only).
    """
    query = {}
    if id:
        query["_id"] = PydanticObjectId(id)
    organizations = await Organization.find(query).skip(skip).limit(limit).to_list()
    # Keep frontend-aligned fields in sync with older DB field names.
    for org in organizations:
        if org.subscription_plan is None and org.subscription_plan_id:
            org.subscription_plan = org.subscription_plan_id
        if org.billing_cycle == "monthly" and org.subscription_interval and org.subscription_interval != "monthly":
            org.billing_cycle = org.subscription_interval
    return organizations


@router.post("/", response_model=OrganizationResponse)
async def create_organization(
    organization_in: OrganizationCreate,
) -> Any:
    """
    Create new organization (Public for registration).
    """
    org = await Organization.find_one(Organization.code == organization_in.code)
    if org:
        raise HTTPException(
            status_code=400,
            detail="An organization with this code already exists",
        )
    data = organization_in.model_dump()

    # New org registration: start in "pending" until platform-staff approves,
    # and grant a 30-day free trial by default.
    data.setdefault("status", "pending")
    if not data.get("trial_ends_at"):
        data["trial_ends_at"] = datetime.utcnow() + timedelta(days=30)
    # Normalize newer -> backward-compatible fields.
    if data.get("subscription_plan") and not data.get("subscription_plan_id"):
        data["subscription_plan_id"] = data["subscription_plan"]
    if data.get("billing_cycle") and not data.get("subscription_interval"):
        data["subscription_interval"] = data["billing_cycle"]
    organization = Organization(**data)
    await organization.create()
    return organization


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def read_organization(
    organization_id: str,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get organization by ID.
    """
    # Platform-staff can access any organization, business-staff must belong to this org
    if current_user.user_type != "platform-staff" and current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this organization's data"
        )
        
    organization = await Organization.get(organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    if organization.subscription_plan is None and organization.subscription_plan_id:
        organization.subscription_plan = organization.subscription_plan_id
    if organization.billing_cycle == "monthly" and organization.subscription_interval and organization.subscription_interval != "monthly":
        organization.billing_cycle = organization.subscription_interval
    return organization


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: str,
    organization_in: OrganizationUpdate,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Update an organization (admin only).
    """
    organization = await Organization.get(organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    update_data = organization_in.model_dump(exclude_unset=True)

    # Map frontend billing fields -> backward-compatible DB fields.
    if update_data.get("subscription_plan") and not update_data.get("subscription_plan_id"):
        update_data["subscription_plan_id"] = update_data["subscription_plan"]
    if update_data.get("billing_cycle") and not update_data.get("subscription_interval"):
        update_data["subscription_interval"] = update_data["billing_cycle"]

    await organization.update({"$set": update_data})
    await organization.save()
    return organization


@router.delete("/{organization_id}", response_model=OrganizationResponse)
async def delete_organization(
    organization_id: str,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Delete an organization (admin only).
    """
    organization = await Organization.get(organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    await organization.delete()
    return organization
