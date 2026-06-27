import os
from pathlib import Path


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


def build_upload_url(*parts: str) -> str:
    clean_parts = [part for part in parts if part]
    return "/uploads/" + "/".join(clean_parts) if clean_parts else "/uploads"
