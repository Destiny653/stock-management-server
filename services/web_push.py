"""Web Push delivery for installed storefront PWAs (VAPID + aes128gcm)."""
from __future__ import annotations

import base64
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

from core.config import settings

logger = logging.getLogger(__name__)

_KEYS_PATH = Path(__file__).resolve().parent.parent / ".vapid_keys.json"


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


def _vapid_authorization(endpoint: str, priv_b64: str, pub_b64: str) -> str:
    """Build VAPID Authorization header value."""
    try:
        from py_vapid import Vapid

        vapid = Vapid.from_string(private_key=priv_b64)
        claims = {
            "sub": settings.VAPID_SUBJECT or "mailto:support@stockflow.com",
            "aud": f"{requests.utils.urlparse(endpoint).scheme}://{requests.utils.urlparse(endpoint).netloc}",
            "exp": int(time.time()) + 12 * 3600,
        }
        headers = vapid.sign(claims)
        # py_vapid returns Authorization already formatted
        auth = headers.get("Authorization") or headers.get("authorization")
        if auth:
            return auth
    except Exception as e:
        logger.warning("py_vapid sign failed, using manual JWT: %s", e)

    # Manual ES256 JWT fallback
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
    # Convert DER to raw r||s
    r, s = utils.decode_dss_signature(signature)
    sig = _urlsafe_b64(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
    token = f"{header}.{body}.{sig}"
    return f"vapid t={token}, k={pub_b64}"


def _encrypt_payload(payload: bytes, p256dh: str, auth: str) -> tuple[bytes, dict]:
    """Encrypt with aes128gcm per RFC 8291 (via http_ece)."""
    try:
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
    except Exception as e:
        logger.error("Payload encryption failed: %s", e)
        raise


def _send_one(endpoint: str, p256dh: str, auth_key: str, payload: bytes, pub: str, priv: str) -> int:
    body, extra_headers = _encrypt_payload(payload, p256dh, auth_key)
    headers = {
        "Authorization": _vapid_authorization(endpoint, priv, pub),
        "Content-Type": "application/octet-stream",
        "Content-Encoding": extra_headers.get("Content-Encoding", "aes128gcm"),
        "TTL": extra_headers.get("TTL", "86400"),
        "Urgency": extra_headers.get("Urgency", "normal"),
    }
    resp = requests.post(endpoint, data=body, headers=headers, timeout=15)
    return resp.status_code


async def send_store_push(
    *,
    organization_id: str,
    title: str,
    body: str,
    url: str,
    tag: Optional[str] = None,
    icon: Optional[str] = None,
) -> dict[str, Any]:
    """Send a Web Push notification to all subscribers of a store organization."""
    from models.store_push_subscription import StorePushSubscription

    subs = await StorePushSubscription.find({"organization_id": organization_id}).to_list()
    if not subs:
        return {"sent": 0, "failed": 0}

    pub, priv = _ensure_vapid_keys()
    payload = json.dumps(
        {
            "title": title,
            "body": body,
            "url": url,
            "tag": tag or "store-update",
            "icon": icon or "/icons/icon.svg",
        }
    ).encode("utf-8")

    sent = 0
    failed = 0
    for sub in subs:
        try:
            status = _send_one(sub.endpoint, sub.keys.p256dh, sub.keys.auth, payload, pub, priv)
            if status in (200, 201, 204):
                sent += 1
            elif status in (404, 410):
                failed += 1
                try:
                    await sub.delete()
                except Exception:
                    pass
            else:
                failed += 1
                logger.warning("Push HTTP %s for %s", status, sub.endpoint[:48])
        except Exception as e:
            failed += 1
            logger.warning("Push error: %s", e)

    return {"sent": sent, "failed": failed}


async def notify_new_arrival(organization_id: str, product_name: str, product_id: str) -> None:
    from models.storefront_config import StorefrontConfig

    config = await StorefrontConfig.find_one({"organization_id": organization_id})
    if not config or not config.slug:
        return
    slug = config.slug
    base = (settings.FRONTEND_URL or "").rstrip("/")
    url = f"{base}/store/{slug}/products/{product_id}"
    await send_store_push(
        organization_id=organization_id,
        title=f"New at {config.store_name or 'our store'}",
        body=f"Just arrived: {product_name}",
        url=url,
        tag=f"new-{product_id}",
        icon=f"{base}/store/{slug}/icon" if base else None,
    )


async def notify_promotion(organization_id: str, product_name: str, product_id: str) -> None:
    from models.storefront_config import StorefrontConfig

    config = await StorefrontConfig.find_one({"organization_id": organization_id})
    if not config or not config.slug:
        return
    slug = config.slug
    base = (settings.FRONTEND_URL or "").rstrip("/")
    url = f"{base}/store/{slug}/products/{product_id}"
    await send_store_push(
        organization_id=organization_id,
        title=f"Promotion at {config.store_name or 'our store'}",
        body=f"On sale now: {product_name}",
        url=url,
        tag=f"promo-{product_id}",
        icon=f"{base}/store/{slug}/icon" if base else None,
    )
