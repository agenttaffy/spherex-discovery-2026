import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.demo_service import demo_service
from app.services.cache_service import cache_service

client = TestClient(app)

def test_demo_manifest_endpoint():
    resp = client.get("/api/demo/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cached_cutouts"] == 22
    assert data["presets_count"] == 5

def test_offline_observation_discovery_fallback():
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
        assert frame_data["image_base64"].startswith("data:image/png;base64,")
        assert frame_data["pixel_stats"]["mean_mjy_sr"] != 0.0

def test_diff_on_demo_epochs():
    # Get Barnard's Star demo records
    barnard_recs = demo_service.find_matching_observations(269.45208, 4.69339, radius_deg=0.1)
    # Filter for same detector
    d3_recs = [r for r in barnard_recs if "D3" in r.detector]
    if len(d3_recs) >= 2:
        diff_resp = client.post("/api/frames/diff", json={
            "frame_id_1": d3_recs[0].id,
            "frame_id_2": d3_recs[1].id
        })
        assert diff_resp.status_code == 200
        diff_data = diff_resp.json()
        assert diff_data["eligible"] is True
        assert "diff_stats" in diff_data
        assert not any(str(v) == "nan" for v in diff_data["diff_stats"].values())

def test_webp_frame_and_diff_endpoints():
    barnard_recs = demo_service.find_matching_observations(269.45208, 4.69339, radius_deg=0.1)
    d3_recs = [r for r in barnard_recs if "D3" in r.detector]
    assert len(d3_recs) >= 2

    # Test WebP frame endpoint
    frame_resp = client.get(f"/api/frames/{d3_recs[0].id}?format=webp")
    assert frame_resp.status_code == 200
    f_data = frame_resp.json()
    assert f_data["image_base64"].startswith("data:image/webp;base64,")
    assert f_data["colormapped_base64"].startswith("data:image/webp;base64,")

    # Test WebP diff endpoint
    diff_resp = client.post("/api/frames/diff", json={
        "frame_id_1": d3_recs[0].id,
        "frame_id_2": d3_recs[1].id,
        "format": "webp"
    })
    assert diff_resp.status_code == 200
    d_data = diff_resp.json()
    assert d_data["image_base64"].startswith("data:image/webp;base64,")
    assert "alignment_method" in d_data["diff_stats"]

