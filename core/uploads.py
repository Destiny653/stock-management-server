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

async def delete_upload(image_url: str | None) -> None:
    """Deletes an image from GridFS and local filesystem if it exists."""
    if not image_url:
        return
        
    # Standardize path
    clean_url = image_url.replace("http://127.0.0.1:8000", "").replace("http://localhost:8000", "")
    parts = [p for p in clean_url.split("/") if p]
    
    # URL is like /uploads/{bucket}/{filename}
    if len(parts) >= 3 and parts[0] == "uploads":
        bucket_name = parts[1]
        filename = parts[2]
        
        # 1. Try deleting from GridFS
        try:
            from db.mongodb import db
            if db is not None:
                fs = AsyncIOMotorGridFSBucket(db, bucket_name=bucket_name)
                cursor = fs.find({"filename": filename})
                file_docs = await cursor.to_list(length=1)
                if file_docs:
                    await fs.delete(file_docs[0]["_id"])
        except Exception as e:
            print(f"Failed to delete GridFS file {filename}: {e}")
            
        # 2. Try deleting from local filesystem
        try:
            file_path = UPLOAD_ROOT / bucket_name / filename
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Failed to delete local file {file_path}: {e}")

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
