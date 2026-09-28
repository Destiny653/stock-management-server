"""Public storefront API – no authentication required"""
import uuid
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from beanie import PydanticObjectId

from models.platform_settings import PlatformSettings
from models.storefront_config import StorefrontConfig
from models.organization import Organization
from models.product import Product
from models.product_review import ProductReview
from models.storefront_order import StorefrontOrder, StorefrontOrderItem
from models.category import Category
from models.warehouse import Warehouse
from models.location import Location
from models.alert import Alert, AlertType, AlertPriority
from schemas.product_review import ReviewCreate, ReviewResponse
from schemas.storefront_order import StorefrontOrderCreate, StorefrontOrderResponse

router = APIRouter()


async def _get_config_by_slug(slug: str) -> StorefrontConfig:
    config = await StorefrontConfig.find_one({"slug": slug})
    if not config:
        raise HTTPException(status_code=404, detail="Store not found")
    return config


@router.get("/{slug}")
async def get_storefront(slug: str) -> Any:
    """Get storefront configuration by slug (public)."""
    config = await _get_config_by_slug(slug)
    platform_settings = await PlatformSettings.find_one()
    default_hero = platform_settings.default_hero_image if platform_settings else None
    allowed_payments = platform_settings.allowed_payment_methods if platform_settings else [
        "momo",
        "orange-money",
        "visa",
        "mastercard",
        "apple-pay",
        "google-pay",
        "paypal",
    ]

    # Prefer storefront brand assets; fall back to organization logo for site/PWA icon
    org_logo = None
    try:
        org_id = config.organization_id
        org = None
        if org_id:
            try:
                org = await Organization.get(PydanticObjectId(org_id))
            except Exception:
                org = await Organization.find_one({"_id": org_id})
            if not org:
                org = await Organization.find_one({"_id": str(org_id)})
        if org and getattr(org, "logo_url", None):
            org_logo = org.logo_url
    except Exception:
        org_logo = None

    data = config.model_dump()
    data["id"] = str(config.id)
    data["default_hero_image"] = default_hero
    data["allowed_payment_methods"] = allowed_payments
    if not data.get("logo_url") and org_logo:
        data["logo_url"] = org_logo
    if not data.get("favicon_url"):
        data["favicon_url"] = data.get("logo_url") or org_logo
    data["organization_logo_url"] = org_logo
    return data


