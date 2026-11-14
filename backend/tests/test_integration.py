import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_explorer_flow():
    # 1. Health check
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"

    # 2. Get demo presets
    demo_resp = client.get("/api/demo")
    assert demo_resp.status_code == 200
    presets = demo_resp.json()
    assert len(presets) >= 5

    # 3. Query observations for Barnard's Star
    obs_resp = client.get("/api/observations?ra=269.45208&dec=4.69339&fov=0.04&collection=spherex_dr1&limit=5")
    assert obs_resp.status_code == 200
    obs_data = obs_resp.json()
    assert obs_data["total_found"] > 0
    first_obs = obs_data["observations"][0]
    frame_id = first_obs["id"]

    # 4. Fetch frame cutout
    frame_resp = client.get(f"/api/frames/{frame_id}?stretch=asinh&fov=0.04")
    assert frame_resp.status_code == 200
    frame_data = frame_resp.json()
    assert frame_data["frame_id"] == frame_id
    assert frame_data["image_base64"].startswith("data:image/png;base64,")
    assert "min_mjy_sr" in frame_data["pixel_stats"]
    assert len(frame_data["dimensions"]) == 2

def test_invalid_coordinates_flow():
    resp = client.get("/api/observations?ra=invalid&dec=4.69339")
    assert resp.status_code == 400

    resp_dec_out = client.get("/api/observations?ra=100.0&dec=120.0")
    assert resp_dec_out.status_code == 400
