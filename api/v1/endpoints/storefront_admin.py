"""Storefront admin API – authenticated endpoints for org admins to manage their store"""
import os
import uuid
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query

from api import deps
from models.user import User
from models.storefront_config import StorefrontConfig, ThemeConfig, HeroSlide, SocialLinks
from models.product_review import ProductReview
from models.storefront_order import StorefrontOrder
from schemas.storefront_config import StorefrontConfigCreate, StorefrontConfigUpdate

router = APIRouter()


@router.get("/config")
async def get_storefront_config(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get own organization's storefront config."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization associated with user")

    config = await StorefrontConfig.find_one({"organization_id": org_id})
    if not config:
        return None
    return config


@router.put("/config")
async def update_storefront_config(
    config_in: StorefrontConfigUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Create or update storefront config for the user's organization."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization associated with user")

    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only admins/managers can manage storefront")

    config = await StorefrontConfig.find_one({"organization_id": org_id})

    if config:
        # Update existing
        update_data = config_in.model_dump(exclude_unset=True)

        # Handle nested theme update (merge, don't replace)
        if "theme" in update_data and update_data["theme"]:
            existing_theme = config.theme.model_dump() if config.theme else {}
            for k, v in update_data["theme"].items():
                if v is not None:
                    existing_theme[k] = v
            update_data["theme"] = existing_theme

        # Handle nested social_links update (merge)
        if "social_links" in update_data and update_data["social_links"]:
            existing_social = config.social_links.model_dump() if config.social_links else {}
            for k, v in update_data["social_links"].items():
                if v is not None:
                    existing_social[k] = v
            update_data["social_links"] = existing_social

        update_data["updated_at"] = datetime.utcnow()

        # Slug uniqueness check
        if "slug" in update_data and update_data["slug"] != config.slug:
            existing = await StorefrontConfig.find_one({"slug": update_data["slug"]})
            if existing:
                raise HTTPException(status_code=400, detail="This slug is already taken")

        await config.update({"$set": update_data})
        await config.save()
        return config
    else:
        # Create new
        data = config_in.model_dump(exclude_unset=True)
        if "slug" not in data or not data["slug"]:
            raise HTTPException(status_code=400, detail="slug is required for initial setup")
        if "store_name" not in data or not data["store_name"]:
            raise HTTPException(status_code=400, detail="store_name is required for initial setup")

        # Slug uniqueness check
        existing = await StorefrontConfig.find_one({"slug": data["slug"]})
        if existing:
            raise HTTPException(status_code=400, detail="This slug is already taken")

        # Build theme
        theme_data = data.pop("theme", None) or {}
        theme = ThemeConfig(**theme_data)

        # Build social links
        social_data = data.pop("social_links", None) or {}
        social = SocialLinks(**social_data)

        # Build hero slides
        hero_data = data.pop("hero_slides", [])
        hero_slides = [HeroSlide(**s) for s in hero_data]

        config = StorefrontConfig(
            organization_id=org_id,
            theme=theme,
            social_links=social,
            hero_slides=hero_slides,
            **data,
        )
        await config.create()
        return config


@router.post("/config/upload-image")
async def upload_storefront_image(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Upload a storefront image (hero, logo, banner)."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only admins/managers can upload images")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    upload_dir = "uploads/storefront"
    os.makedirs(upload_dir, exist_ok=True)

    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    return {"url": f"/uploads/storefront/{filename}"}


@router.get("/reviews")
async def list_reviews(
    is_approved: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """List all reviews for the organization (for moderation)."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization associated with user")

    query = {"organization_id": org_id}
    if is_approved is not None:
        query["is_approved"] = is_approved

    reviews = await ProductReview.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
    return reviews


@router.put("/reviews/{review_id}/approve")
async def approve_review(
    review_id: str,
    approve: bool = True,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Approve or reject a review."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization associated with user")

    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only admins/managers can moderate reviews")

    try:
        from beanie import PydanticObjectId
        obj_id = PydanticObjectId(review_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid review ID")

    review = await ProductReview.find_one({"_id": obj_id, "organization_id": org_id})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.is_approved = approve
    await review.save()

    return {"message": f"Review {'approved' if approve else 'rejected'}", "id": str(review.id)}


@router.delete("/reviews/{review_id}")
async def delete_review(
    review_id: str,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Delete a review."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization associated with user")

    try:
        from beanie import PydanticObjectId
        obj_id = PydanticObjectId(review_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid review ID")

    review = await ProductReview.find_one({"_id": obj_id, "organization_id": org_id})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    await review.delete()
    return {"message": "Review deleted"}


@router.get("/orders")
async def list_storefront_orders(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """List storefront orders for the organization."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization associated with user")

    query = {"organization_id": org_id}
    if status:
        query["status"] = status

    orders = await StorefrontOrder.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
    return orders


@router.put("/orders/{order_id}/status")
async def update_order_status(
    order_id: str,
    new_status: str = Query(..., pattern="^(pending|confirmed|processing|completed|cancelled)$"),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Update storefront order status."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization associated with user")

    try:
        from beanie import PydanticObjectId
        obj_id = PydanticObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order ID")

    order = await StorefrontOrder.find_one({"_id": obj_id, "organization_id": org_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = new_status
    order.updated_at = datetime.utcnow()
    await order.save()

    return {"message": f"Order status updated to {new_status}", "order_ref": order.order_ref}
