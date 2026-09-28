"""Web Push delivery for installed storefront PWAs (VAPID + aes128gcm).

Payload follows Notifications API / web.dev rich-notification guidance:
  title, body, url, icon (192+ PNG), badge (96 monochrome), image (hero / product)
Chrome Android + desktop honour `image`; Safari/Firefox ignore it silently.
All image URLs should be absolute HTTPS (relative paths are resolved against FRONTEND_URL).
"""
from __future__ import annotations

import base64
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

from core.config import settings

logger = logging.getLogger(__name__)

_KEYS_PATH = Path(__file__).resolve().parent.parent / ".vapid_keys.json"

# Keep payload small — push services often cap ~4KB encrypted; URLs only, never image bytes
_MAX_PAYLOAD_CHARS = 3500


def _urlsafe_b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _ensure_vapid_keys() -> tuple[str, str]:
    """Return (public_key, private_key) as URL-safe base64 strings."""
    pub = (settings.VAPID_PUBLIC_KEY or "").strip()
    priv = (settings.VAPID_PRIVATE_KEY or "").strip()
    if pub and priv:
        return pub, priv

    if _KEYS_PATH.exists():
        try:
            data = json.loads(_KEYS_PATH.read_text())
            if data.get("public_key") and data.get("private_key"):
                return data["public_key"], data["private_key"]
        except Exception:
            pass

    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()

    priv_bytes = private_key.private_numbers().private_value.to_bytes(32, "big")
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )

    pub_b64 = _urlsafe_b64(pub_bytes)
    priv_b64 = _urlsafe_b64(priv_bytes)

    try:
        _KEYS_PATH.write_text(
            json.dumps({"public_key": pub_b64, "private_key": priv_b64}, indent=2)
        )
        logger.info("Generated VAPID keys at %s", _KEYS_PATH)
    except Exception as e:
        logger.warning("Could not persist VAPID keys: %s", e)

    return pub_b64, priv_b64


def get_vapid_public_key() -> str:
    pub, _ = _ensure_vapid_keys()
    return pub


def _frontend_origin() -> str:
    return (settings.FRONTEND_URL or "").rstrip("/")


def _api_origin() -> str:
    """Public origin that serves /uploads (API host or same as frontend via rewrite)."""
    raw = (getattr(settings, "PUBLIC_API_URL", None) or "").strip().rstrip("/")
    if raw:
        return raw.replace("/api/v1", "").rstrip("/")
    # Prefer frontend — Next.js rewrites /uploads → backend
    return _frontend_origin()


def absolute_url(path_or_url: Optional[str], *, prefer_api: bool = False) -> Optional[str]:
    """Turn relative paths into absolute HTTPS/HTTP URLs for notification assets."""
    if not path_or_url or not isinstance(path_or_url, str):
        return None
    value = path_or_url.strip()
    if not value or value in ("null", "undefined"):
        return None
    if value.startswith("data:"):
        return None  # browsers won't fetch data: for notification image/icon
    if value.startswith("http://") or value.startswith("https://"):
        return value

    path = value if value.startswith("/") else f"/{value}"
    # Product uploads live on API (or frontend rewrite of /uploads)
    if prefer_api or path.startswith("/uploads/"):
        base = _api_origin() or _frontend_origin()
    else:
        base = _frontend_origin() or _api_origin()
    if not base:
        return path
    return urljoin(base + "/", path.lstrip("/"))


