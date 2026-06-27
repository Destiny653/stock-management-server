import os
import uuid
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

# We'll use MongoDB GridFS since Render free tier has an ephemeral disk
# This will save uploads directly into MongoDB.
def build_upload_url(bucket_name: str, filename: str) -> str:
    """Returns the URL to access a file in GridFS."""
    return f"/uploads/{bucket_name}/{filename}"

async def upload_to_gridfs(file_bytes: bytes, filename: str, bucket_name: str, content_type: str) -> str:
    from db.mongodb import db
    if db is None:
        raise Exception("Database not initialized")
    fs = AsyncIOMotorGridFSBucket(db, bucket_name=bucket_name)
    grid_in = fs.open_upload_stream(filename, metadata={"contentType": content_type})
    await grid_in.write(file_bytes)
    await grid_in.close()
    return build_upload_url(bucket_name, filename)

# Keep these for backwards compatibility or local testing if needed
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_UPLOAD_ROOT = BASE_DIR / "uploads"

def _get_upload_root() -> Path:
    configured_root = os.getenv("UPLOAD_ROOT") or os.getenv("UPLOAD_DIR")
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    return DEFAULT_UPLOAD_ROOT

UPLOAD_ROOT = _get_upload_root()

def get_upload_dir(subdir: str | None = None, base_dir: Path | None = None) -> Path:
    root = Path(base_dir).expanduser().resolve() if base_dir is not None else UPLOAD_ROOT
    upload_dir = root / subdir if subdir else root
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir
