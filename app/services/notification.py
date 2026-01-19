"""Notification service for sending various types of notifications"""
from typing import List
from app.services.email import send_email
from app.models.user import User


async def send_low_stock_alert(user: User, product_name: str, current_stock: int, reorder_point: int):
    """Send low stock alert notification"""
    if not user.preferences.notifications.low_stock_alerts:
        return
    
    if user.preferences.notifications.email:
        await send_email(
            email_to=[user.email],
            subject=f"Low Stock Alert: {product_name}",
            html_content=f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #dc2626;">⚠️ Low Stock Alert</h2>
                        <p>Hi {user.full_name or user.username},</p>
                        <p>The following product is running low on stock:</p>
                        <div style="background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; margin: 20px 0;">
                            <p style="margin: 0;"><strong>Product:</strong> {product_name}</p>
                            <p style="margin: 5px 0 0 0;"><strong>Current Stock:</strong> {current_stock} units</p>
                            <p style="margin: 5px 0 0 0;"><strong>Reorder Point:</strong> {reorder_point} units</p>
                        </div>
                        <p>Please consider restocking this item soon to avoid stockouts.</p>
                        <p style="margin-top: 30px;">Best regards,<br>The StockFlow Team</p>
                    </div>
                </body>
            </html>
            """
        )


async def send_order_update(user: User, order_number: str, status: str):
    """Send order update notification"""
    if not user.preferences.notifications.order_updates:
        return
    
    if user.preferences.notifications.email:
        await send_email(
            email_to=[user.email],
            subject=f"Order Update: {order_number}",
            html_content=f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #0d9488;">📦 Order Update</h2>
                        <p>Hi {user.full_name or user.username},</p>
                        <p>Your order has been updated:</p>
                        <div style="background-color: #f0fdfa; border-left: 4px solid #0d9488; padding: 15px; margin: 20px 0;">
                            <p style="margin: 0;"><strong>Order Number:</strong> {order_number}</p>
                            <p style="margin: 5px 0 0 0;"><strong>New Status:</strong> {status.upper()}</p>
                        </div>
                        <p>You can view the full order details in your StockFlow dashboard.</p>
                        <p style="margin-top: 30px;">Best regards,<br>The StockFlow Team</p>
                    </div>
                </body>
            </html>
            """
        )


async def send_weekly_report(user: User, report_data: dict):
    """Send weekly report notification"""
    if not user.preferences.notifications.weekly_reports:
        return
    
    if user.preferences.notifications.email:
        await send_email(
            email_to=[user.email],
            subject="Your Weekly StockFlow Report",
            html_content=f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #0d9488;">📊 Weekly Report</h2>
                        <p>Hi {user.full_name or user.username},</p>
                        <p>Here's your weekly inventory summary:</p>
                        <div style="background-color: #f8fafc; border-radius: 8px; padding: 20px; margin: 20px 0;">
                            <p style="margin: 0;"><strong>Total Sales:</strong> ${report_data.get('total_sales', 0):,.2f}</p>
                            <p style="margin: 10px 0 0 0;"><strong>Orders Processed:</strong> {report_data.get('orders_count', 0)}</p>
                            <p style="margin: 10px 0 0 0;"><strong>Low Stock Items:</strong> {report_data.get('low_stock_count', 0)}</p>
                            <p style="margin: 10px 0 0 0;"><strong>Stock Movements:</strong> {report_data.get('movements_count', 0)}</p>
                        </div>
                        <p>Keep up the great work managing your inventory!</p>
                        <p style="margin-top: 30px;">Best regards,<br>The StockFlow Team</p>
                    </div>
                </body>
            </html>
            """
        )


async def send_push_notification_test(user: User):
    """Send a test notification when push notifications are enabled"""
    await send_email(
        email_to=[user.email],
        subject="Push Notifications Enabled - StockFlow",
        html_content=f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #0d9488;">🔔 Push Notifications Enabled</h2>
                    <p>Hi {user.full_name or user.username},</p>
                    <p>You have successfully enabled push notifications for your StockFlow account.</p>
                    <p>You will now receive real-time updates about:</p>
                    <ul>
                        <li>Low stock alerts</li>
                        <li>Order updates</li>
                        <li>Weekly reports</li>
                        <li>And more...</li>
                    </ul>
                    <p>You can manage your notification preferences anytime from your profile settings.</p>
                    <p style="margin-top: 30px;">Best regards,<br>The StockFlow Team</p>
                </div>
            </body>
        </html>
        """
    )
