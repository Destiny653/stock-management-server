import os
import uuid
from typing import List, Any, Optional, Union
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


@router.post("/", response_model=Union[ProductResponse, List[ProductResponse]])
async def create_product(
    product_in: Union[ProductCreate, List[ProductCreate]],
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new product(s) within an organization.
    Accepts either a single product or a list of products.
    """
    # Normalize to a list for processing
    products_to_create = product_in if isinstance(product_in, list) else [product_in]
    
    if not products_to_create:
         raise HTTPException(status_code=400, detail="Empty product list")

    # Determine organization_id
    if not organization_id:
        # Try to get from the first product if not provided via dependency (e.g. platform-staff)
        organization_id = products_to_create[0].organization_id
    
    if not organization_id:
        raise HTTPException(
            status_code=400,
            detail="organization_id is required"
        )

    # Collect all SKUs from all products to check uniqueness
    all_variant_skus = []
    for p in products_to_create:
        all_variant_skus.extend([v.sku for v in p.variants])
    
    if all_variant_skus:
        # Check uniqueness within the organization
        existing_product = await Product.find_one({
            "organization_id": organization_id,
            "variants.sku": {"$in": all_variant_skus}
        })
        if existing_product:
            raise HTTPException(
                status_code=400,
                detail="One or more SKUs already exist in this organization",
            )
    
    created_products = []
    for p_in in products_to_create:
        data = p_in.model_dump()
        data["organization_id"] = organization_id
        product = Product(**data)
        await product.create()
        created_products.append(product)
    
    # Return single object if input was single, else return list
    return created_products[0] if not isinstance(product_in, list) else created_products


@router.post("/bulk", response_model=List[ProductResponse])
async def create_products_bulk(
    products_in: List[ProductCreate],
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Explicitly create multiple products at once.
    """
    return await create_product(product_in=products_in, organization_id=organization_id, current_user=current_user)


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