@router.get("/{slug}/products")
async def get_storefront_products(
    slug: str,
    search: Optional[str] = None,
    category: Optional[str] = None,
    location: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    ids: Optional[str] = Query(default=None, description="Comma-separated product IDs"),
    on_promotion: Optional[bool] = Query(
        default=None,
        description="If true, only products flagged is_on_promotion",
    ),
    sort: Optional[str] = Query(default="newest", pattern="^(newest|price_asc|price_desc|name_asc|name_desc|rating|best_selling|featured)$"),
    skip: int = 0,
    limit: int = 24,
) -> Any:
    """List products for a storefront with filtering & sorting (public)."""
    config = await _get_config_by_slug(slug)
    org_id = config.organization_id

    query: dict = {"organization_id": org_id, "status": {"$ne": "discontinued"}}

    if config.excluded_category_names:
        query["category"] = {"$nin": config.excluded_category_names}

    # Fast path: fetch specific wishlist / cart IDs
    id_list: list[str] = []
    if ids:
        id_list = [i.strip() for i in ids.split(",") if i.strip()]
        obj_ids = []
        for i in id_list:
            try:
                obj_ids.append(PydanticObjectId(i))
            except Exception:
                continue
        if obj_ids:
            query["_id"] = {"$in": obj_ids}
        else:
            return {"products": [], "total": 0}

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"variants.sku": {"$regex": search, "$options": "i"}},
        ]

    if category:
        query["category"] = category

    if on_promotion is True:
        query["is_on_promotion"] = True

    if location:
        location_query = {"$or": [{"location_id": location}, {"warehouse_id": location}]}
        if "$or" in query:
            existing_or = query.pop("$or")
            query["$and"] = [{"$or": existing_or}, location_query]
        else:
            query.update(location_query)

    # Keep ranking window small — large windows + per-product reviews were killing latency
    fetch_limit = limit
    fetch_skip = skip
    if not id_list and sort in ("best_selling", "featured", "rating"):
        fetch_skip = 0
        fetch_limit = min(max(limit + skip, limit * 2), 48)
    # Promotions: allow a wider window so newly flagged items aren't truncated by "newest"
    if on_promotion is True:
        fetch_limit = min(max(limit, 48), 100)

    find_q = Product.find(query)
    # Push simple sorts to Mongo so skip/limit return the right page without loading extras
    if sort == "newest":
        find_q = find_q.sort("-updated_at" if on_promotion else "-created_at")
    elif sort == "name_asc":
        find_q = find_q.sort("+name")
    elif sort == "name_desc":
        find_q = find_q.sort("-name")

    products = await find_q.skip(fetch_skip).limit(fetch_limit).to_list()

    # Price filtering (post-query since price is in variants)
    if min_price is not None or max_price is not None:
        filtered = []
        for p in products:
            if not p.variants:
                continue
            lowest = min(v.unit_price for v in p.variants)
            if min_price is not None and lowest < min_price:
                continue
            if max_price is not None and lowest > max_price:
                continue
            filtered.append(p)
        products = filtered

    # In-memory sorts that depend on variant prices / featured order
    if sort == "price_asc":
        products.sort(key=lambda p: min((v.unit_price for v in p.variants), default=0))
    elif sort == "price_desc":
        products.sort(key=lambda p: min((v.unit_price for v in p.variants), default=0), reverse=True)
    elif sort == "featured":
        featured_ids = config.featured_product_ids or []
        products.sort(key=lambda p: (0 if str(p.id) in featured_ids else 1, p.created_at), reverse=False)

    # Aggregate ratings in one query (avoid loading every review document)
    product_ids = [str(p.id) for p in products]
    rating_map: dict[str, tuple[float, int]] = {pid: (0.0, 0) for pid in product_ids}
    if product_ids:
        rating_rows = await ProductReview.aggregate([
            {
                "$match": {
                    "product_id": {"$in": product_ids},
                    "is_approved": True,
                }
            },
            {
                "$group": {
                    "_id": "$product_id",
                    "avg": {"$avg": "$rating"},
                    "count": {"$sum": 1},
                }
            },
        ]).to_list()
        for row in rating_rows:
            pid = row.get("_id")
            if not pid:
                continue
            rating_map[pid] = (round(float(row.get("avg") or 0), 1), int(row.get("count") or 0))

    result = []
    for p in products:
        total_stock = sum(v.stock for v in p.variants)

        is_on_promotion = bool(getattr(p, "is_on_promotion", False))
        # Flagged in POS → always show promo pricing on the storefront
        apply_promo = is_on_promotion
        has_promo_price = any(
            getattr(v, "promotion_price", None) is not None for v in (p.variants or [])
        )

        original_price = min((v.unit_price for v in p.variants), default=0) if p.variants else 0

        variants_dump = []
        for v in p.variants:
            unit_price = v.unit_price
            vdump = {
                "variant_id": v.variant_id,
                "sku": v.sku,
                "attributes": v.attributes,
                "unit_price": unit_price,
                "stock": v.stock,
                "image_url": v.image_url,
            }
            if apply_promo and getattr(v, "promotion_price", None) is not None:
                vdump["original_price"] = v.unit_price
                vdump["unit_price"] = v.promotion_price
                vdump["promotion_price"] = v.promotion_price
            variants_dump.append(vdump)

        lowest_price = min((v["unit_price"] for v in variants_dump), default=0) if variants_dump else 0
        if apply_promo and has_promo_price and lowest_price >= original_price:
            promo_mins = [
                float(v.promotion_price)
                for v in p.variants
                if getattr(v, "promotion_price", None) is not None
            ]
            if promo_mins:
                lowest_price = min(promo_mins)
                originals = [float(v.unit_price) for v in p.variants]
                if originals and original_price <= lowest_price:
                    original_price = max(originals)

        avg_rating, review_count = rating_map.get(str(p.id), (0.0, 0))

        desc = (p.description or "").strip()
        if len(desc) > 180:
            desc = desc[:180] + "…"

        result.append({
            "id": str(p.id),
            "name": p.name,
            "category": p.category,
            "description": desc or None,
            "image_url": p.image_url,
            "status": p.status,
            "variants": variants_dump,
            "total_stock": total_stock,
            "original_price": original_price,
            "lowest_price": lowest_price,
            "avg_rating": avg_rating,
            "review_count": review_count,
            "is_on_promotion": is_on_promotion,
            "is_promo_active": apply_promo,
            "created_at": p.created_at.isoformat(),
        })

    if sort in ("best_selling", "rating"):
        result.sort(key=lambda x: (x["avg_rating"], x["review_count"]), reverse=True)

    if not id_list and sort in ("best_selling", "featured", "rating"):
        result = result[skip : skip + limit]

    # Preserve wishlist id order when requested
    if id_list:
        order = {pid: i for i, pid in enumerate(id_list)}
        result.sort(key=lambda x: order.get(x["id"], 9999))

    return {"products": result, "total": len(result)}


