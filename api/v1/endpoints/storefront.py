"""Public storefront API – no authentication required"""
import uuid
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from beanie import PydanticObjectId

from models.storefront_config import StorefrontConfig
from models.product import Product
from models.product_review import ProductReview
from models.storefront_order import StorefrontOrder, StorefrontOrderItem
from models.category import Category
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
    return config


@router.get("/{slug}/products")
async def get_storefront_products(
    slug: str,
    search: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort: Optional[str] = Query(default="newest", pattern="^(newest|price_asc|price_desc|name_asc|name_desc|rating|best_selling|featured)$"),
    skip: int = 0,
    limit: int = 24,
) -> Any:
    """List products for a storefront with filtering & sorting (public)."""
    config = await _get_config_by_slug(slug)
    org_id = config.organization_id

    query: dict = {"organization_id": org_id, "status": {"$ne": "discontinued"}}

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"variants.sku": {"$regex": search, "$options": "i"}},
        ]

    if category:
        query["category"] = category

    products = await Product.find(query).skip(skip).limit(limit).to_list()

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

    # Sorting
    if sort == "price_asc":
        products.sort(key=lambda p: min((v.unit_price for v in p.variants), default=0))
    elif sort == "price_desc":
        products.sort(key=lambda p: min((v.unit_price for v in p.variants), default=0), reverse=True)
    elif sort == "name_asc":
        products.sort(key=lambda p: p.name.lower())
    elif sort == "name_desc":
        products.sort(key=lambda p: p.name.lower(), reverse=True)
    elif sort == "newest":
        products.sort(key=lambda p: p.created_at, reverse=True)
    elif sort == "featured":
        # Prioritize featured products
        featured_ids = config.featured_product_ids or []
        products.sort(key=lambda p: (0 if str(p.id) in featured_ids else 1, p.created_at), reverse=False)
    elif sort == "best_selling":
        # Proxy: sort by a mix of rating and review count (we don't have orders count on product easily)
        # We'll calculate it on the fly below or just use a placeholder
        pass # Will handle after computing fields

    # Build response with computed fields
    result = []
    for p in products:
        total_stock = sum(v.stock for v in p.variants)
        lowest_price = min((v.unit_price for v in p.variants), default=0) if p.variants else 0
        reviews = await ProductReview.find({"product_id": str(p.id), "is_approved": True}).to_list()
        avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0
        review_count = len(reviews)

        result.append({
            "id": str(p.id),
            "name": p.name,
            "category": p.category,
            "description": p.description,
            "image_url": p.image_url,
            "status": p.status,
            "variants": [v.model_dump() for v in p.variants],
            "total_stock": total_stock,
            "lowest_price": lowest_price,
            "avg_rating": avg_rating,
            "review_count": review_count,
            "created_at": p.created_at.isoformat(),
        })

    if sort == "best_selling":
        result.sort(key=lambda x: (x["avg_rating"], x["review_count"]), reverse=True)

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

    return {
        "id": str(product.id),
        "name": product.name,
        "category": product.category,
        "description": product.description,
        "image_url": product.image_url,
        "status": product.status,
        "variants": [v.model_dump() for v in product.variants],
        "total_stock": total_stock,
        "lowest_price": min((v.unit_price for v in product.variants), default=0),
        "avg_rating": avg_rating,
        "review_count": len(reviews),
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

    result = []
    for cat in categories:
        # Count products in category
        count = await Product.find({
            "organization_id": config.organization_id,
            "category": cat.name,
            "status": {"$ne": "discontinued"},
        }).count()
        result.append({
            "id": str(cat.id),
            "name": cat.name,
            "description": cat.description,
            "color": cat.color,
            "icon": cat.icon,
            "product_count": count,
        })

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
        # Stripe integration
        try:
            # Note: amount for Stripe must be in cents/units. 
            # For XAF (no decimals), int(total) is correct if total is in XAF.
            # If USD, it should be int(total * 100).
            # We assume XAF for now as it's Cameroon context, but let's be safe.
            currency = config.currency.lower() or "xaf"
            stripe_amount = amount_int
            if currency in ["usd", "eur", "gbp"]:
                stripe_amount = int(total * 100)
            
            stripe_res = StripeService.create_payment_intent(
                amount=stripe_amount,
                currency=currency,
                order_id=order_ref,
                customer_email=order_in.customer_email
            )
            stripe_client_secret = stripe_res["client_secret"]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Stripe setup failed: {str(e)}")

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

