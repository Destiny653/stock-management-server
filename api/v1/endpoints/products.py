import os
import uuid
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from beanie import PydanticObjectId
from api import deps
from models.user import User
from models.product import Product
from schemas.product import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter()


@router.post("/upload-image", response_model=dict)
async def upload_product_image(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Upload a product image and return the path.
    """
    # Check if file is an image
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    

    # Create directory if not exists
    upload_dir = "uploads/products"
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    # Return the URL/path
    return {"url": f"/uploads/products/{filename}"}


@router.get("/", response_model=List[ProductResponse])
async def read_products(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve products. Filtered by organization for non-superadmins.
    """
    query = {}
    if organization_id:
        query["organization_id"] = organization_id
    
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"variants.sku": {"$regex": search, "$options": "i"}},
        ]
    
    products = await Product.find(query).skip(skip).limit(limit).to_list()
    return products


@router.post("/", response_model=ProductResponse)
async def create_product(
    product_in: ProductCreate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new product within an organization.
    """
    data = product_in.model_dump()
    if organization_id:
        data["organization_id"] = organization_id
        
    # Check if any variant SKUs already exist within the organization
    variant_skus = [v.sku for v in product_in.variants]
    if variant_skus:
        existing_product = await Product.find_one({
            "organization_id": data["organization_id"],
            "variants.sku": {"$in": variant_skus}
        })
        if existing_product:
            raise HTTPException(
                status_code=400,
                detail="A product with one of these SKUs already exists in this organization",
            )
    product = Product(**data)
    await product.create()
    return product


@router.get("/{product_id}", response_model=ProductResponse)
async def read_product(
    product_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get product by ID within an organization.
    """
    try:
        obj_id = PydanticObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    
    query = {"_id": obj_id}
    if organization_id:
        query["organization_id"] = organization_id
        
    product = await Product.find_one(query)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_in: ProductUpdate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a product within an organization.
    """
    try:
        obj_id = PydanticObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    
    query = {"_id": obj_id}
    if organization_id:
        query["organization_id"] = organization_id
        
    product = await Product.find_one(query)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product_in.model_dump(exclude_unset=True)
    
    # Check SKU uniqueness if variants are being updated
    if "variants" in update_data:
        variant_skus = [v["sku"] for v in update_data["variants"]]
        if variant_skus:
            sku_query = {
                "organization_id": product.organization_id,
                "_id": {"$ne": obj_id},
                "variants.sku": {"$in": variant_skus}
            }
            existing_product = await Product.find_one(sku_query)
            if existing_product:
                raise HTTPException(
                    status_code=400,
                    detail="One of the provided variant SKUs already exists in another product",
                )
    
    # Prevent organization_id modification
    if "organization_id" in update_data:
        del update_data["organization_id"]

    # Apply updates to the product object
    for key, value in update_data.items():
        setattr(product, key, value)
    
    # Recalculate status
    total_stock = sum(v.stock if hasattr(v, "stock") else v.get("stock", 0) for v in product.variants)
    if total_stock == 0:
        product.status = "out_of_stock"
    elif total_stock <= (product.reorder_point or 0):
        product.status = "low_stock"
    else:
        product.status = "active"
        
    product.updated_at = datetime.utcnow()
    await product.save()
    return product


@router.delete("/{product_id}", response_model=ProductResponse)
async def delete_product(
    product_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a product within an organization.
    """
    try:
        obj_id = PydanticObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    
    query = {"_id": obj_id}
    if organization_id:
        query["organization_id"] = organization_id
        
    product = await Product.find_one(query)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    await product.delete()
    return product


@router.get("/low-stock/", response_model=List[ProductResponse])
async def get_low_stock_products(
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get products that are at or below their reorder point.
    """
    query = {
        "$expr": {
            "$lte": [
                {"$sum": "$variants.stock"},
                "$reorder_point"
            ]
        }
    }
    if organization_id:
        query["organization_id"] = organization_id
        
    products = await Product.find(query).to_list()
    return products
