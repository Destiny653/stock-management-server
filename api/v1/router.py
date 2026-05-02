"""API v1 Router - All endpoints"""
from fastapi import APIRouter
from api.v1.endpoints import (
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
    organization_payments,
    locations,
    search,
    subscription_plans,
    categories,
    notifications,
    payunit_payments,
    storefront,
    storefront_admin,
    platform,
    stripe_webhooks,
)


api_router = APIRouter()

# Platform Settings
api_router.include_router(platform.router, prefix="/platform", tags=["Platform"])

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

# Organization Payments
api_router.include_router(organization_payments.router, prefix="/organization-payments", tags=["Organization Payments"])

# Locations
api_router.include_router(locations.router, prefix="/locations", tags=["Locations"])

# Search
api_router.include_router(search.router, prefix="/search", tags=["Global Search"])

# Notifications
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])

# Subscription Plans
api_router.include_router(subscription_plans.router, prefix="/subscription-plans", tags=["Subscription Plans"])

# Categories
api_router.include_router(categories.router, prefix="/categories", tags=["Categories"])

# PayUnit Payments
api_router.include_router(payunit_payments.router, prefix="/payments", tags=["PayUnit Payments"])

# Stripe Webhooks
api_router.include_router(stripe_webhooks.router, prefix="/stripe-webhooks", tags=["Stripe Webhooks"])

# Public Storefront

api_router.include_router(storefront.router, prefix="/storefront", tags=["Public Storefront"])

# Storefront Admin
api_router.include_router(storefront_admin.router, prefix="/storefront-admin", tags=["Storefront Admin"])
