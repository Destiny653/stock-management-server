"""PurchaseOrder endpoints"""
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from beanie import PydanticObjectId
from api import deps
from models.user import User
from models.purchase_order import PurchaseOrder, POItem
from models.product import Product
from models.stock_movement import StockMovement, MovementType
from schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse

router = APIRouter()


@router.get("/", response_model=List[PurchaseOrderResponse])
async def read_purchase_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    supplier_id: Optional[str] = None,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve purchase orders. Filtered by organization for non-superadmins.
    """
    query = {}
    if organization_id:
        query["organization_id"] = organization_id
    
    if status:
        query["status"] = status
    if supplier_id:
        query["supplier_id"] = supplier_id
    
    purchase_orders = await PurchaseOrder.find(query).skip(skip).limit(limit).to_list()
    return purchase_orders


@router.post("/", response_model=PurchaseOrderResponse)
async def create_purchase_order(
    po_in: PurchaseOrderCreate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new purchase order within an organization.
    """
    data = po_in.model_dump()
    if organization_id:
        data["organization_id"] = organization_id
        
    existing = await PurchaseOrder.find_one({
        "organization_id": data["organization_id"],
        "po_number": po_in.po_number
    })
    if existing:
        raise HTTPException(
            status_code=400,
            detail="A purchase order with this number already exists",
        )
    
    # Convert POItemCreate to POItem
    data["items"] = [POItem(**item) for item in data["items"]]
    
    purchase_order = PurchaseOrder(**data)
    await purchase_order.create()
    return purchase_order


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def read_purchase_order(
    po_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get purchase order by ID within an organization.
    """
    query = {"_id": PydanticObjectId(po_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    purchase_order = await PurchaseOrder.find_one(query)
    if not purchase_order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return purchase_order


@router.put("/{po_id}", response_model=PurchaseOrderResponse)
async def update_purchase_order(
    po_id: str,
    po_in: PurchaseOrderUpdate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a purchase order within an organization.
    """
    query = {"_id": PydanticObjectId(po_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    purchase_order = await PurchaseOrder.find_one(query)
    if not purchase_order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    update_data = po_in.model_dump(exclude_unset=True)
    
    # Prevent organization_id modification
    if "organization_id" in update_data:
        del update_data["organization_id"]
        
    # Convert items if present
    if "items" in update_data and update_data["items"]:
        update_data["items"] = [POItem(**item) for item in update_data["items"]]
    
    update_data["updated_at"] = datetime.utcnow()
    await purchase_order.update({"$set": update_data})
    await purchase_order.save()
    return purchase_order


@router.delete("/{po_id}", response_model=PurchaseOrderResponse)
async def delete_purchase_order(
    po_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a purchase order within an organization.
    """
    query = {"_id": PydanticObjectId(po_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    purchase_order = await PurchaseOrder.find_one(query)
    if not purchase_order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    await purchase_order.delete()
    return purchase_order


@router.post("/{po_id}/approve", response_model=PurchaseOrderResponse)
async def approve_purchase_order(
    po_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Approve a purchase order.
    """
    query = {"_id": PydanticObjectId(po_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    purchase_order = await PurchaseOrder.find_one(query)
    if not purchase_order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    if purchase_order.status != "pending_approval":
        raise HTTPException(status_code=400, detail="Purchase order is not pending approval")
    
    await purchase_order.update({
        "$set": {
            "status": "approved",
            "approved_by": str(current_user.id),
            "updated_at": datetime.utcnow()
        }
    })
    await purchase_order.save()
    return purchase_order


@router.get("/stats/summary", response_model=dict)
async def get_po_stats(
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get purchase order statistics for an organization.
    """
    query = {}
    if organization_id:
        query["organization_id"] = organization_id
        
    total = await PurchaseOrder.find(query).count()
    pending = await PurchaseOrder.find({
        **query,
        "status": "pending_approval"
    }).count()
    ordered = await PurchaseOrder.find({
        **query,
        "status": "ordered"
    }).count()
    received = await PurchaseOrder.find({
        **query,
        "status": "received"
    }).count()
    
    return {
        "total_orders": total,
        "pending_approval": pending,
        "ordered": ordered,
        "received": received
    }


@router.post("/{po_id}/receive", response_model=PurchaseOrderResponse)
async def receive_purchase_order(
    po_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Mark a purchase order as received and update product variant stock.
    """
    query = {"_id": PydanticObjectId(po_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    purchase_order = await PurchaseOrder.find_one(query)
    if not purchase_order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    if purchase_order.status == "received":
        raise HTTPException(status_code=400, detail="Purchase order is already received")
    
    # Update inventory for each item
    for item in purchase_order.items:
        # Use organization_id from the PO itself for data consistency
        product = await Product.find_one({
            "_id": PydanticObjectId(item.product_id),
            "organization_id": purchase_order.organization_id
        })
        
        if product:
            # Find the variant by SKU
            variant_idx = -1
            if item.sku:
                item_sku_clean = item.sku.strip().upper()
                for i, v in enumerate(product.variants):
                    if v.sku.strip().upper() == item_sku_clean:
                        variant_idx = i
                        break
            
            # If SKU not found but only one variant, use that
            if variant_idx == -1 and len(product.variants) == 1:
                variant_idx = 0
            
            if variant_idx != -1:
                # Update variant stock
                product.variants[variant_idx].stock += item.quantity_ordered
                
                # Update total status
                total_stock = sum(v.stock for v in product.variants)
                # Use a consistent default reorder point of 10 if not specified
                effective_reorder_point = product.reorder_point if product.reorder_point is not None else 10
                
                if total_stock == 0:
                    product.status = "out_of_stock"
                elif total_stock <= effective_reorder_point:
                    product.status = "low_stock"
                else:
                    product.status = "active"
                
                product.updated_at = datetime.utcnow()
                await product.save()
                
                # Create stock movement record
                movement = StockMovement(
                    organization_id=purchase_order.organization_id,
                    product_id=item.product_id,
                    product_name=product.name,
                    sku=item.sku or product.variants[variant_idx].sku,
                    type=MovementType.RECEIVED,
                    quantity=item.quantity_ordered,
                    reference=purchase_order.po_number,
                    performed_by=str(current_user.id)
                )
                await movement.create()

    # Update PO status
    purchase_order.status = "received"
    purchase_order.received_date = datetime.utcnow().date()
    purchase_order.updated_at = datetime.utcnow()
    # Mark all items as fully received if not already
    for item in purchase_order.items:
        item.quantity_received = item.quantity_ordered
        
    await purchase_order.save()
    return purchase_order
