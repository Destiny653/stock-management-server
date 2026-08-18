from enum import Enum

class Privilege(str, Enum):
    # Product Management
    PRODUCTS_READ = "products:read"
    PRODUCTS_CREATE = "products:create"
    PRODUCTS_UPDATE = "products:update"
    PRODUCTS_DELETE = "products:delete"
    PRODUCTS_PRICE_CHANGE = "products:price_change"
    
    # Inventory & Stock Operations
    STOCK_READ = "stock:read"
    STOCK_ADJUST = "stock:adjust"
    STOCK_TRANSFER = "stock:transfer"
    STOCK_COUNT = "stock:count"
    
    # Sales & POS Management
    SALES_READ = "sales:read"
    SALES_CREATE = "sales:create"
    SALES_VOID = "sales:void"
    SALES_DISCOUNT = "sales:discount"
    CUSTOMERS_MANAGE = "customers:manage"
    
    # Purchase Orders & Procurement
    PO_READ = "po:read"
    PO_CREATE = "po:create"
    PO_APPROVE = "po:approve"
    PO_RECEIVE = "po:receive"
    
    # Supplier & Vendor Management
    SUPPLIERS_MANAGE = "suppliers:manage"
    VENDORS_MANAGE = "vendors:manage"
    
    # Financial Accounting & Audit
    FINANCE_VIEW = "finance:view"
    AUDIT_VIEW = "audit:view"
    
    # User & Organization Management
    USERS_MANAGE = "users:manage"
    ORG_SETTINGS = "org:settings"
    
    # Reports & Analytics
    REPORTS_VIEW = "reports:view"

# Helper for role-based default permissions
ROLE_PERMISSIONS = {
    "admin": [p.value for p in Privilege],
    "administrator": [p.value for p in Privilege],
    "inventory_manager": [
        Privilege.PRODUCTS_READ.value,
        Privilege.PRODUCTS_CREATE.value,
        Privilege.PRODUCTS_UPDATE.value,
        Privilege.PRODUCTS_DELETE.value,
        Privilege.PRODUCTS_PRICE_CHANGE.value,
        Privilege.STOCK_READ.value,
        Privilege.STOCK_ADJUST.value,
        Privilege.STOCK_TRANSFER.value,
        Privilege.STOCK_COUNT.value,
        Privilege.REPORTS_VIEW.value,
    ],
    "procurement_officer": [
        Privilege.PO_READ.value,
        Privilege.PO_CREATE.value,
        Privilege.PO_APPROVE.value,
        Privilege.PO_RECEIVE.value,
        Privilege.SUPPLIERS_MANAGE.value,
        Privilege.VENDORS_MANAGE.value,
        Privilege.PRODUCTS_READ.value,
    ],
    "store_manager": [
        Privilege.PRODUCTS_READ.value,
        Privilege.STOCK_READ.value,
        Privilege.STOCK_TRANSFER.value,
        Privilege.SALES_READ.value,
        Privilege.SALES_CREATE.value,
        Privilege.SALES_VOID.value,
        Privilege.SALES_DISCOUNT.value,
        Privilege.CUSTOMERS_MANAGE.value,
        Privilege.REPORTS_VIEW.value,
    ],
    "salesperson": [
        Privilege.PRODUCTS_READ.value,
        Privilege.STOCK_READ.value,
        Privilege.SALES_READ.value,
        Privilege.SALES_CREATE.value,
        Privilege.SALES_DISCOUNT.value,
        Privilege.CUSTOMERS_MANAGE.value,
    ],
    "auditor": [
        Privilege.PRODUCTS_READ.value,
        Privilege.STOCK_READ.value,
        Privilege.SALES_READ.value,
        Privilege.PO_READ.value,
        Privilege.FINANCE_VIEW.value,
        Privilege.AUDIT_VIEW.value,
        Privilege.REPORTS_VIEW.value,
    ],
    "manager": [
        Privilege.PRODUCTS_READ.value,
        Privilege.PRODUCTS_CREATE.value,
        Privilege.PRODUCTS_UPDATE.value,
        Privilege.PRODUCTS_DELETE.value,
        Privilege.STOCK_READ.value,
        Privilege.STOCK_ADJUST.value,
        Privilege.STOCK_TRANSFER.value,
        Privilege.SALES_READ.value,
        Privilege.SALES_CREATE.value,
        Privilege.SALES_VOID.value,
        Privilege.PO_READ.value,
        Privilege.PO_CREATE.value,
        Privilege.PO_RECEIVE.value,
        Privilege.SUPPLIERS_MANAGE.value,
        Privilege.VENDORS_MANAGE.value,
        Privilege.USERS_MANAGE.value,
        Privilege.REPORTS_VIEW.value,
    ],
    "vendor": [
        Privilege.PRODUCTS_READ.value,
        Privilege.STOCK_READ.value,
        Privilege.SALES_CREATE.value,
        Privilege.SALES_READ.value,
    ],
    "user": [
        Privilege.PRODUCTS_READ.value,
        Privilege.STOCK_READ.value,
        Privilege.SALES_CREATE.value,
        Privilege.SALES_READ.value,
        Privilege.PO_READ.value,
    ],
}
