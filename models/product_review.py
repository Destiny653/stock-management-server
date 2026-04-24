"""ProductReview model – customer reviews and ratings for storefront products"""
from typing import Optional
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field


class ProductReview(Document):
    organization_id: Indexed(str)
    product_id: Indexed(str)
    reviewer_name: str
    reviewer_email: Optional[str] = None
    rating: int = Field(ge=1, le=5)  # 1-5 stars
    title: Optional[str] = None
    comment: Optional[str] = None
    is_approved: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "product_reviews"
