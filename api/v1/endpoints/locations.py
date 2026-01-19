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
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve all locations.
    """
    locations = await Location.find_all().skip(skip).limit(limit).to_list()
    return locations

@router.post("/", response_model=LocationResponse)
async def create_location(
    location_in: LocationCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new location within an organization.
    """
    location = Location(**location_in.model_dump())
    await location.create()
    return location

@router.get("/{location_id}", response_model=LocationResponse)
async def read_location(
    location_id: str,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get location by ID.
    """
    location = await Location.get(location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location

@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: str,
    location_in: LocationUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a location.
    """
    location = await Location.get(location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    update_data = location_in.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    await location.update({"$set": update_data})
    await location.save()
    return location

@router.delete("/{location_id}", response_model=LocationResponse)
async def delete_location(
    location_id: str,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a location.
    """
    location = await Location.get(location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    await location.delete()
    return location
