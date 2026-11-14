from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "SPHEREx Discovery"
    assert data["status"] == "operational"

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data

def test_demo_presets():
    response = client.get("/api/demo")
    assert response.status_code == 200
    presets = response.json()
    assert len(presets) >= 5
    names = [p["name"] for p in presets]
    assert "Barnard's Star" in names
    assert "WISE 0855" in names
    assert "RW Aurigae" in names
