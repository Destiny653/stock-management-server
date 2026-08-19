"""Sale endpoints"""
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from beanie import PydanticObjectId
from api import deps
from models.user import User
from models.sale import Sale, SaleItem
from models.product import Product
from models.stock_movement import StockMovement, MovementType
from schemas.sale import SaleCreate, SaleUpdate, SaleResponse
from services.notification import send_low_stock_alert
from services.notification_helpers import get_org_notification_recipients

router = APIRouter()


@router.get("/", response_model=List[SaleResponse])
async def read_sales(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    vendor_id: Optional[str] = None,
    payment_method: Optional[str] = None,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve sales. Filtered by organization for non-superadmins.
    """
    query = {}
    if organization_id:
        query["organization_id"] = organization_id
    
    if status:
        query["status"] = status
    if vendor_id:
        query["vendor_id"] = vendor_id
    if payment_method:
        query["payment_method"] = payment_method
    
    sales = await Sale.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
    return sales


@router.post("/", response_model=SaleResponse)
async def create_sale(
    sale_in: SaleCreate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new sale within an organization and update product quantities & ledger.
    """
    import uuid
    data = sale_in.model_dump()
    if not data.get("organization_id"):
        data["organization_id"] = organization_id or getattr(current_user, "organization_id", None)
    
    if not data.get("organization_id"):
        raise HTTPException(status_code=400, detail="organization_id is required")

    org_id = data["organization_id"]

    # Ensure vendor details
    if not data.get("vendor_name"):
        data["vendor_name"] = current_user.full_name or current_user.username or "POS Cashier"
    if not data.get("vendor_id"):
        data["vendor_id"] = str(current_user.id)

    # Customer fallback mapping
    if data.get("client_name") and not data.get("customer_name"):
        data["customer_name"] = data["client_name"]
    if not data.get("customer_name"):
        data["customer_name"] = "Walk-in Customer"

    # Auto generate sale_number if missing
    if not data.get("sale_number"):
        cnt = await Sale.find(Sale.organization_id == org_id).count()
        data["sale_number"] = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{cnt+1:04d}-{uuid.uuid4().hex[:4].upper()}"
        
    existing = await Sale.find_one({
        "organization_id": org_id,
        "sale_number": data["sale_number"]
    })
    if existing:
        data["sale_number"] = f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

    # Convert items and calculate COGS
    sale_items = []
    total_cogs = 0.0
    
    for item in data["items"]:
        try:
            prod_id = PydanticObjectId(item["product_id"])
        except Exception:
            prod_id = item["product_id"]
            
        product = await Product.find_one({
            "_id": prod_id
        })
        
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product '{item['product_name']}' not found."
            )

        unit_cost = getattr(product, "cost_price", 0.0) or 0.0
        cogs_item = unit_cost * item["quantity"]
        total_cogs += cogs_item
        item["unit_cost"] = unit_cost
        item["cogs"] = cogs_item

        # Deduct total stock on main product
        if product.total_stock >= item["quantity"]:
            product.total_stock -= item["quantity"]
        else:
            product.total_stock = 0

        # Update variant if matched
        if product.variants:
            v_idx = -1
            if item.get("sku"):
                for i, v in enumerate(product.variants):
                    if v.sku == item["sku"]:
                        v_idx = i
                        break
            if v_idx == -1 and len(product.variants) == 1:
                v_idx = 0
            if v_idx != -1:
                product.variants[v_idx].stock = max(0, product.variants[v_idx].stock - item["quantity"])

        # Update product status
        if product.total_stock <= 0:
            product.status = "out_of_stock"
        elif product.total_stock <= (product.reorder_point or 0):
            product.status = "low_stock"
        else:
            product.status = "active"

        product.updated_at = datetime.utcnow()
        await product.save()

        # Create stock movement record
        movement = StockMovement(
            organization_id=org_id,
            product_id=str(product.id),
            product_name=item["product_name"],
            sku=item.get("sku") or product.sku,
            type=MovementType.STOCK_OUT,
            quantity=-item["quantity"],
            reference=data["sale_number"],
            notes=f"POS Sale #{data['sale_number']}",
            unit_cost=unit_cost,
            unit_price=item["unit_price"],
            total_cost=cogs_item,
            actor_id=str(current_user.id),
            actor_name=current_user.username or current_user.full_name or "POS Cashier",
        )
        await movement.create()
        sale_items.append(SaleItem(**item))
    
    data["items"] = sale_items
    data["cogs_total"] = total_cogs
    data["gross_profit"] = data.get("total", 0.0) - total_cogs
    data["cashier_id"] = str(current_user.id)
    data["cashier_name"] = current_user.username or current_user.full_name or "POS Cashier"

    sale = Sale(**data)
    await sale.create()
    return sale


