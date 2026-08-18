"""Finance Service - Financial ledger metrics calculation (Revenue, COGS, Profit, Payables, Receivables)"""
from typing import Dict, Any, Optional
from datetime import datetime, date
from models.sale import Sale, SaleStatus, PaymentStatus
from models.product import Product
from models.supplier import Supplier
from models.customer import Customer
from models.purchase_order import PurchaseOrder, POStatus


async def get_financial_summary(
    organization_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """Calculate financial metrics including total revenue, COGS, gross profit, payables, and receivables."""
    
    # 1. Fetch completed sales
    sales_query = Sale.find(
        Sale.organization_id == organization_id,
        Sale.status == SaleStatus.COMPLETED
    )
    all_sales = await sales_query.to_list()
    
    # Filter by date if provided
    if start_date or end_date:
        filtered_sales = []
        for s in all_sales:
            sale_dt = s.created_at.date()
            if start_date and sale_dt < start_date:
                continue
            if end_date and sale_dt > end_date:
                continue
            filtered_sales.append(s)
        all_sales = filtered_sales

    total_revenue = sum(s.total for s in all_sales)
    total_cogs = sum(s.cogs_total for s in all_sales)
    gross_profit = total_revenue - total_cogs
    gross_margin_pct = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    # 2. Inventory Asset Valuation
    products = await Product.find(Product.organization_id == organization_id).to_list()
    inventory_asset_valuation = sum(p.total_stock * p.cost_price for p in products)

    # 3. Accounts Payable (Suppliers owed money for purchase orders or credit)
    suppliers = await Supplier.find(Supplier.organization_id == organization_id).to_list()
    total_accounts_payable = sum(sup.outstanding_balance for sup in suppliers)

    # 4. Accounts Receivable (Customers owing money on credit sales)
    customers = await Customer.find(Customer.organization_id == organization_id).to_list()
    total_accounts_receivable = sum(c.current_balance for c in customers)

    return {
        "organization_id": organization_id,
        "total_revenue": round(total_revenue, 2),
        "total_cogs": round(total_cogs, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_margin_pct": round(gross_margin_pct, 2),
        "inventory_asset_valuation": round(inventory_asset_valuation, 2),
        "total_accounts_payable": round(total_accounts_payable, 2),
        "total_accounts_receivable": round(total_accounts_receivable, 2),
        "sales_count": len(all_sales),
    }
