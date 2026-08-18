"""Barcode API Endpoints - Instant barcode scanner lookup & label generator"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import Optional
from models.user import User
from models.product import Product
from api.deps import get_current_user
from services.barcode_service import generate_barcode_svg, generate_random_barcode

router = APIRouter()


@router.get("/lookup")
async def lookup_barcode(
    code: str = Query(..., description="Barcode string scanned"),
    current_user: User = Depends(get_current_user),
):
    """Scan or lookup a barcode (EAN-13, SKU, or custom code) and return product, variant & stock details."""
    org_id = str(current_user.organization_id)
    
    # 1. Direct barcode match on main product
    product = await Product.find_one(
        Product.organization_id == org_id,
        Product.barcode == code
    )
    
    # 2. SKU match on main product
    if not product:
        product = await Product.find_one(
            Product.organization_id == org_id,
            Product.sku == code
        )
        
    # 3. Check variants if not matched
    matched_variant = None
    if not product:
        all_products = await Product.find(Product.organization_id == org_id).to_list()
        for p in all_products:
            for v in p.variants:
                if v.barcode == code or v.sku == code:
                    product = p
                    matched_variant = v
                    break
            if product:
                break
                
    if not product:
        raise HTTPException(status_code=404, detail=f"No product found matching barcode or SKU '{code}'")

    return {
        "matched_code": code,
        "product_id": str(product.id),
        "name": product.name,
        "sku": matched_variant.sku if matched_variant else product.sku,
        "barcode": matched_variant.barcode if matched_variant else product.barcode,
        "category": product.category,
        "brand": product.brand,
        "unit_of_measure": product.unit_of_measure,
        "cost_price": matched_variant.cost_price if matched_variant else product.cost_price,
        "selling_price": matched_variant.unit_price if matched_variant else product.selling_price,
        "tax_rate": product.tax_rate,
        "available_stock": matched_variant.stock if matched_variant else product.total_stock,
        "reserved_stock": product.reserved_stock,
        "damaged_stock": product.damaged_stock,
        "status": product.status,
        "image_url": matched_variant.image_url if matched_variant else product.image_url,
        "variant": matched_variant,
        "warehouse_stocks": product.warehouse_stocks
    }


@router.get("/generate")
async def generate_barcode(
    code: Optional[str] = Query(None, description="Optional custom barcode string"),
    current_user: User = Depends(get_current_user),
):
    """Generate a printable barcode SVG string and code."""
    barcode_string = code if code else generate_random_barcode()
    svg_data = generate_barcode_svg(barcode_string)
    
    return {
        "code": barcode_string,
        "svg": svg_data
    }


@router.get("/render/{code}.svg")
async def render_barcode_svg(code: str):
    """Return raw SVG image for rendering in print labels or web components."""
    svg_data = generate_barcode_svg(code)
    return Response(content=svg_data, media_type="image/svg+xml")
