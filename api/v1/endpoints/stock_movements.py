"""StockMovement endpoints"""
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from beanie import PydanticObjectId
from api import deps
from models.user import User
from models.stock_movement import StockMovement
from models.product import Product
from schemas.stock_movement import StockMovementCreate, StockMovementResponse
from datetime import datetime

router = APIRouter()


@router.get("/", response_model=List[StockMovementResponse])
async def read_stock_movements(
    organization_id: str = Query(..., description="Organization ID to filter by"),
    skip: int = 0,
    limit: int = 100,
    sort: Optional[str] = None,
    product_id: Optional[str] = None,
    movement_type: Optional[str] = None,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve stock movements for a specific organization.
    """
    query = {"organization_id": organization_id}
    
    if product_id:
        query["product_id"] = product_id
    if movement_type:
        query["type"] = movement_type
    
    q = StockMovement.find(query)
    if sort:
        q = q.sort(sort)
    
    movements = await q.skip(skip).limit(limit).to_list()
    return movements


@router.post("/", response_model=StockMovementResponse)
async def create_stock_movement(
    movement_in: StockMovementCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new stock movement and update product quantities.
    """
    # Get the product
    product = await Product.find_one({
        "_id": PydanticObjectId(movement_in.product_id),
        "organization_id": movement_in.organization_id
    })
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Find the variant if SKU is provided
    variant = None
    variant_idx = -1
    if movement_in.sku:
        for i, v in enumerate(product.variants):
            if v.sku == movement_in.sku:
                variant = v
                variant_idx = i
                break
    
    if not variant and len(product.variants) == 1:
        variant = product.variants[0]
        variant_idx = 0
    elif not variant and len(product.variants) > 1:
        raise HTTPException(status_code=400, detail="SKU is required for products with multiple variants")
    elif not variant and len(product.variants) == 0:
         raise HTTPException(status_code=400, detail="Product has no variants")

    # Calculate new stock based on movement type
    change = movement_in.quantity
    if movement_in.type in ["received", "returned"]:
        change = abs(movement_in.quantity)
    elif movement_in.type in ["dispatched"]:
        change = -abs(movement_in.quantity)
    
    new_stock = variant.stock + change
    if new_stock < 0:
        raise HTTPException(status_code=400, detail="Insufficient stock for this variant")
    
    # Update variant stock
    product.variants[variant_idx].stock = new_stock
    product.updated_at = datetime.utcnow()
    
    # Update status based on total quantity
    total_stock = sum(v.stock for v in product.variants)
    if total_stock == 0:
        product.status = "out_of_stock"
    elif total_stock <= (product.reorder_point or 0):
        product.status = "low_stock"
    else:
        product.status = "active"

    await product.save()
    
    # Create movement record
    movement_data = movement_in.model_dump()
    movement_data["product_name"] = product.name
    movement_data["sku"] = variant.sku
    movement_data["performed_by"] = str(current_user.id)
    
    movement = StockMovement(**movement_data)
    await movement.create()
    return movement


@router.get("/{movement_id}", response_model=StockMovementResponse)
async def read_stock_movement(
    movement_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get stock movement by ID within an organization.
    """
    movement = await StockMovement.find_one({
        "_id": PydanticObjectId(movement_id),
        "organization_id": organization_id
    })
    if not movement:
        raise HTTPException(status_code=404, detail="Stock movement not found")
    return movement


@router.get("/product/{product_id}/history", response_model=List[StockMovementResponse])
async def get_product_movement_history(
    product_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get stock movement history for a specific product.
    """
    movements = await StockMovement.find({
        "organization_id": organization_id,
        "product_id": product_id
    }).sort("-created_at").skip(skip).limit(limit).to_list()
    return movements
