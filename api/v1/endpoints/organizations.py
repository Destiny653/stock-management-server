"""Organization endpoints"""
from typing import List, Any, Optional
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
    return organizations


@router.post("/", response_model=OrganizationResponse)
async def create_organization(
    organization_in: OrganizationCreate,
    current_user: Optional[User] = None, # Depends(deps.get_current_active_superuser),
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
    organization = Organization(**organization_in.model_dump())
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
    # If not superadmin, they must belong to this organization
    if current_user.role not in ["admin", "owner"] and current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this organization's data"
        )
        
    organization = await Organization.get(organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
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
