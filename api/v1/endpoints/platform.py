from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException
from models.platform_settings import PlatformSettings
from models.user import User
from api.deps import get_current_active_user
from pydantic import BaseModel

router = APIRouter()

class PlatformSettingsUpdate(BaseModel):
    support_whatsapp: Optional[str] = None
    support_email: Optional[str] = None
    platform_name: Optional[str] = None
    default_currency: Optional[str] = None
    allowed_payment_methods: Optional[List[str]] = None

@router.get("/settings")
async def get_platform_settings() -> Any:
    """Publicly get platform settings."""
    settings = await PlatformSettings.find_one()
    if not settings:
        # Return default if not initialized
        return {
            "support_whatsapp": "+237670000000",
            "support_email": "support@stockflow.com",
            "platform_name": "StockFlow",
            "default_currency": "CFAF",
            "allowed_payment_methods": [
                "momo",
                "orange-money",
                "visa",
                "mastercard",
                "apple-pay",
                "google-pay",
                "paypal",
            ],
        }
    return settings

@router.put("/settings")
async def update_platform_settings(
    settings_in: PlatformSettingsUpdate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Update platform settings (Platform Staff only)."""
    if current_user.user_type != "platform-staff":
        raise HTTPException(status_code=403, detail="Not authorized to update platform settings")
    
    settings = await PlatformSettings.find_one()
    if not settings:
        settings = PlatformSettings()
    
    if settings_in.support_whatsapp is not None:
        settings.support_whatsapp = settings_in.support_whatsapp
    if settings_in.support_email is not None:
        settings.support_email = settings_in.support_email
    if settings_in.platform_name is not None:
        settings.platform_name = settings_in.platform_name
    if settings_in.default_currency is not None:
        settings.default_currency = settings_in.default_currency
    if settings_in.allowed_payment_methods is not None:
        settings.allowed_payment_methods = settings_in.allowed_payment_methods
        
    await settings.save()
    return settings