def _vapid_headers(endpoint: str, priv_b64: str, pub_b64: str) -> dict[str, str]:
    """Build VAPID headers compatible with Apple APNs, Google FCM, and Mozilla Push."""
    try:
        from py_vapid import Vapid

        vapid = Vapid.from_string(private_key=priv_b64)
        parsed = urlparse(endpoint)
        claims = {
            "sub": settings.VAPID_SUBJECT or "mailto:support@stockflow.com",
            "aud": f"{parsed.scheme}://{parsed.netloc}",
            "exp": int(time.time()) + 12 * 3600,
        }
        res = vapid.sign(claims)
        headers = {k: v for k, v in res.items()}
        if "Crypto-Key" not in headers and "crypto-key" not in headers:
            headers["Crypto-Key"] = f"p256ecdsa={pub_b64}"
        return headers
    except Exception as e:
        logger.warning("py_vapid sign failed, using manual JWT: %s", e)

    aud = f"{urlparse(endpoint).scheme}://{urlparse(endpoint).netloc}"
    header = _urlsafe_b64(json.dumps({"typ": "JWT", "alg": "ES256"}).encode())
    body = _urlsafe_b64(
        json.dumps(
            {
                "aud": aud,
                "exp": int(time.time()) + 12 * 3600,
                "sub": settings.VAPID_SUBJECT or "mailto:support@stockflow.com",
            }
        ).encode()
    )
    signing_input = f"{header}.{body}".encode()
    private_key = ec.derive_private_key(
        int.from_bytes(_urlsafe_b64decode(priv_b64), "big"),
        ec.SECP256R1(),
        default_backend(),
    )
    signature = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = utils.decode_dss_signature(signature)
    sig = _urlsafe_b64(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
    token = f"{header}.{body}.{sig}"
    return {
        "Authorization": f"vapid t={token},k={pub_b64}",
        "Crypto-Key": f"p256ecdsa={pub_b64}",
    }


def _encrypt_payload(payload: bytes, p256dh: str, auth: str) -> tuple[bytes, dict]:
    """Encrypt with aes128gcm per RFC 8291 (via http_ece)."""
    import http_ece

    client_public = _urlsafe_b64decode(p256dh)
    auth_secret = _urlsafe_b64decode(auth)
    local_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    encrypted = http_ece.encrypt(
        payload,
        private_key=local_key,
        dh=client_public,
        auth_secret=auth_secret,
        version="aes128gcm",
    )
    return encrypted, {
        "Content-Encoding": "aes128gcm",
        "TTL": "86400",
        "Urgency": "normal",
    }


def _send_one(endpoint: str, p256dh: str, auth_key: str, payload: bytes, pub: str, priv: str) -> int:
    body, extra_headers = _encrypt_payload(payload, p256dh, auth_key)
    vapid_h = _vapid_headers(endpoint, priv, pub)
    headers = {
        **vapid_h,
        "Content-Type": "application/octet-stream",
        "Content-Encoding": extra_headers.get("Content-Encoding", "aes128gcm"),
        "TTL": extra_headers.get("TTL", "86400"),
        "Urgency": extra_headers.get("Urgency", "high"),
    }
    resp = requests.post(endpoint, data=body, headers=headers, timeout=20)
    if resp.status_code not in (200, 201, 204):
        logger.warning(
            "Push HTTP %s endpoint=%s body=%s",
            resp.status_code,
            endpoint[:64],
            (resp.text or "")[:200],
        )
    return resp.status_code


def _build_payload(
    *,
    title: str,
    body: str,
    url: str,
    tag: Optional[str] = None,
    icon: Optional[str] = None,
    badge: Optional[str] = None,
    image: Optional[str] = None,
) -> bytes:
    """JSON payload for the service worker — URLs only (never embed image bytes)."""
    abs_url = absolute_url(url) or url
    abs_icon = absolute_url(icon) or absolute_url("/icons/icon-192.png")
    abs_badge = absolute_url(badge) or absolute_url("/icons/badge-96.png")
    abs_image = absolute_url(image, prefer_api=True)

    data: dict[str, Any] = {
        "title": (title or "Store update")[:120],
        "body": (body or "")[:240],
        "url": abs_url,
        "tag": tag or "store-update",
        "icon": abs_icon,
        "badge": abs_badge,
        "timestamp": int(time.time() * 1000),
    }
    if abs_image:
        data["image"] = abs_image

    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    if len(raw) > _MAX_PAYLOAD_CHARS:
        # Drop hero image first if oversize (rare — URLs are short)
        data.pop("image", None)
        raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return raw


async def send_store_push(
    *,
    organization_id: str,
    title: str,
    body: str,
    url: str,
    tag: Optional[str] = None,
    icon: Optional[str] = None,
    badge: Optional[str] = None,
    image: Optional[str] = None,
) -> dict[str, Any]:
    """Send a Web Push notification to all subscribers of a store organization."""
    from models.store_push_subscription import StorePushSubscription
    import asyncio

    org_ids = {str(organization_id)}
    subs = await StorePushSubscription.find(
        {"organization_id": {"$in": list(org_ids)}}
    ).to_list()
    if not subs:
        logger.warning("No push subscribers for organization_id=%s", organization_id)
        return {"sent": 0, "failed": 0, "subscribers": 0}

    pub, priv = _ensure_vapid_keys()
    payload = _build_payload(
        title=title,
        body=body,
        url=url,
        tag=tag,
        icon=icon,
        badge=badge,
        image=image,
    )

    sent = 0
    failed = 0
    loop = asyncio.get_event_loop()

    for sub in subs:
        try:
            status = await loop.run_in_executor(
                None,
                lambda s=sub: _send_one(
                    s.endpoint, s.keys.p256dh, s.keys.auth, payload, pub, priv
                ),
            )
            if status in (200, 201, 204):
                sent += 1
            elif status == 410:
                # 410 Gone: Explicitly unsubscribed by user/device OS — delete record
                failed += 1
                try:
                    await sub.delete()
                except Exception:
                    pass
            else:
                failed += 1
        except Exception as e:
            failed += 1
            logger.warning("Push error for %s: %s", sub.endpoint[:48], e)
        except Exception as e:
            failed += 1
            logger.warning("Push error for %s: %s", sub.endpoint[:48], e)

    logger.info(
        "Push result org=%s sent=%s failed=%s subscribers=%s title=%s has_image=%s",
        organization_id,
        sent,
        failed,
        len(subs),
        title,
        bool(image),
    )
    return {"sent": sent, "failed": failed, "subscribers": len(subs)}


def _product_url(slug: str, product_id: str) -> str:
    return f"/store/{slug}/products/{product_id}"


def _store_icon(slug: str) -> str:
    # Next.js route returns real PNG (192/512) — better than SVG for notifications
    return f"/store/{slug}/icon"


def _product_image_url(product: Any) -> Optional[str]:
    """Best product photo for notification hero `image`."""
    if not product:
        return None
    img = getattr(product, "image_url", None)
    if img:
        return img
    variants = getattr(product, "variants", None) or []
    for v in variants:
        v_img = v.get("image_url") if isinstance(v, dict) else getattr(v, "image_url", None)
        if v_img:
            return v_img
    return None


async def _storefront_for_org(organization_id: str):
    from models.storefront_config import StorefrontConfig

    config = await StorefrontConfig.find_one({"organization_id": str(organization_id)})
    if not config:
        config = await StorefrontConfig.find_one({"organization_id": organization_id})
    return config


async def notify_new_arrival(
    organization_id: str,
    product_name: str,
    product_id: str,
    *,
    image_url: Optional[str] = None,
) -> dict[str, Any]:
    config = await _storefront_for_org(organization_id)
    if not config or not config.slug:
        logger.warning("notify_new_arrival: no storefront for org %s", organization_id)
        return {"sent": 0, "failed": 0, "subscribers": 0}
    slug = config.slug
    return await send_store_push(
        organization_id=str(config.organization_id),
        title=f"New at {config.store_name or 'our store'}",
        body=f"Just arrived: {product_name}",
        url=_product_url(slug, product_id),
        tag=f"new-{product_id}",
        icon=_store_icon(slug),
        badge="/icons/badge-96.png",
        image=image_url,
    )


async def notify_promotion(
    organization_id: str,
    product_name: str,
    product_id: str,
    *,
    image_url: Optional[str] = None,
) -> dict[str, Any]:
    config = await _storefront_for_org(organization_id)
    if not config or not config.slug:
        logger.warning("notify_promotion: no storefront for org %s", organization_id)
        return {"sent": 0, "failed": 0, "subscribers": 0}
    slug = config.slug
    return await send_store_push(
        organization_id=str(config.organization_id),
        title=f"On sale at {config.store_name or 'our store'}",
        body=f"{product_name} — tap to view the deal",
        url=_product_url(slug, product_id),
        tag=f"promo-{product_id}-{int(time.time())}",
        icon=_store_icon(slug),
        badge="/icons/badge-96.png",
        image=image_url,
    )
