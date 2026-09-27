"""Normalize uploaded images — accept HEIC/HEIF and convert to web-safe JPEG."""
from __future__ import annotations

import io
import os
import uuid
from typing import Optional, Tuple

from fastapi import HTTPException

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".heic",
    ".heif",
    ".avif",
}

HEIC_EXTENSIONS = {".heic", ".heif"}
HEIC_CONTENT_TYPES = {
    "image/heic",
    "image/heif",
    "image/heic-sequence",
    "image/heif-sequence",
}


def _ext(filename: Optional[str]) -> str:
    return os.path.splitext(filename or "")[1].lower()


def is_allowed_image_upload(filename: Optional[str], content_type: Optional[str]) -> bool:
    """HEIC often arrives as application/octet-stream — allow by extension too."""
    ext = _ext(filename)
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return True
    ct = (content_type or "").lower().strip()
    if ct.startswith("image/"):
        return True
    if ct in HEIC_CONTENT_TYPES:
        return True
    return False


def is_heic_upload(filename: Optional[str], content_type: Optional[str]) -> bool:
    ext = _ext(filename)
    ct = (content_type or "").lower().strip()
    return ext in HEIC_EXTENSIONS or ct in HEIC_CONTENT_TYPES


def convert_heic_to_jpeg(file_bytes: bytes) -> bytes:
    """Convert HEIC/HEIF bytes to JPEG for browser display."""
    try:
        from pillow_heif import register_heif_opener
        from PIL import Image

        register_heif_opener()
        with Image.open(io.BytesIO(file_bytes)) as img:
            rgb = img.convert("RGB")
            out = io.BytesIO()
            rgb.save(out, format="JPEG", quality=90, optimize=True)
            return out.getvalue()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not process HEIC/HEIF image. Please convert to JPG/PNG or try again. ({exc})",
        ) from exc


def prepare_image_upload(
    file_bytes: bytes,
    filename: Optional[str],
    content_type: Optional[str],
) -> Tuple[bytes, str, str]:
    """
    Validate + normalize an uploaded image.
    Returns (bytes, filename, content_type). HEIC/HEIF → JPEG.
    """
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid file name")

    if not is_allowed_image_upload(filename, content_type):
        raise HTTPException(
            status_code=400,
            detail="File must be an image (JPG, PNG, WEBP, GIF, HEIC, HEIF)",
        )

    if is_heic_upload(filename, content_type):
        jpeg_bytes = convert_heic_to_jpeg(file_bytes)
        return jpeg_bytes, f"{uuid.uuid4()}.jpg", "image/jpeg"

    ext = _ext(filename) or ".jpg"
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        ext = ".jpg"
    safe_name = f"{uuid.uuid4()}{ext}"
    ct = content_type if content_type and content_type.startswith("image/") else f"image/{ext.lstrip('.')}"
    if ct == "image/jpg":
        ct = "image/jpeg"
    return file_bytes, safe_name, ct
