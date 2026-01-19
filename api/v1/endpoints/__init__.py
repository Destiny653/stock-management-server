"""Endpoints package"""
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
)

__all__ = [
    "auth",
    "organizations",
    "users",
    "products",
    "suppliers",
    "vendors",
    "warehouses",
    "purchase_orders",
    "sales",
    "stock_movements",
    "alerts",
    "vendor_payments",
]
