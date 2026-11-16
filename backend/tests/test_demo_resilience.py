import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.demo_service import demo_service
from app.services.cache_service import cache_service

client = TestClient(app)


def _fixture_record(monkeypatch, index=0):
    from app.models.schemas import ObservationRecord
    from app.services.irsa_client import OBSERVATION_REGISTRY

    record = ObservationRecord(id=f"offline-fixture-{index}", obs_id=f"fixture-{index}",
        collection="spherex_dr1", detector="SPHEREx-D3", access_url=f"https://example.invalid/fixture-{index}.fits",
        ra=269.45208, dec=4.69339, mjd=60000.0 + index, search_provenance="cached_demo")
    metadata = record.model_dump()
    metadata["cached_cutout_url"] = f"fixture-cache-{index}"
    monkeypatch.setitem(OBSERVATION_REGISTRY, record.id, metadata)
    return record


def _fixture_fits(record, index=0):
    """In-memory FITS for codec/offline tests; never marketed as archive data."""
    import io
    import numpy as np
    from astropy.io import fits
    from astropy.wcs import WCS

    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [record.ra, record.dec]
    wcs.wcs.crpix = [11, 11]
    wcs.wcs.cdelt = [-6.2 / 3600, 6.2 / 3600]
    header = wcs.to_header()
    header["OBSID"] = record.obs_id
    header["DETECTOR"] = int(record.detector[-1])
    header["MJD-BEG"], header["MJD-END"] = 60000.0 + index, 60000.01 + index
    image = np.arange(441, dtype=np.float32).reshape(21, 21) + 1
    output = io.BytesIO()
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(image, header=header, name="IMAGE")]).writeto(output)
    return output.getvalue()

def test_demo_manifest_endpoint():
    resp = client.get("/api/demo/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cached_cutouts"] == 22
    assert data["presets_count"] == 5

