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
HEIC_BRANDS = {
    b"heic",
    b"heix",
    b"hevc",
    b"hevx",
    b"heim",
    b"heis",
    b"mif1",
    b"msf1",
}


def _ext(filename: Optional[str]) -> str:
    return os.path.splitext(filename or "")[1].lower()


def looks_like_heic_bytes(file_bytes: bytes) -> bool:
    """Detect HEIC/HEIF via ISO BMFF `ftyp` brand (iOS often sends wrong MIME)."""
    if len(file_bytes) < 12:
        return False
    if file_bytes[4:8] != b"ftyp":
        return False
    return file_bytes[8:12] in HEIC_BRANDS


def is_allowed_image_upload(
    filename: Optional[str],
    content_type: Optional[str],
    file_bytes: Optional[bytes] = None,
) -> bool:
    """HEIC often arrives as application/octet-stream — allow by extension/bytes too."""
    ext = _ext(filename)
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return True
    ct = (content_type or "").lower().strip()
    if ct.startswith("image/"):
        return True
    if ct in HEIC_CONTENT_TYPES:
        return True
    if file_bytes and looks_like_heic_bytes(file_bytes):
        return True
    if file_bytes and len(file_bytes) > 8:
        if file_bytes[:3] == b"\xff\xd8\xff":
            return True
        if file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            return True
        if file_bytes[:6] in (b"GIF87a", b"GIF89a"):
            return True
        if file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
            return True
    return False


def is_heic_upload(
    filename: Optional[str],
    content_type: Optional[str],
    file_bytes: Optional[bytes] = None,
) -> bool:
    ext = _ext(filename)
    ct = (content_type or "").lower().strip()
    if ext in HEIC_EXTENSIONS or ct in HEIC_CONTENT_TYPES:
        return True
    if file_bytes and looks_like_heic_bytes(file_bytes):
        return True
    return False


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
            detail=(
                "Could not process HEIC/HEIF image. "
                "Ensure the server has pillow-heif installed, or convert to JPG/PNG. "
                f"({exc})"
            ),
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
    if not filename or filename in ("blob", "image", "undefined"):
        if looks_like_heic_bytes(file_bytes):
            filename = "photo.heic"
        elif file_bytes[:3] == b"\xff\xd8\xff":
            filename = "photo.jpg"
        elif file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            filename = "photo.png"
        else:
            filename = "photo.jpg"

    if not is_allowed_image_upload(filename, content_type, file_bytes):
        raise HTTPException(
            status_code=400,
            detail="File must be an image (JPG, PNG, WEBP, GIF, HEIC, HEIF)",
        )

    if is_heic_upload(filename, content_type, file_bytes):
        jpeg_bytes = convert_heic_to_jpeg(file_bytes)
        return jpeg_bytes, f"{uuid.uuid4()}.jpg", "image/jpeg"

    ext = _ext(filename) or ".jpg"
    non_heic = ALLOWED_IMAGE_EXTENSIONS - HEIC_EXTENSIONS
    if ext not in non_heic:
        if file_bytes[:3] == b"\xff\xd8\xff":
            ext = ".jpg"
        elif file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            ext = ".png"
        else:
            ext = ".jpg"
    safe_name = f"{uuid.uuid4()}{ext}"
    ct = content_type if content_type and content_type.startswith("image/") else f"image/{ext.lstrip('.')}"
    if ct == "image/jpg":
        ct = "image/jpeg"
    return file_bytes, safe_name, ct
