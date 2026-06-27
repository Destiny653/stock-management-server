from pathlib import Path

from core.uploads import build_upload_url, get_upload_dir


def test_upload_dir_is_absolute_and_created(tmp_path: Path) -> None:
    upload_dir = get_upload_dir("storefront", base_dir=tmp_path)

    assert upload_dir.is_absolute()
    assert upload_dir == tmp_path / "storefront"
    assert upload_dir.exists()


def test_build_upload_url_uses_expected_path() -> None:
    assert build_upload_url("storefront", "example.jpg") == "/uploads/storefront/example.jpg"
