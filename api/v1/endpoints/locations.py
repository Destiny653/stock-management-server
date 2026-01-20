"""Location endpoints"""
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from api import deps
from models.user import User
from models.location import Location
from schemas.location import LocationCreate, LocationUpdate, LocationResponse

router = APIRouter()

@router.get("/", response_model=List[LocationResponse])
async def read_locations(
    skip: int = 0,
    limit: int = 100,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve locations. Filtered by organization for non-superadmins.
    """
    query = {}
    if organization_id:
        query["organization_id"] = organization_id
        
    locations = await Location.find(query).skip(skip).limit(limit).to_list()
    return locations


@router.post("/", response_model=LocationResponse)
async def create_location(
    location_in: LocationCreate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new location within an organization.
    """
    data = location_in.model_dump()
    if organization_id:
        data["organization_id"] = organization_id
        
    location = Location(**data)
    await location.create()
    return location


@router.get("/{location_id}", response_model=LocationResponse)
async def read_location(
    location_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get location by ID within an organization.
    """
    query = {"_id": location_id}
    if organization_id:
        query["organization_id"] = organization_id
        
    location = await Location.find_one(query)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: str,
    location_in: LocationUpdate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a location within an organization.
    """
    query = {"_id": location_id}
    if organization_id:
        query["organization_id"] = organization_id
        
    location = await Location.find_one(query)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    update_data = location_in.model_dump(exclude_unset=True)
    # Prevent organization_id modification
    if "organization_id" in update_data:
        del update_data["organization_id"]
        
    update_data["updated_at"] = datetime.utcnow()
    await location.update({"$set": update_data})
    await location.save()
    return location


@router.delete("/{location_id}", response_model=LocationResponse)
async def delete_location(
    location_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a location within an organization.
    """
    query = {"_id": location_id}
    if organization_id:
        query["organization_id"] = organization_id
        
    location = await Location.find_one(query)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    await location.delete()
    return location
