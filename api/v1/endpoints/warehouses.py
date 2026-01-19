"""Warehouse endpoints"""
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from beanie import PydanticObjectId
from api import deps
from models.user import User
from models.warehouse import Warehouse
from schemas.warehouse import WarehouseCreate, WarehouseUpdate, WarehouseResponse

router = APIRouter()


@router.get("/", response_model=List[WarehouseResponse])
async def read_warehouses(
    organization_id: str = Query(..., description="Organization ID to filter by"),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve warehouses for a specific organization.
    """
    query = {"organization_id": organization_id}
    
    if status:
        query["status"] = status
    
    warehouses = await Warehouse.find(query).skip(skip).limit(limit).to_list()
    return warehouses


@router.post("/", response_model=WarehouseResponse)
async def create_warehouse(
    warehouse_in: WarehouseCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new warehouse within an organization.
    """
    existing = await Warehouse.find_one({
        "organization_id": warehouse_in.organization_id,
        "code": warehouse_in.code
    })
    if existing:
        raise HTTPException(
            status_code=400,
            detail="A warehouse with this code already exists in this organization",
        )
    warehouse = Warehouse(**warehouse_in.model_dump())
    await warehouse.create()
    return warehouse


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
async def read_warehouse(
    warehouse_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get warehouse by ID within an organization.
    """
    warehouse = await Warehouse.find_one({
        "_id": PydanticObjectId(warehouse_id),
        "organization_id": organization_id
    })
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return warehouse


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: str,
    warehouse_in: WarehouseUpdate,
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a warehouse within an organization.
    """
    warehouse = await Warehouse.find_one({
        "_id": PydanticObjectId(warehouse_id),
        "organization_id": organization_id
    })
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    update_data = warehouse_in.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    await warehouse.update({"$set": update_data})
    await warehouse.save()
    return warehouse


@router.delete("/{warehouse_id}", response_model=WarehouseResponse)
async def delete_warehouse(
    warehouse_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a warehouse within an organization.
    """
    warehouse = await Warehouse.find_one({
        "_id": PydanticObjectId(warehouse_id),
        "organization_id": organization_id
    })
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    await warehouse.delete()
    return warehouse
