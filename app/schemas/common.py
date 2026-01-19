"""Common schemas for pagination and responses"""
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel

T = TypeVar('T')


class PaginationParams(BaseModel):
    skip: int = 0
    limit: int = 100


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    skip: int
    limit: int
    has_more: bool


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
