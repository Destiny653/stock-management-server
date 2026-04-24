"""Product review schemas"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from beanie import PydanticObjectId


class ReviewCreate(BaseModel):
    reviewer_name: str = Field(min_length=2, max_length=100)
    reviewer_email: Optional[str] = None
    rating: int = Field(ge=1, le=5)
    title: Optional[str] = Field(default=None, max_length=200)
    comment: Optional[str] = Field(default=None, max_length=2000)


class ReviewResponse(BaseModel):
    id: PydanticObjectId
    organization_id: str
    product_id: str
    reviewer_name: str
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None
    is_approved: bool = False
    created_at: datetime

    class Config:
        from_attributes = True
