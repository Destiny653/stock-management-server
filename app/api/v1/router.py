"""API v1 Router - All endpoints"""
from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    organizations,
    users,
    products,
    suppliers,
    vendors,
    warehouses,
    purchase_orders,
    sales,
    stock_movements,
    alerts,
    vendor_payments,
    locations,
    search,
    notifications,
)

api_router = APIRouter()

# Authentication
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Organizations (Admin)
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])

# Users
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# Products
api_router.include_router(products.router, prefix="/products", tags=["Products"])

# Suppliers
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["Suppliers"])

# Vendors
api_router.include_router(vendors.router, prefix="/vendors", tags=["Vendors"])

# Warehouses
api_router.include_router(warehouses.router, prefix="/warehouses", tags=["Warehouses"])

# Purchase Orders
api_router.include_router(purchase_orders.router, prefix="/purchase-orders", tags=["Purchase Orders"])

# Sales
api_router.include_router(sales.router, prefix="/sales", tags=["Sales"])

# Stock Movements
api_router.include_router(stock_movements.router, prefix="/stock-movements", tags=["Stock Movements"])

# Alerts
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])

# Vendor Payments
api_router.include_router(vendor_payments.router, prefix="/vendor-payments", tags=["Vendor Payments"])

# Locations
api_router.include_router(locations.router, prefix="/locations", tags=["Locations"])

# Search
api_router.include_router(search.router, prefix="/search", tags=["Global Search"])

# Notifications
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
