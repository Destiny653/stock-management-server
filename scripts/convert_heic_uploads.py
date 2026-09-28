"""
Walk product / org / storefront image URLs and convert HEIC/HEIF → JPEG.

New uploads already convert on ingest. This fixes older HEIC files that only
render on iPhone/Safari.

Usage (from stock-management-server):
  .venv/bin/python scripts/convert_heic_uploads.py          # dry-run
  .venv/bin/python scripts/convert_heic_uploads.py --apply  # write changes
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket


HEIC_RE = re.compile(r"\.(heic|heif)(?:\?.*)?$", re.IGNORECASE)


def is_heic_url(url: Optional[str]) -> bool:
    if not url or not isinstance(url, str):
        return False
    return bool(HEIC_RE.search(url.strip()))


def parse_upload_url(url: str) -> Optional[Tuple[str, str]]:
    """Return (bucket, filename) for /uploads/{bucket}/{filename} URLs."""
    clean = url.replace("http://127.0.0.1:8000", "").replace("http://localhost:8000", "")
    parts = [p for p in clean.split("/") if p]
    if len(parts) >= 3 and parts[0] == "uploads":
        return parts[1], parts[2].split("?")[0]
    return None


async def convert_gridfs_heic(
    db,
    bucket_name: str,
    filename: str,
) -> Optional[str]:
    """Convert a GridFS HEIC file to JPEG; return new /uploads/.../.jpg URL."""
    from core.image_upload import convert_heic_to_jpeg, looks_like_heic_bytes, is_heic_upload

    fs = AsyncIOMotorGridFSBucket(db, bucket_name=bucket_name)
    docs = await fs.find({"filename": filename}).to_list(length=1)
    if not docs:
        print(f"  ! missing GridFS file: {bucket_name}/{filename}")
        return None

    grid_out = await fs.open_download_stream_by_name(filename)
    raw = await grid_out.read()
    ct = (grid_out.metadata or {}).get("contentType")

    if not is_heic_upload(filename, ct, raw) and not looks_like_heic_bytes(raw):
        print(f"  ~ skip (not HEIC bytes): {bucket_name}/{filename}")
        return None

    jpeg = convert_heic_to_jpeg(raw)
    jpg_name = filename.rsplit(".", 1)[0] + ".jpg"
    existing = await fs.find({"filename": jpg_name}).to_list(length=1)
    if not existing:
        grid_in = fs.open_upload_stream(
            jpg_name, metadata={"contentType": "image/jpeg", "convertedFrom": filename}
        )
        await grid_in.write(jpeg)
        await grid_in.close()
    return f"/uploads/{bucket_name}/{jpg_name}"


async def rewrite_url(db, url: str, apply: bool) -> Optional[str]:
    if not is_heic_url(url):
        return None
    parsed = parse_upload_url(url)
    if not parsed:
        print(f"  ! unsupported URL shape: {url}")
        return None
    bucket, filename = parsed
    if not apply:
        print(f"  would convert {bucket}/{filename}")
        return url.rsplit(".", 1)[0] + ".jpg"
    new_url = await convert_gridfs_heic(db, bucket, filename)
    return new_url


async def walk_products(db, apply: bool) -> Dict[str, int]:
    stats = {"scanned": 0, "updated": 0, "variants": 0}
    coll = db["products"]
    cursor = coll.find(
        {
            "$or": [
                {"image_url": {"$regex": r"\.(heic|heif)$", "$options": "i"}},
                {"variants.image_url": {"$regex": r"\.(heic|heif)$", "$options": "i"}},
            ]
        }
    )
    async for doc in cursor:
        stats["scanned"] += 1
        updates: Dict[str, Any] = {}
        pid = str(doc.get("_id"))

        image_url = doc.get("image_url")
        if is_heic_url(image_url):
            print(f"Product {pid} image_url={image_url}")
            new_url = await rewrite_url(db, image_url, apply)
            if new_url and apply:
                updates["image_url"] = new_url

        variants = doc.get("variants") or []
        changed_variants = False
        new_variants: List[Any] = []
        for v in variants:
            if not isinstance(v, dict):
                new_variants.append(v)
                continue
            v_url = v.get("image_url")
            if is_heic_url(v_url):
                print(f"Product {pid} variant image_url={v_url}")
                new_url = await rewrite_url(db, v_url, apply)
                if new_url and apply:
                    v = {**v, "image_url": new_url}
                    changed_variants = True
                    stats["variants"] += 1
            new_variants.append(v)

        if changed_variants:
            updates["variants"] = new_variants

        if updates and apply:
            await coll.update_one({"_id": doc["_id"]}, {"$set": updates})
            stats["updated"] += 1
            print(f"  ✓ updated product {pid}")
        elif updates or is_heic_url(image_url) or changed_variants:
            stats["updated"] += 1

    return stats


async def walk_simple(
    db,
    collection: str,
    fields: List[str],
    apply: bool,
) -> Dict[str, int]:
    stats = {"scanned": 0, "updated": 0}
    coll = db[collection]
    or_clause = [{f: {"$regex": r"\.(heic|heif)$", "$options": "i"}} for f in fields]
    cursor = coll.find({"$or": or_clause})
    async for doc in cursor:
        stats["scanned"] += 1
        updates: Dict[str, Any] = {}
        for field in fields:
            url = doc.get(field)
            if is_heic_url(url):
                print(f"{collection} {doc.get('_id')} {field}={url}")
                new_url = await rewrite_url(db, url, apply)
                if new_url and apply:
                    updates[field] = new_url
        if updates and apply:
            await coll.update_one({"_id": doc["_id"]}, {"$set": updates})
            stats["updated"] += 1
            print(f"  ✓ updated {collection} {doc.get('_id')}")
        elif updates:
            stats["updated"] += 1
    return stats


async def main(apply: bool) -> None:
    load_dotenv(".env")
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB_NAME", "stockflow_db")
    client = AsyncIOMotorClient(mongodb_url)
    db = client[db_name]

    print(f"DB={db_name} apply={apply}")
    p = await walk_products(db, apply)
    print(f"products: {p}")

    o = await walk_simple(db, "organizations", ["logo_url"], apply)
    print(f"organizations: {o}")

    s = await walk_simple(
        db, "storefront_configs", ["logo_url", "banner_url", "favicon_url"], apply
    )
    print(f"storefront_configs: {s}")

    if not apply:
        print("\nDry-run only. Re-run with --apply to convert and update URLs.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert stored HEIC uploads to JPEG")
    parser.add_argument("--apply", action="store_true", help="Write converted files + DB updates")
    args = parser.parse_args()
    asyncio.run(main(apply=args.apply))
