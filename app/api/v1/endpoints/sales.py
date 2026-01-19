"""Sale endpoints"""
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from beanie import PydanticObjectId
from app.api import deps
from app.models.user import User
from app.models.sale import Sale, SaleItem
from app.models.product import Product
from app.models.stock_movement import StockMovement, MovementType
from app.schemas.sale import SaleCreate, SaleUpdate, SaleResponse

router = APIRouter()


@router.get("/", response_model=List[SaleResponse])
async def read_sales(
    organization_id: str = Query(..., description="Organization ID to filter by"),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    vendor_id: Optional[str] = None,
    payment_method: Optional[str] = None,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve sales for a specific organization.
    """
    query = {"organization_id": organization_id}
    
    if status:
        query["status"] = status
    if vendor_id:
        query["vendor_id"] = vendor_id
    if payment_method:
        query["payment_method"] = payment_method
    
    sales = await Sale.find(query).skip(skip).limit(limit).to_list()
    return sales


@router.post("/", response_model=SaleResponse)
async def create_sale(
    sale_in: SaleCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new sale within an organization and update product quantities.
    """
    existing = await Sale.find_one({
        "organization_id": sale_in.organization_id,
        "sale_number": sale_in.sale_number
    })
    if existing:
        raise HTTPException(
            status_code=400,
            detail="A sale with this number already exists",
        )
    
    # Convert SaleItemCreate to SaleItem and update product quantities
    sale_data = sale_in.model_dump()
    sale_items = []
    
    for item in sale_data["items"]:
        # Update product quantity
        try:
            prod_id = PydanticObjectId(item["product_id"])
        except:
            prod_id = item["product_id"]
            
        product = await Product.find_one({
            "_id": prod_id,
            "organization_id": sale_in.organization_id
        })
        
        if product:
            # Find the variant by SKU
            variant_idx = -1
            if item.get("sku"):
                for i, v in enumerate(product.variants):
                    if v.sku == item["sku"]:
                        variant_idx = i
                        break
            
            # If SKU not found but only one variant, use that
            if variant_idx == -1 and len(product.variants) == 1:
                variant_idx = 0
            
            if variant_idx == -1:
                raise HTTPException(
                    status_code=400,
                    detail=f"Specific variant SKU is required for product {item['product_name']}"
                )

            new_stock = product.variants[variant_idx].stock - item["quantity"]
            if new_stock < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for variant {item.get('sku', 'default')} of product {item['product_name']}"
                )
            
            # Update variant stock
            product.variants[variant_idx].stock = new_stock
            
            # Update status based on total quantity
            total_stock = sum(v.stock for v in product.variants)
            if total_stock == 0:
                product.status = "out_of_stock"
            elif total_stock <= (product.reorder_point or 0):
                product.status = "low_stock"
            else:
                product.status = "active"

            product.updated_at = datetime.utcnow()
            await product.save()

            # Create stock movement
            movement = StockMovement(
                organization_id=sale_in.organization_id,
                product_id=item["product_id"],
                product_name=item["product_name"],
                sku=item.get("sku"),
                type=MovementType.DISPATCHED,
                quantity=-item["quantity"],
                reference=sale_in.sale_number,
                notes=f"Direct sale to {sale_in.client_name or 'Walk-in customer'}"
            )
            await movement.create()
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Product {item['product_name']} (ID: {item['product_id']}) not found"
            )
        sale_items.append(SaleItem(**item))
    
    sale_data["items"] = sale_items
    sale = Sale(**sale_data)
    await sale.create()
    return sale


@router.get("/{sale_id}", response_model=SaleResponse)
async def read_sale(
    sale_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get sale by ID within an organization.
    """
    sale = await Sale.find_one({
        "_id": PydanticObjectId(sale_id),
        "organization_id": organization_id
    })
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale


@router.put("/{sale_id}", response_model=SaleResponse)
async def update_sale(
    sale_id: str,
    sale_in: SaleUpdate,
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a sale within an organization.
    """
    sale = await Sale.find_one({
        "_id": PydanticObjectId(sale_id),
        "organization_id": organization_id
    })
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    update_data = sale_in.model_dump(exclude_unset=True)
    
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
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a sale within an organization.
    """
    sale = await Sale.find_one({
        "_id": sale_id,
        "organization_id": organization_id
    })
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    await sale.delete()
    return sale


@router.get("/stats/summary", response_model=dict)
async def get_sales_stats(
    organization_id: str = Query(..., description="Organization ID"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get sales statistics for an organization.
    """
    total = await Sale.find({"organization_id": organization_id}).count()
    completed = await Sale.find({
        "organization_id": organization_id,
        "status": "completed"
    }).count()
    
    # Calculate total revenue
    all_sales = await Sale.find({
        "organization_id": organization_id,
        "status": "completed"
    }).to_list()
    total_revenue = sum(sale.total for sale in all_sales)
    
    return {
        "total_sales": total,
        "completed_sales": completed,
        "total_revenue": total_revenue
    }
