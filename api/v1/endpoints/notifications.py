"""Notification endpoints for testing and managing notifications"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from api import deps
from models.user import User
from services.notification import (
    send_low_stock_alert,
    send_order_update,
    send_weekly_report,
    send_push_notification_test
)

router = APIRouter()


@router.post("/test/push-notification")
async def test_push_notification(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Send a test push notification email to the current user
    """
    try:
        await send_push_notification_test(current_user)
        return {"message": "Test notification sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")


@router.post("/test/low-stock-alert")
async def test_low_stock_alert(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Send a test low stock alert email to the current user
    """
    try:
        await send_low_stock_alert(
            user=current_user,
            product_name="Test Product",
            current_stock=5,
            reorder_point=10
        )
        return {"message": "Test low stock alert sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")


@router.post("/test/order-update")
async def test_order_update(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Send a test order update email to the current user
    """
    try:
        await send_order_update(
            user=current_user,
            order_number="PO-2024-001",
            status="shipped"
        )
        return {"message": "Test order update sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")


@router.post("/test/weekly-report")
async def test_weekly_report(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Send a test weekly report email to the current user
    """
    try:
        await send_weekly_report(
            user=current_user,
            report_data={
                "total_sales": 15420.50,
                "orders_count": 42,
                "low_stock_count": 3,
                "movements_count": 127
            }
        )
        return {"message": "Test weekly report sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")
