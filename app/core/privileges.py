from enum import Enum

class Privilege(str, Enum):
    # Product Management
    PRODUCTS_READ = "products:read"
    PRODUCTS_CREATE = "products:create"
    PRODUCTS_UPDATE = "products:update"
    PRODUCTS_DELETE = "products:delete"
    
    # Inventory & Stock
    STOCK_READ = "stock:read"
    STOCK_ADJUST = "stock:adjust"
    STOCK_TRANSFER = "stock:transfer"
    
    # Sales Management
    SALES_READ = "sales:read"
    SALES_CREATE = "sales:create"
    SALES_VOID = "sales:void"
    
    # Purchase Orders
    PO_READ = "po:read"
    PO_CREATE = "po:create"
    PO_APPROVE = "po:approve"
    PO_RECEIVE = "po:receive"
    
    # Supplier & Vendor Management
    SUPPLIERS_MANAGE = "suppliers:manage"
    VENDORS_MANAGE = "vendors:manage"
    
    # User & Organization Management
    USERS_MANAGE = "users:manage"
    ORG_SETTINGS = "org:settings"
    
    # Reports & Analytics
    REPORTS_VIEW = "reports:view"

# Helper for role-based default permissions
ROLE_PERMISSIONS = {
    "owner": [p.value for p in Privilege],
    "admin": [p.value for p in Privilege],
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
    "staff": [
        Privilege.PRODUCTS_READ.value,
        Privilege.STOCK_READ.value,
        Privilege.SALES_CREATE.value,
        Privilege.SALES_READ.value,
        Privilege.PO_READ.value,
    ],
    "vendor": [
        Privilege.PRODUCTS_READ.value,
        Privilege.STOCK_READ.value,
        Privilege.SALES_CREATE.value,
        Privilege.SALES_READ.value,
    ],
    "viewer": [
        Privilege.PRODUCTS_READ.value,
        Privilege.STOCK_READ.value,
        Privilege.SALES_READ.value,
        Privilege.REPORTS_VIEW.value,
    ]
}
