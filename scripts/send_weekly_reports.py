"""
Script to send weekly inventory reports to all users who have enabled them.
Run this script weekly via cron or manually.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import List

# Add the parent directory to sys.path to import from models, core, etc.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from db.mongodb import init_db
from models.user import User
from models.organization import Organization
from models.sale import Sale
from models.purchase_order import PurchaseOrder
from models.stock_movement import StockMovement
from services.notification import send_weekly_report


async def gather_report_data(organization_id: str):
    """Gather inventory stats for the last 7 days for an organization"""
    last_week = datetime.utcnow() - timedelta(days=7)
    
    # Total Sales Revenue
    sales = await Sale.find({
        "organization_id": organization_id,
        "status": "completed",
        "created_at": {"$gte": last_week}
    }).to_list()
    total_sales = sum(s.total for s in sales)
    
    # Orders Count
    orders_count = await PurchaseOrder.find({
        "organization_id": organization_id,
        "status": "received",
        "received_date": {"$gte": last_week.date()}
    }).count()
    
    # Stock Movements
    movements_count = await StockMovement.find({
        "organization_id": organization_id,
        "created_at": {"$gte": last_week}
    }).count()
    
    # Low Stock Items count (Current snapshot)
    from models.product import Product
    low_stock_count = await Product.find({
        "organization_id": organization_id,
        "status": "low_stock"
    }).count()
    
    return {
        "total_sales": total_sales,
        "orders_count": orders_count,
        "low_stock_count": low_stock_count,
        "movements_count": movements_count
    }


async def main():
    print(f"[{datetime.utcnow()}] Starting weekly reports distribution...")
    await init_db()
    
    # Find all users who want weekly reports
    users = await User.find({
        "preferences.notifications.weekly_reports": True,
        "is_active": True
    }).to_list()
    
    print(f"Found {len(users)} users with weekly reports enabled.")
    
    processed_orgs = {}
    
    for user in users:
        if not user.organization_id:
            continue
            
        # Cache org data to avoid redundant queries
        if user.organization_id not in processed_orgs:
            print(f"Gathering data for organization: {user.organization_id}")
            processed_orgs[user.organization_id] = await gather_report_data(user.organization_id)
            
        report_data = processed_orgs[user.organization_id]
        
        try:
            print(f"Sending weekly report to: {user.email}")
            await send_weekly_report(user, report_data)
        except Exception as e:
            print(f"Failed to send report to {user.email}: {e}")

    print(f"[{datetime.utcnow()}] Weekly reports distribution completed.")


if __name__ == "__main__":
    asyncio.run(main())
