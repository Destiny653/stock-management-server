"""Bulk Import & Export API Endpoints - Products and Inventory Data"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from typing import List, Dict, Any
import csv
import io
from datetime import datetime
from models.user import User
from models.product import Product, ProductStatus, ValuationMethod
from api.deps import get_current_user
from services.audit_service import log_audit_event

router = APIRouter()


@router.post("/products/import-csv")
async def import_products_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Import products from CSV file with header validation and duplicate checks."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a valid .csv format")

    org_id = str(current_user.organization_id)
    content = await file.read()
    decoded = content.decode('utf-8-sig')
    csv_reader = csv.DictReader(io.StringIO(decoded))

    created_count = 0
    updated_count = 0
    errors = []

    for row_idx, row in enumerate(csv_reader, start=2):
        name = row.get("Product") or row.get("name") or row.get("Product Name")
        if not name:
            errors.append(f"Row {row_idx}: Missing product name")
            continue

        sku = row.get("SKU") or row.get("sku")
        barcode = row.get("Barcode") or row.get("barcode")
        category = row.get("Category") or row.get("category") or "Other"
        brand = row.get("Brand") or row.get("brand")
        cost_price = float(row.get("Cost") or row.get("cost_price") or 0.0)
        selling_price = float(row.get("Price") or row.get("selling_price") or 0.0)
        stock = int(row.get("Stock") or row.get("stock") or 0)
        uom = row.get("UOM") or row.get("unit_of_measure") or "pcs"

        existing = None
        if sku:
            existing = await Product.find_one(Product.organization_id == org_id, Product.sku == sku)
        if not existing and barcode:
            existing = await Product.find_one(Product.organization_id == org_id, Product.barcode == barcode)

        if existing:
            existing.name = name
            existing.category = category
            existing.brand = brand or existing.brand
            existing.cost_price = cost_price
            existing.selling_price = selling_price
            existing.total_stock = stock
            existing.unit_of_measure = uom
            existing.updated_at = datetime.utcnow()
            await existing.save()
            updated_count += 1
        else:
            new_prod = Product(
                organization_id=org_id,
                name=name,
                sku=sku,
                barcode=barcode,
                category=category,
                brand=brand,
                cost_price=cost_price,
                selling_price=selling_price,
                total_stock=stock,
                unit_of_measure=uom,
                status=ProductStatus.ACTIVE if stock > 0 else ProductStatus.OUT_OF_STOCK,
            )
            await new_prod.insert()
            created_count += 1

    await log_audit_event(
        organization_id=org_id,
        action="product.import_csv",
        resource_type="Product",
        user_id=str(current_user.id),
        user_name=current_user.username,
        reason=f"Imported CSV: {created_count} created, {updated_count} updated",
    )

    return {
        "status": "success",
        "created_count": created_count,
        "updated_count": updated_count,
        "errors": errors,
    }


@router.get("/products/export-csv")
async def export_products_csv(
    current_user: User = Depends(get_current_user),
):
    """Export all organization products to a CSV file."""
    org_id = str(current_user.organization_id)
    products = await Product.find(Product.organization_id == org_id).to_list()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "SKU", "Barcode", "Product Name", "Category", "Brand",
        "Cost Price", "Selling Price", "Stock", "UOM", "Status", "Valuation Method"
    ])

    for p in products:
        writer.writerow([
            p.sku or "",
            p.barcode or "",
            p.name,
            p.category,
            p.brand or "",
            p.cost_price,
            p.selling_price,
            p.total_stock,
            p.unit_of_measure,
            p.status,
            p.valuation_method
        ])

    csv_data = output.getvalue()
    filename = f"products_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