@router.get("/{slug}/products/{product_id}")
async def get_storefront_product(slug: str, product_id: str) -> Any:
    """Get a single product detail (public)."""
    config = await _get_config_by_slug(slug)

    try:
        obj_id = PydanticObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = await Product.find_one({"_id": obj_id, "organization_id": config.organization_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Fetch reviews
    reviews = await ProductReview.find(
        {"product_id": product_id, "is_approved": True}
    ).sort("-created_at").to_list()
    avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0

    total_stock = sum(v.stock for v in product.variants)

    now = datetime.utcnow()
    is_on_promotion = bool(getattr(product, "is_on_promotion", False))
    apply_promo = is_on_promotion

    original_price = min((v.unit_price for v in product.variants), default=0) if product.variants else 0
    
    variants_dump = []
    for v in product.variants:
        vdump = v.model_dump()
        if apply_promo and getattr(v, "promotion_price", None) is not None:
            vdump["original_price"] = v.unit_price
            vdump["unit_price"] = v.promotion_price
        variants_dump.append(vdump)
        
    lowest_price = min((v["unit_price"] for v in variants_dump), default=0) if variants_dump else 0

    return {
        "id": str(product.id),
        "name": product.name,
        "category": product.category,
        "description": product.description,
        "image_url": product.image_url,
        "status": product.status,
        "variants": variants_dump,
        "total_stock": total_stock,
        "original_price": original_price,
        "lowest_price": lowest_price,
        "avg_rating": avg_rating,
        "review_count": len(reviews),
        "is_on_promotion": is_on_promotion,
        "is_promo_active": apply_promo,
        "reviews": [
            {
                "id": str(r.id),
                "reviewer_name": r.reviewer_name,
                "rating": r.rating,
                "title": r.title,
                "comment": r.comment,
                "created_at": r.created_at.isoformat(),
            }
            for r in reviews
        ],
        "created_at": product.created_at.isoformat(),
    }


@router.get("/{slug}/categories")
async def get_storefront_categories(slug: str) -> Any:
    """List categories for a storefront (public)."""
    config = await _get_config_by_slug(slug)
    categories = await Category.find({"organization_id": config.organization_id}).to_list()

    excluded = set(config.excluded_category_names or [])

    # Single aggregation for counts — was N+1 product+review loads per category (~30s)
    count_rows = await Product.aggregate([
        {
            "$match": {
                "organization_id": config.organization_id,
                "status": {"$ne": "discontinued"},
            }
        },
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
    ]).to_list()
    count_map = {row["_id"]: row["count"] for row in count_rows if row.get("_id")}

    result = []
    for cat in categories:
        if cat.name in excluded:
            continue
        result.append({
            "id": str(cat.id),
            "name": cat.name,
            "description": cat.description,
            "color": cat.color,
            "icon": cat.icon,
            "product_count": count_map.get(cat.name, 0),
            # Ratings come from the products catalog on the client
            "avg_rating": 0.0,
            "review_count": 0,
        })

    return result


@router.get("/{slug}/locations")
async def get_storefront_locations(slug: str) -> Any:
    """List available locations/warehouses for a storefront (public)."""
    config = await _get_config_by_slug(slug)
    
    warehouses = await Warehouse.find({"organization_id": config.organization_id}).to_list()
    locations = await Location.find({"organization_id": config.organization_id}).to_list()
    
    result = []
    for w in warehouses:
        result.append({"id": str(w.id), "name": w.name, "type": "warehouse"})
    for l in locations:
        result.append({"id": str(l.id), "name": l.name, "type": "location"})
        
    return result


@router.get("/{slug}/reviews/{product_id}")
async def get_product_reviews(
    slug: str,
    product_id: str,
    skip: int = 0,
    limit: int = 20,
) -> Any:
    """Get approved reviews for a product (public)."""
    config = await _get_config_by_slug(slug)
    reviews = await ProductReview.find(
        {"product_id": product_id, "organization_id": config.organization_id, "is_approved": True}
    ).sort("-created_at").skip(skip).limit(limit).to_list()

    return [
        {
            "id": str(r.id),
            "reviewer_name": r.reviewer_name,
            "rating": r.rating,
            "title": r.title,
            "comment": r.comment,
            "created_at": r.created_at.isoformat(),
        }
        for r in reviews
    ]


@router.post("/{slug}/reviews/{product_id}")
async def submit_review(slug: str, product_id: str, review_in: ReviewCreate) -> Any:
    """Submit a product review (public, auto-moderated)."""
    config = await _get_config_by_slug(slug)

    if not config.enable_ratings:
        raise HTTPException(status_code=403, detail="Ratings are disabled for this store")

    # Verify product exists
    try:
        obj_id = PydanticObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = await Product.find_one({"_id": obj_id, "organization_id": config.organization_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    review = ProductReview(
        organization_id=config.organization_id,
        product_id=product_id,
        reviewer_name=review_in.reviewer_name,
        reviewer_email=review_in.reviewer_email,
        rating=review_in.rating,
        title=review_in.title,
        comment=review_in.comment,
        is_approved=False,  # Requires moderation
    )
    await review.create()

    return {"message": "Review submitted for moderation", "id": str(review.id)}


from services.stripe import StripeService

@router.post("/{slug}/checkout")
async def submit_order(slug: str, order_in: StorefrontOrderCreate) -> Any:
    """Submit a storefront order and handle payment (USSD or Stripe) (public)."""
    config = await _get_config_by_slug(slug)

    if not config.enable_cart:
        raise HTTPException(status_code=403, detail="Cart/checkout is disabled for this store")

    # Build order items and calculate total
    order_items = []
    subtotal = 0.0

    for item in order_in.items:
        item_total = item.unit_price * item.quantity
        subtotal += item_total
        order_items.append(StorefrontOrderItem(
            product_id=item.product_id,
            product_name=item.product_name,
            sku=item.sku,
            variant_label=item.variant_label,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total=item_total,
            image_url=item.image_url,
        ))

    total = subtotal
    order_ref = f"SF-{uuid.uuid4().hex[:8].upper()}"

    # Determine payment logic
    payment_method = order_in.payment_method
    payment_phone = None
    ussd_string = None
    stripe_client_secret = None
    amount_int = int(total)

    if payment_method == "mtn" and config.payment_phone_mtn:
        payment_phone = config.payment_phone_mtn
        ussd_string = f"*126*9*{config.payment_phone_mtn}*{amount_int}#"
    elif payment_method == "orange" and config.payment_phone_orange:
        payment_phone = config.payment_phone_orange
        ussd_string = f"#150*1*{config.payment_phone_orange}*{amount_int}#"
    elif payment_method == "stripe":
        # Stripe temporarily disabled across the platform
        raise HTTPException(
            status_code=400,
            detail="Card payments (Stripe) are temporarily unavailable. Please use MTN or Orange Money.",
        )

    order = StorefrontOrder(
        organization_id=config.organization_id,
        order_ref=order_ref,
        customer_name=order_in.customer_name,
        customer_email=order_in.customer_email,
        customer_phone=order_in.customer_phone,
        items=order_items,
        subtotal=subtotal,
        total=total,
        payment_method=payment_method,
        payment_phone=payment_phone,
        ussd_string=ussd_string,
        stripe_client_secret=stripe_client_secret,
        notes=order_in.notes,
    )
    await order.create()

    # Create system notification for the purchase order
    try:
        alert = Alert(
            organization_id=config.organization_id,
            type=AlertType.STOREFRONT_ORDER,
            priority=AlertPriority.HIGH,
            title="New Storefront Order",
            message=f"A new order {order_ref} was placed by {order_in.customer_name} for a total of {total} {config.currency or 'XAF'}.",
            action_url=f"/orders?ref={order_ref}"
        )
        await alert.create()
    except Exception as e:
        print(f"Failed to create alert notification: {e}")

    return {
        "order_ref": order_ref,
        "total": total,
        "currency": config.currency,
        "payment_method": payment_method,
        "payment_phone": payment_phone,
        "ussd_string": ussd_string,
        "stripe_client_secret": stripe_client_secret,
        "message": "Order placed successfully",
    }

@router.get("/{slug}/orders")
async def get_customer_orders(
    slug: str,
    phone: str,
    email: Optional[str] = None,
) -> Any:
    """Get orders for a specific customer by phone/email (public)."""
    config = await _get_config_by_slug(slug)
    query: dict = {"organization_id": config.organization_id}
    
    # We allow lookup by phone or email
    if email:
        query["$or"] = [{"customer_phone": phone}, {"customer_email": email}]
    else:
        query["customer_phone"] = phone
        
    orders = await StorefrontOrder.find(query).sort("-created_at").to_list()
    return orders


# ─── Web Push (installed PWA) ───────────────────────────────────────────────

@router.get("/{slug}/push/vapid-key")
async def get_push_vapid_key(slug: str) -> Any:
    """Public VAPID key for PushManager.subscribe."""
    await _get_config_by_slug(slug)
    from services.web_push import get_vapid_public_key

    return {"public_key": get_vapid_public_key()}


@router.post("/{slug}/push/subscribe")
async def subscribe_store_push(slug: str, body: dict) -> Any:
    """Save a browser push subscription for this store's PWA."""
    from models.store_push_subscription import StorePushSubscription, PushSubscriptionKeys

    config = await _get_config_by_slug(slug)
    endpoint = (body.get("endpoint") or "").strip()
    keys = body.get("keys") or {}
    p256dh = (keys.get("p256dh") or "").strip()
    auth = (keys.get("auth") or "").strip()
    if not endpoint or not p256dh or not auth:
        raise HTTPException(status_code=400, detail="Invalid push subscription")

    existing = await StorePushSubscription.find_one({"endpoint": endpoint})
    if existing:
        existing.organization_id = str(config.organization_id)
        existing.store_slug = slug
        existing.keys = PushSubscriptionKeys(p256dh=p256dh, auth=auth)
        existing.user_agent = body.get("user_agent")
        existing.updated_at = datetime.utcnow()
        await existing.save()
        return {"ok": True, "id": str(existing.id)}

    sub = StorePushSubscription(
        organization_id=str(config.organization_id),
        store_slug=slug,
        endpoint=endpoint,
        keys=PushSubscriptionKeys(p256dh=p256dh, auth=auth),
        user_agent=body.get("user_agent"),
    )
    await sub.create()
    return {"ok": True, "id": str(sub.id)}


@router.post("/{slug}/push/test")
async def test_store_push(slug: str) -> Any:
    """Send a test notification to all subscribers of this store (public, for setup)."""
    config = await _get_config_by_slug(slug)
    from services.web_push import send_store_push

    result = await send_store_push(
        organization_id=str(config.organization_id),
        title=f"Hello from {config.store_name or 'our store'}",
        body="Notifications are working. You'll get alerts for new arrivals and promotions.",
        url=f"/store/{slug}",
        tag="push-test",
        icon=f"/store/{slug}/icon",
        badge="/icons/badge-96.png",
        image=(config.logo_url or config.banner_url or config.favicon_url),
    )
    return {"ok": True, **result}


@router.delete("/{slug}/push/unsubscribe")
async def unsubscribe_store_push(slug: str, endpoint: str = Query(...)) -> Any:
    """Remove a push subscription."""
    await _get_config_by_slug(slug)
    from models.store_push_subscription import StorePushSubscription

    sub = await StorePushSubscription.find_one({"endpoint": endpoint, "store_slug": slug})
    if sub:
        await sub.delete()
    return {"ok": True}
