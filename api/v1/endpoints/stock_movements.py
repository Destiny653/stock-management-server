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
from services.notification import send_low_stock_alert
from services.notification_helpers import get_org_notification_recipients
from models.alert import Alert, AlertType, AlertPriority

router = APIRouter()


@router.get("/", response_model=List[StockMovementResponse])
async def read_stock_movements(
    skip: int = 0,
    limit: int = 100,
    sort: Optional[str] = None,
    product_id: Optional[str] = None,
    movement_type: Optional[str] = None,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve stock movements. Filtered by organization for non-superadmins.
    """
    query = {}
    if organization_id:
        query["organization_id"] = organization_id
    
    if product_id:
        query["product_id"] = product_id
    if movement_type:
        query["type"] = movement_type
    
    q = StockMovement.find(query)
    if sort:
        q = q.sort(sort)
    else:
        q = q.sort("-created_at")
    
    movements = await q.skip(skip).limit(limit).to_list()
    return movements


@router.post("/", response_model=StockMovementResponse)
async def create_stock_movement(
    movement_in: StockMovementCreate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new stock movement and update product quantities.
    """
    data = movement_in.model_dump()
    if organization_id:
        data["organization_id"] = organization_id

    # Get the product
    product = await Product.find_one({
        "_id": PydanticObjectId(movement_in.product_id),
        "organization_id": data["organization_id"]
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
    org_id = data["organization_id"]
    total_stock = sum(v.stock for v in product.variants)
    product_id_str = str(product.id)

    if total_stock == 0:
        product.status = "out_of_stock"
        # Create in-app critical alert (deduped)
        existing = await Alert.find_one({
            "organization_id": org_id,
            "product_id": product_id_str,
            "type": AlertType.OUT_OF_STOCK,
            "is_dismissed": False,
        })
        if not existing:
            await Alert(
                organization_id=org_id,
                type=AlertType.OUT_OF_STOCK,
                priority=AlertPriority.CRITICAL,
                title=f"Out of Stock: {product.name}",
                message=f"{product.name} has run out of stock. Reorder quantity: {product.reorder_quantity or 'N/A'}.",
                product_id=product_id_str,
                action_url=f"/Inventory",
            ).create()
        # Email admins
        recipients = await get_org_notification_recipients(org_id)
        for recipient in recipients:
            await send_low_stock_alert(
                user=recipient,
                product_name=product.name,
                current_stock=total_stock,
                reorder_point=product.reorder_point or 0
            )
    elif total_stock <= (product.reorder_point or 0):
        product.status = "low_stock"
        # Create in-app high alert (deduped)
        existing = await Alert.find_one({
            "organization_id": org_id,
            "product_id": product_id_str,
            "type": AlertType.LOW_STOCK,
            "is_dismissed": False,
        })
        if not existing:
            await Alert(
                organization_id=org_id,
                type=AlertType.LOW_STOCK,
                priority=AlertPriority.HIGH,
                title=f"Low Stock: {product.name}",
                message=f"{product.name} has reached its reorder point ({product.reorder_point} units). Current stock: {total_stock}.",
                product_id=product_id_str,
                action_url=f"/Inventory",
            ).create()
        # Email admins
        recipients = await get_org_notification_recipients(org_id)
        for recipient in recipients:
            await send_low_stock_alert(
                user=recipient,
                product_name=product.name,
                current_stock=total_stock,
                reorder_point=product.reorder_point or 0
            )
    else:
        product.status = "active"

    await product.save()
    
    # Create movement record
    data["product_name"] = product.name
    data["sku"] = variant.sku
    data["performed_by"] = str(current_user.id)
    
    movement = StockMovement(**data)
    await movement.create()
    return movement


@router.get("/{movement_id}", response_model=StockMovementResponse)
async def read_stock_movement(
    movement_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get stock movement by ID within an organization.
    """
    query = {"_id": PydanticObjectId(movement_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    movement = await StockMovement.find_one(query)
    if not movement:
        raise HTTPException(status_code=404, detail="Stock movement not found")
    return movement


@router.get("/product/{product_id}/history", response_model=List[StockMovementResponse])
async def get_product_movement_history(
    product_id: str,
    skip: int = 0,
    limit: int = 50,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get stock movement history for a specific product.
    """
    query = {"product_id": product_id}
    if organization_id:
        query["organization_id"] = organization_id
        
    movements = await StockMovement.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
    return movements


@router.post("/transfer")
async def transfer_stock_between_stores(
    transfer_data: dict,
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Transfer stock between stores or warehouses.
    Payload: product_id, from_warehouse_id, to_warehouse_id, quantity, notes, reference
    """
    org_id = str(current_user.organization_id)
    product_id = transfer_data.get("product_id")
    from_wh = transfer_data.get("from_warehouse_id")
    to_wh = transfer_data.get("to_warehouse_id")
    qty = int(transfer_data.get("quantity") or 0)
    notes = transfer_data.get("notes")
    ref = transfer_data.get("reference") or f"TRF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    if qty <= 0:
        raise HTTPException(status_code=400, detail="Transfer quantity must be greater than 0")
    if from_wh == to_wh:
        raise HTTPException(status_code=400, detail="Source and destination warehouses cannot be the same")

    product = await Product.find_one(
        Product.id == PydanticObjectId(product_id),
        Product.organization_id == org_id
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Update or initialize warehouse stock records on product
    source_record = next((ws for ws in product.warehouse_stocks if ws.warehouse_id == from_wh), None)
    if not source_record or source_record.stock < qty:
        # Fallback check against product total stock if warehouse records not initialized
        if product.total_stock < qty:
            raise HTTPException(status_code=400, detail=f"Insufficient stock ({product.total_stock} available)")

    if source_record:
        source_record.stock -= qty

    dest_record = next((ws for ws in product.warehouse_stocks if ws.warehouse_id == to_wh), None)
    if dest_record:
        dest_record.stock += qty
    else:
        product.warehouse_stocks.append({
            "warehouse_id": to_wh,
            "warehouse_name": transfer_data.get("to_warehouse_name") or "Store",
            "stock": qty,
            "reserved_stock": 0,
            "damaged_stock": 0
        })

    product.updated_at = datetime.utcnow()
    await product.save()

    # Record movement
    movement = StockMovement(
        organization_id=org_id,
        product_id=str(product.id),
        product_name=product.name,
        sku=product.sku,
        type="transferred",
        quantity=-qty,
        from_location=from_wh,
        to_location=to_wh,
        reference=ref,
        notes=notes,
        actor_id=str(current_user.id),
        actor_name=current_user.username,
        performed_by=str(current_user.id),
        unit_cost=product.cost_price,
        total_cost=qty * product.cost_price,
    )
    await movement.insert()

    return {
        "status": "success",
        "message": f"Successfully transferred {qty} units of {product.name}",
        "reference": ref,
        "product_id": str(product.id),
        "total_stock": product.total_stock
    }