def test_offline_observation_discovery_fallback(monkeypatch):
    from app.services.irsa_client import OBSERVATION_REGISTRY

    records = [_fixture_record(monkeypatch)]
    monkeypatch.setattr(demo_service, "find_matching_observations", lambda **kwargs: records)
    monkeypatch.setattr("app.services.saved_observation_search.saved_observations", lambda *args, **kwargs: [])
    cached_url = OBSERVATION_REGISTRY[records[0].id]["cached_cutout_url"]
    payload = _fixture_fits(records[0])
    # Simulate the local FITS cache; the test must not depend on staging or
    # contact the independent cloud path when claiming an offline result.
    monkeypatch.setattr(cache_service, "get", lambda key: payload if key == cached_url else None)
    from unittest.mock import Mock
    cloud = Mock(side_effect=AssertionError("unexpected cloud request"))
    monkeypatch.setattr("app.services.cutout_service.cloud_cutout", cloud)
    # Simulate NASA IRSA network timeout / failure
    with patch("httpx.AsyncClient.get", side_effect=Exception("Simulated IRSA network timeout")):
        # Query Barnard's Star coordinates
        resp = client.get("/api/observations?ra=269.45208&dec=4.69339&fov=0.05&collection=spherex_dr1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] > 0
        assert data["observations"][0]["obs_id"] != ""
        
        # Verify genuine frame can be retrieved from disk cache without network
        first_frame_id = data["observations"][0]["id"]
        frame_resp = client.get(f"/api/frames/{first_frame_id}?stretch=asinh&fov=0.04")
        assert frame_resp.status_code == 200
        frame_data = frame_resp.json()
        assert frame_data["is_synthetic"] is False
        assert frame_data["image_provenance"] == "cached_demo_cutout"
        assert frame_data["image_base64"].startswith("data:image/png;base64,")
        assert frame_data["pixel_stats"]["mean_mjy_sr"] != 0.0
        cloud.assert_not_called()


def test_offline_search_does_not_expand_requested_radius():
    with patch("httpx.AsyncClient.get", side_effect=Exception("Offline")):
        resp = client.get("/api/observations?ra=269.55208&dec=4.69339&fov=0.01&collection=spherex_dr1")
    assert resp.status_code == 200
    assert resp.json()["total_found"] == 0

def test_cache_only_demo_never_queries_live_observations_or_health():
    with (
        patch("app.services.irsa_client.DEMO_CACHE_ONLY", True),
        patch("app.api.health.DEMO_CACHE_ONLY", True),
        patch("httpx.AsyncClient.get") as archive_get,
    ):
        health = client.get("/api/health").json()
        covered = client.get("/api/observations?ra=269.45208&dec=4.69339&fov=0.05&collection=ALL").json()
        empty = client.get("/api/observations?ra=0&dec=0&fov=0.01&collection=ALL").json()
    archive_get.assert_not_called()
    assert health["demo_cache_only"] is True
    assert health["irsa_connected"] is False
    assert covered["observations"]
    assert all(record["search_provenance"] == "cached_demo" for record in covered["observations"])
    assert empty["total_found"] == 0

def test_diff_on_demo_epochs(monkeypatch):
    from unittest.mock import AsyncMock, Mock
    from app.services.irsa_client import OBSERVATION_REGISTRY
    records = [_fixture_record(monkeypatch, 0), _fixture_record(monkeypatch, 1)]
    payloads = {OBSERVATION_REGISTRY[r.id]["cached_cutout_url"]: _fixture_fits(r, index)
                for index, r in enumerate(records)}
    monkeypatch.setattr(cache_service, "get", lambda key: payloads.get(key))
    cloud = Mock(side_effect=AssertionError("fixture test must not contact cloud"))
    monkeypatch.setattr("app.services.cutout_service.cloud_cutout", cloud)
    archive = AsyncMock(side_effect=AssertionError("fixture test must not contact IRSA"))
    monkeypatch.setattr("httpx.AsyncClient.get", archive)
    diff_resp = client.post("/api/frames/diff", json={
        "frame_id_1": records[0].id, "frame_id_2": records[1].id,
    })
    assert diff_resp.status_code == 422
    assert "per-pixel wavelength compatibility" in diff_resp.json()["detail"]
    cloud.assert_not_called()
    archive.assert_not_awaited()

def test_webp_frame_and_diff_endpoints(monkeypatch):
    import base64
    import io
    from unittest.mock import AsyncMock, Mock
    from PIL import Image
    from app.services.irsa_client import OBSERVATION_REGISTRY

    d3_recs = [_fixture_record(monkeypatch, 0), _fixture_record(monkeypatch, 1)]

    payloads = {OBSERVATION_REGISTRY[record.id]["cached_cutout_url"]: _fixture_fits(record, index)
                for index, record in enumerate(d3_recs[:2])}
    monkeypatch.setattr(cache_service, "get", lambda key: payloads.get(key))
    cloud = Mock(side_effect=AssertionError("codec test must not contact cloud"))
    monkeypatch.setattr("app.services.cutout_service.cloud_cutout", cloud)
    archive = AsyncMock(side_effect=AssertionError("codec test must not contact IRSA"))
    monkeypatch.setattr("httpx.AsyncClient.get", archive)

    # Test WebP frame endpoint
    frame_resp = client.get(f"/api/frames/{d3_recs[0].id}?format=webp")
    assert frame_resp.status_code == 200
    f_data = frame_resp.json()
    assert f_data["image_base64"].startswith("data:image/webp;base64,")
    assert f_data["colormapped_base64"].startswith("data:image/webp;base64,")
    for key in ("image_base64", "colormapped_base64"):
        raw = base64.b64decode(f_data[key].split(",", 1)[1], validate=True)
        with Image.open(io.BytesIO(raw)) as rendered:
            assert rendered.format == "WEBP" and rendered.size == (21, 21)

    # Test WebP diff endpoint
    diff_resp = client.post("/api/frames/diff", json={
        "frame_id_1": d3_recs[0].id,
        "frame_id_2": d3_recs[1].id,
        "format": "webp"
    })
    assert diff_resp.status_code == 422
    assert "spectral WCS" in diff_resp.json()["detail"]
    # The fixture intentionally has no independently verified spectral map;
    # rejecting subtraction is required, not an indication of target motion.
    cloud.assert_not_called()
    archive.assert_not_awaited()

