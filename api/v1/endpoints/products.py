from typing import List, Any, Optional, Union
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from beanie import PydanticObjectId
from api import deps
from core.uploads import build_upload_url, get_upload_dir
from models.user import User
from models.product import Product, ProductStatus
from models.alert import Alert, AlertType, AlertPriority
from schemas.product import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter()


@router.post("/upload-image", response_model=dict)
async def upload_product_image(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Upload a product image and return the path.
    Accepts HEIC/HEIF (iPhone) and converts to JPEG for browser display.
    """
    from core.image_upload import prepare_image_upload
    from core.uploads import upload_to_gridfs

    # Create directory if not exists
    get_upload_dir("products")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    prepared_bytes, filename, content_type = prepare_image_upload(
        file_bytes, file.filename, file.content_type
    )
    url = await upload_to_gridfs(
        prepared_bytes, filename, bucket_name="products", content_type=content_type
    )
    return {"url": url}


@router.get("/", response_model=List[ProductResponse])
async def read_products(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    location_id: Optional[str] = None,
    warehouse_id: Optional[str] = None,
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
    if location_id:
        query["location_id"] = location_id
    if warehouse_id:
        query["warehouse_id"] = warehouse_id
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

    # Notify installed PWA shoppers about new arrivals (best-effort, awaited so it actually sends)
    try:
        from services.web_push import notify_new_arrival

        for product in created_products:
            if not product.name:
                continue
            result = await notify_new_arrival(
                str(organization_id), product.name, str(product.id)
            )
            print(f"New-arrival push: {result}")
    except Exception as e:
        print(f"Failed to send new-arrival push: {e}")
    
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
    
    query: dict = {"_id": obj_id}
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
    
    query: dict = {"_id": obj_id}
    if organization_id:
        query["organization_id"] = organization_id
        
    product = await Product.find_one(query)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    was_on_promo = bool(getattr(product, "is_on_promotion", False))
    
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
        if key == "variants" and value is not None:
            from models.product import ProductVariant
            value = [ProductVariant(**v) if isinstance(v, dict) else v for v in value]
        setattr(product, key, value)
    
    # Recalculate status
    total_stock = sum(v.stock for v in product.variants)
    effective_reorder_point = product.reorder_point if product.reorder_point is not None else 10
    product_id_str = str(product.id)
    org_id = product.organization_id

    if total_stock == 0:
        product.status = ProductStatus.OUT_OF_STOCK
        existing = await Alert.find_one({
            "organization_id": org_id, "product_id": product_id_str,
            "type": AlertType.OUT_OF_STOCK, "is_dismissed": False,
        })
        if not existing:
            await Alert(
                organization_id=org_id, type=AlertType.OUT_OF_STOCK,
                priority=AlertPriority.CRITICAL,
                title=f"Out of Stock: {product.name}",
                message=f"{product.name} has run out of stock.",
                product_id=product_id_str, action_url="/Inventory",
            ).create()
    elif total_stock <= effective_reorder_point:
        product.status = ProductStatus.LOW_STOCK
        existing = await Alert.find_one({
            "organization_id": org_id, "product_id": product_id_str,
            "type": AlertType.LOW_STOCK, "is_dismissed": False,
        })
        if not existing:
            await Alert(
                organization_id=org_id, type=AlertType.LOW_STOCK,
                priority=AlertPriority.HIGH,
                title=f"Low Stock: {product.name}",
                message=f"{product.name} is at reorder point ({effective_reorder_point} units). Current stock: {total_stock}.",
                product_id=product_id_str, action_url="/Inventory",
            ).create()
    else:
        product.status = ProductStatus.ACTIVE
        
    product.updated_at = datetime.utcnow()
    await product.save()

    # Notify shoppers when a promotion is saved/activated (awaited so delivery isn't dropped)
    now_on_promo = bool(getattr(product, "is_on_promotion", False))
    promo_touched = any(
        k in update_data
        for k in ("is_on_promotion", "promotion_start", "promotion_end", "variants")
    )
    if now_on_promo and (not was_on_promo or promo_touched):
        try:
            from services.web_push import notify_promotion

            result = await notify_promotion(
                str(product.organization_id), product.name, str(product.id)
            )
            print(f"Promotion push: {result}")
        except Exception as e:
            print(f"Failed to send promotion push: {e}")

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
    
    query: dict = {"_id": obj_id}
    if organization_id:
        query["organization_id"] = organization_id
        
    product = await Product.find_one(query)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    # Delete images from storage
    from core.uploads import delete_upload
    if product.image_url:
        await delete_upload(product.image_url)
    for v in product.variants:
        if v.image_url:
            await delete_upload(v.image_url)
            
    await product.delete()
    return product


@router.get("/aging/", response_model=List[ProductResponse])
async def get_aging_products(
    days_threshold: int = Query(default=30, description="Products not restocked in this many days"),
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get aging inventory: products not restocked in `days_threshold` days (or never restocked),
    sorted oldest-first. Useful for stock session / FIFO management.
    """
    from datetime import timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_threshold)
    query: dict = {}
    if organization_id:
        query["organization_id"] = organization_id
    all_products = await Product.find(query).to_list()
    aging = [
        p for p in all_products
        if p.last_restocked is None or datetime(
            p.last_restocked.year, p.last_restocked.month,
            p.last_restocked.day, tzinfo=timezone.utc
        ) < cutoff
    ]
    aging.sort(key=lambda p: (
        datetime(p.last_restocked.year, p.last_restocked.month, p.last_restocked.day, tzinfo=timezone.utc)
        if p.last_restocked else datetime.min.replace(tzinfo=timezone.utc)
    ))
    return aging


@router.get("/expiring/", response_model=List[ProductResponse])
async def get_expiring_products(
    days_threshold: int = Query(default=90, description="Fetch products expiring within this many days"),
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get products expiring within `days_threshold` (e.g., 30, 60, 90 days),
    sorted by earliest expiry date (FEFO - First Expired, First Out).
    """
    from datetime import date, timedelta
    today = date.today()
    max_expiry = today + timedelta(days=days_threshold)
    
    query: dict = {
        "expiry_date": {"$ne": None, "$lte": max_expiry}
    }
    if organization_id:
        query["organization_id"] = organization_id

    products = await Product.find(query).to_list()
    # Sort FEFO
    products.sort(key=lambda p: p.expiry_date if p.expiry_date else date.max)

    # Auto-generate alerts for products expiring within 30 days
    thirty_days_limit = today + timedelta(days=30)
    for p in products:
        if p.expiry_date and p.expiry_date <= thirty_days_limit:
            p_id_str = str(p.id)
            org_id = p.organization_id
            existing = await Alert.find_one({
                "organization_id": org_id,
                "product_id": p_id_str,
                "type": AlertType.EXPIRING,
                "is_dismissed": False
            })
            if not existing:
                await Alert(
                    organization_id=org_id,
                    type=AlertType.EXPIRING,
                    priority=AlertPriority.HIGH,
                    title=f"Expiring Item: {p.name}",
                    message=f"{p.name} expires on {p.expiry_date.strftime('%Y-%m-%d')}. Current stock: {p.total_stock}.",
                    product_id=p_id_str,
                    action_url="/Inventory"
                ).create()

    return products

