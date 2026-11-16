import pytest
from fastapi.testclient import TestClient

from app.api import health
from app.config import CORS_ORIGINS, parse_cors_origins
from app.main import app


def test_cors_defaults_and_explicit_empty():
    assert parse_cors_origins(None) == [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:3000", "http://127.0.0.1:3000",
    ]
    assert parse_cors_origins(" , ") == []
    assert parse_cors_origins("https://frontend.example.test, http://localhost:5173,https://frontend.example.test") == [
        "https://frontend.example.test", "http://localhost:5173",
    ]


@pytest.mark.parametrize("value", [
    "*", "https://*.example.test", "https://frontend.example.test/path",
    "https://frontend.example.test:", "http://localhost:0", "https://a.example.test?x=1",
    "https://a.example.test#x", "https://name@a.example.test", "null",
    "https://frontend.example.test,*", "http://broken host",
])
def test_invalid_cors_origin_is_rejected_without_echoing_configuration(value):
    with pytest.raises(ValueError, match="explicit HTTP") as error:
        parse_cors_origins(value)
    assert value not in str(error.value)


def test_actual_health_accepts_only_configured_browser_origins(monkeypatch):
    monkeypatch.setattr(health, "DEMO_CACHE_ONLY", True)
    with TestClient(app) as client:
        for origin in CORS_ORIGINS:
            response = client.options("/api/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin

        denied = "https://unlisted.example.test"
        response = client.options("/api/health", headers={"Origin": denied, "Access-Control-Request-Method": "GET"})
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers
        direct = client.get("/api/health", headers={"Origin": denied})
        assert direct.status_code == 200 and direct.json()["status"] == "healthy"
        assert "access-control-allow-origin" not in direct.headers
        missing = client.get("/api/nonexistent")
        assert missing.status_code == 404 and missing.json()["detail"] == "Not Found"
