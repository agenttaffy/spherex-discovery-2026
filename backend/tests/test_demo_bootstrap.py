import hashlib
from pathlib import Path
import sys

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from bootstrap_demo_data import Asset, BootstrapError, cutout_asset, fetch_asset, load_plan, seed_manifest


def asset(data: bytes) -> Asset:
    return Asset(Path("data/cache/demo_multiepoch/example.fits"),
                 "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/example.fits",
                 len(data), hashlib.sha256(data).hexdigest())


def test_release_plan_has_ten_cutouts_and_four_optional_assets():
    base, extension, manifest = load_plan(ROOT, True)
    assert len(base) == 10 and len(extension) == 4
    assert sum(item.size for item in base) == 39_513_600
    assert sum(item.size for item in extension) == 74_528_640
    assert hashlib.sha256(manifest).hexdigest() == "781c4d4ee7d72c04b150d07bcbedd59a8010a04f591de0af8f9d63e27bff4e60"
    assert load_plan(ROOT, False)[1] == []


def test_retry_and_reuse_verified_bytes(tmp_path):
    payload = b"expected FITS test bytes"
    pinned = asset(payload)
    attempts = []

    def upstream(request):
        attempts.append(str(request.url))
        return httpx.Response(503 if len(attempts) == 1 else 200, content=payload)

    with httpx.Client(transport=httpx.MockTransport(upstream)) as client:
        assert fetch_asset(tmp_path, pinned, client) == "downloaded"
        assert fetch_asset(tmp_path, pinned, client) == "cached"
    assert attempts == [pinned.url, pinned.url]
    assert (tmp_path / pinned.path).read_bytes() == payload


def test_alternate_url_may_reorder_but_cannot_change_a_cutout():
    stem = "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/example.fits?"
    row = {"url": stem + "center=1,2&size=0.0350", "bytes": 7, "sha256": "0" * 64,
           "alternate_url": stem + "size=0.0350&center=1,2"}
    result = cutout_asset(row, Path("data/cache/demo_multiepoch"))
    assert result.secondary_url == row["alternate_url"]
    row["alternate_url"] = stem + "size=0.04&center=1,2"
    with pytest.raises(BootstrapError, match="different archive data"):
        cutout_asset(row, Path("data/cache/demo_multiepoch"))


def test_mismatched_bytes_are_never_installed_or_overwritten(tmp_path):
    pinned = asset(b"verified")
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"wrong!!!"))) as client:
        with pytest.raises(BootstrapError, match="pinned size or SHA-256"):
            fetch_asset(tmp_path, pinned, client)
        assert not (tmp_path / pinned.path).exists()
        assert not list(tmp_path.rglob("*.pending"))
        (tmp_path / pinned.path).write_bytes(b"keep local bytes")
        with pytest.raises(BootstrapError, match="Move the affected file aside"):
            fetch_asset(tmp_path, pinned, client)
        assert (tmp_path / pinned.path).read_bytes() == b"keep local bytes"


def test_manifest_check_is_read_only_and_conflicting_data_is_preserved(tmp_path):
    target = tmp_path / "data/cache/demo_multiepoch/demo_dataset.json"
    assert not seed_manifest(tmp_path, b"release bytes", True)
    assert not target.parent.exists()
    assert seed_manifest(tmp_path, b"release bytes", False)
    with pytest.raises(BootstrapError, match="Existing bytes fail verification"):
        seed_manifest(tmp_path, b"different release", False)
    assert target.read_bytes() == b"release bytes"
