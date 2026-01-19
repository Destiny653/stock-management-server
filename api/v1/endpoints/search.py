"""General Search Endpoints"""
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, Query
from api import deps
from models.user import User
from models.product import Product
from models.vendor import Vendor
from models.supplier import Supplier
from pydantic import BaseModel

router = APIRouter()

class SearchResult(BaseModel):
    id: str
    type: str  # 'product', 'vendor', 'supplier'
    title: str
    subtitle: Optional[str] = None
    status: Optional[str] = None
    url: Optional[str] = None

@router.get("/", response_model=List[SearchResult])
async def general_search(
    q: str = Query(..., min_length=1, description="Search query"),
    organization_id: Optional[str] = Query(None, description="Organization ID to filter by"),
    limit: int = 20,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    General search across Products, Vendors, and Suppliers.
    Multi-tenant aware - filters by organization_id if provided or if user is tied to one.
    """
    # Use user's organization_id if not explicitly provided, unless user is a super admin
    effective_org_id = organization_id or current_user.organization_id
    
    results = []
    search_regex = {"$regex": q, "$options": "i"}
    
    # 1. Search Products
    product_query = {
        "$or": [
            {"name": search_regex},
            {"category": search_regex},
            {"description": search_regex},
            {"variants.sku": search_regex}
        ]
    }
    if effective_org_id:
        product_query["organization_id"] = effective_org_id
        
    products = await Product.find(product_query).limit(limit).to_list()
    for p in products:
        results.append(SearchResult(
            id=str(p.id),
            type="product",
            title=p.name,
            subtitle=f"Category: {p.category.value if hasattr(p.category, 'value') else p.category}",
            status=p.status,
            url=f"/inventory/{p.id}"
        ))

    # 2. Search Vendors
    vendor_query = {
        "$or": [
            {"name": search_regex},
            {"store_name": search_regex},
            {"email": search_regex}
        ]
    }
    if effective_org_id:
        vendor_query["organization_id"] = effective_org_id
        
    vendors = await Vendor.find(vendor_query).limit(limit).to_list()
    for v in vendors:
        results.append(SearchResult(
            id=str(v.id),
            type="vendor",
            title=v.name,
            subtitle=f"Store: {v.store_name}",
            status=v.status,
            url=f"/vendors/{v.id}"
        ))

    # 3. Search Suppliers
    supplier_query = {
        "$or": [
            {"name": search_regex},
            {"contact_name": search_regex},
            {"email": search_regex}
        ]
    }
    if effective_org_id:
        supplier_query["organization_id"] = effective_org_id
        
    suppliers = await Supplier.find(supplier_query).limit(limit).to_list()
    for s in suppliers:
        results.append(SearchResult(
            id=str(s.id),
            type="supplier",
            title=s.name,
            subtitle=f"Contact: {s.contact_name}",
            status=s.status,
            url=f"/suppliers/{s.id}"
        ))

    # Sort results by relevance (simple sort for now: title matching query start first)
    results.sort(key=lambda x: not x.title.lower().startswith(q.lower()))
    
    return results[:limit]
