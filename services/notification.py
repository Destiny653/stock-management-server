"""Notification service for sending various types of notifications"""
from typing import List
from services.email import send_email
from models.user import User


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


async def send_password_reset_email(user: User, token: str):
    """Send password reset email with bilingual support (EN/FR)"""
    reset_url = f"http://localhost:3000/auth/reset-password?token={token}"
    
    # Simple bilingual content for password reset
    subject = "Reset your password / Réinitialisez votre mot de passe - StockFlow"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
                <h2 style="color: #0d9488; text-align: center;">StockFlow</h2>
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                
                <div style="margin-bottom: 30px;">
                    <p><strong>[English]</strong></p>
                    <p>Hi {user.full_name or user.username},</p>
                    <p>You requested to reset your password. Click the button below to continue:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}" style="background-color: #0d9488; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
                    </div>
                    <p>If you didn't request this, you can safely ignore this email. This link will expire in 1 hour.</p>
                </div>
                
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                
                <div>
                    <p><strong>[Français]</strong></p>
                    <p>Bonjour {user.full_name or user.username},</p>
                    <p>Vous avez demandé la réinitialisation de votre mot de passe. Cliquez sur le bouton ci-dessous pour continuer :</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}" style="background-color: #0d9488; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Réinitialiser le mot de passe</a>
                    </div>
                    <p>Si vous n'avez pas demandé cela, vous pouvez ignorer cet e-mail en toute sécurité. Ce lien expirera dans 1 heure.</p>
                </div>
                
                <p style="margin-top: 30px; font-size: 12px; color: #64748b; text-align: center;">
                    &copy; 2026 StockFlow. All rights reserved. / Tous droits réservés.
                </p>
            </div>
        </body>
    </html>
    """
    
    print(f"Attempting to send password reset email to: {user.email}")
    try:
        await send_email(
            email_to=[user.email],
            subject=subject,
            html_content=html_content
        )
        print(f"Successfully sent password reset email to: {user.email}")
    except Exception as e:
        print(f"Error in send_email: {e}")
        raise e
