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
    default_hero_image: Optional[str] = None
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
            "default_hero_image": None,
            "allowed_payment_methods": [
                "mtn",
                "orange",
                "stripe",
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
    if settings_in.default_hero_image is not None:
        settings.default_hero_image = settings_in.default_hero_image
    if settings_in.allowed_payment_methods is not None:
        settings.allowed_payment_methods = settings_in.allowed_payment_methods
        
    await settings.save()
    return settings

from fastapi import UploadFile, File
import uuid
import os
from core.uploads import upload_to_gridfs

@router.post("/upload-default-hero")
async def upload_default_hero(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Upload default platform hero banner (Platform Staff only)."""
    if current_user.user_type != "platform-staff":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
        
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid file name")
        
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"default-hero-{uuid.uuid4()}{file_extension}"
    
    file_bytes = await file.read()
    url = await upload_to_gridfs(file_bytes, filename, bucket_name="storefront", content_type=file.content_type)
    
    # Save directly to platform settings as well
    settings = await PlatformSettings.find_one()
    if not settings:
        settings = PlatformSettings()
    
    # Optional: Delete old default hero image if it exists
    if settings.default_hero_image:
        try:
            from motor.motor_asyncio import AsyncIOMotorGridFSBucket
            from db.mongodb import db
            fs = AsyncIOMotorGridFSBucket(db, bucket_name="storefront")
            old_filename = settings.default_hero_image.split("/")[-1]
            cursor = fs.find({"filename": old_filename})
            file_docs = await cursor.to_list(length=1)
            if file_docs:
                await fs.delete(file_docs[0]["_id"])
        except Exception as e:
            print(f"Failed to delete old default hero: {e}")
            
    settings.default_hero_image = url
    await settings.save()
    
    return {"url": url}


from models.product import Product
from models.storefront_config import StorefrontConfig
from core.uploads import UPLOAD_ROOT
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from pathlib import Path

@router.post("/cleanup-images")
async def cleanup_orphaned_images(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Scan and delete all orphaned images in GridFS and local storage (Platform Staff only)."""
    if current_user.user_type != "platform-staff":
        raise HTTPException(status_code=403, detail="Not authorized")

    # 1. Gather all active files referenced in DB
    active_product_files = set()
    active_storefront_files = set()

    products = await Product.find_all().to_list()
    for p in products:
        if p.image_url:
            filename = p.image_url.split("/")[-1]
            active_product_files.add(filename)
        for v in p.variants:
            if v.image_url:
                filename = v.image_url.split("/")[-1]
                active_product_files.add(filename)

    configs = await StorefrontConfig.find_all().to_list()
    for c in configs:
        if c.logo_url:
            active_storefront_files.add(c.logo_url.split("/")[-1])
        if c.banner_url:
            active_storefront_files.add(c.banner_url.split("/")[-1])
        if c.hero_slides:
            for slide in c.hero_slides:
                if slide.image_url:
                    active_storefront_files.add(slide.image_url.split("/")[-1])

    settings = await PlatformSettings.find_one()
    if settings and settings.default_hero_image:
        active_storefront_files.add(settings.default_hero_image.split("/")[-1])

    deleted_count = 0
    from db.mongodb import db

    # 2. Cleanup GridFS
    if db is not None:
        for bucket, active_set in [("products", active_product_files), ("storefront", active_storefront_files)]:
            try:
                fs = AsyncIOMotorGridFSBucket(db, bucket_name=bucket)
                cursor = fs.find({})
                file_docs = await cursor.to_list(length=10000)
                for doc in file_docs:
                    filename = doc.get("filename")
                    if filename and filename not in active_set:
                        await fs.delete(doc["_id"])
                        deleted_count += 1
            except Exception as e:
                print(f"GridFS cleanup failed for {bucket}: {e}")

    # 3. Cleanup Local Filesystem
    for subdir, active_set in [("products", active_product_files), ("storefront", active_storefront_files)]:
        local_dir = UPLOAD_ROOT / subdir
        if local_dir.exists():
            try:
                for file_path in local_dir.iterdir():
                    if file_path.is_file():
                        if file_path.name not in active_set:
                            file_path.unlink()
                            deleted_count += 1
            except Exception as e:
                print(f"Local cleanup failed for {subdir}: {e}")

    return {
        "status": "success",
        "deleted_images_count": deleted_count,
        "message": f"Successfully cleaned up {deleted_count} orphaned images."
    }