@router.get("/{sale_id}", response_model=SaleResponse)
async def read_sale(
    sale_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get sale by ID within an organization.
    """
    query = {"_id": PydanticObjectId(sale_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    sale = await Sale.find_one(query)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale


@router.put("/{sale_id}", response_model=SaleResponse)
async def update_sale(
    sale_id: str,
    sale_in: SaleUpdate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a sale within an organization.
    """
    query = {"_id": PydanticObjectId(sale_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    sale = await Sale.find_one(query)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    update_data = sale_in.model_dump(exclude_unset=True)
    
    # Prevent organization_id update
    if "organization_id" in update_data:
        del update_data["organization_id"]
        
    # Convert items if present
    if "items" in update_data and update_data["items"]:
        update_data["items"] = [SaleItem(**item) for item in update_data["items"]]
    
    update_data["updated_at"] = datetime.utcnow()
    await sale.update({"$set": update_data})
    await sale.save()
    return sale


@router.delete("/{sale_id}", response_model=SaleResponse)
async def delete_sale(
    sale_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a sale within an organization.
    """
    query = {"_id": PydanticObjectId(sale_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    sale = await Sale.find_one(query)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    await sale.delete()
    return sale


@router.get("/stats/summary", response_model=dict)
async def get_sales_stats(
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get sales statistics for an organization.
    """
    query = {}
    if organization_id:
        query["organization_id"] = organization_id
        
    total = await Sale.find(query).count()
    completed = await Sale.find({
        **query,
        "status": "completed"
    }).count()
    
    # Calculate total revenue
    all_sales = await Sale.find({
        **query,
        "status": "completed"
    }).to_list()
    total_revenue = sum(sale.total for sale in all_sales)
    
    
    return {
        "total": total,
        "completed": completed,
        "revenue": round(revenue, 2),
        "avg_order_value": round(avg_order_value, 2)
    }


@router.post("/{sale_id}/return", response_model=SaleResponse)
async def process_sale_return(
    sale_id: str,
    reason: Optional[str] = Query("Customer Return"),
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Process a customer sale return, restoring inventory levels and recording stock movement.
    """
    query = {"_id": PydanticObjectId(sale_id)}
    if organization_id:
        query["organization_id"] = organization_id

    sale = await Sale.find_one(query)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale record not found")

    if sale.status == "refunded":
        raise HTTPException(status_code=400, detail="Sale has already been fully refunded")

    # Restore stock for items
    for item in sale.items:
        try:
            prod_id = PydanticObjectId(item.product_id)
        except Exception:
            prod_id = item.product_id

        product = await Product.find_one({"_id": prod_id})
        if product:
            product.total_stock += item.quantity
            if product.total_stock > 0:
                product.status = "active"
            product.updated_at = datetime.utcnow()
            await product.save()

            # Record stock movement for return
            movement = StockMovement(
                organization_id=sale.organization_id,
                product_id=str(product.id),
                product_name=item.product_name,
                sku=item.sku or product.sku,
                type=MovementType.STOCK_IN,
                quantity=item.quantity,
                reference=sale.sale_number,
                notes=f"Customer Return: {reason}",
                unit_cost=item.unit_cost,
                unit_price=item.unit_price,
                total_cost=item.cogs,
                actor_id=str(current_user.id),
                actor_name=current_user.username or current_user.full_name or "System",
            )
            await movement.create()

    sale.status = "refunded"
    sale.payment_status = "refunded"
    sale.updated_at = datetime.utcnow()
    await sale.save()
    return sale
