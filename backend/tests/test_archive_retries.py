import asyncio
from unittest.mock import AsyncMock, patch

import httpx

from app.services.irsa_client import IRSAClient
from app.services.cutout_service import CutoutService


def test_observation_search_retries_transient_failure():
    client = IRSAClient("https://archive.example/sia")
    unavailable = httpx.Response(502)
    success = httpx.Response(200, text="obs_id,energy_bandpassname,access_url,t_min\nexample,SPHEREx-D6,https://archive.example/image,60000\n")
    with patch("app.services.irsa_client.DEMO_CACHE_ONLY", False), \
         patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=[unavailable, success])) as get, \
         patch("app.services.irsa_client.asyncio.sleep", new=AsyncMock()):
        results = asyncio.run(client.query_observations(1, 2, collection="spherex_dr1"))
    assert get.await_count == 2
    assert len(results) == 1 and results[0].search_provenance == "irsa_query"


def test_cutout_retries_transient_failure():
    import io
    import numpy as np
    from astropy.io import fits
    buffer = io.BytesIO()
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(np.ones((2, 2)), name="IMAGE"),
                  fits.ImageHDU(np.zeros((2, 2), dtype=np.int32), name="FLAGS"),
                  fits.ImageHDU(np.ones((2, 2)), name="VARIANCE")]).writeto(buffer)
    valid = buffer.getvalue()
    service = CutoutService()
    with patch("app.services.cutout_service.cache_service.get", return_value=None), \
         patch("app.services.cutout_service.cache_service.set") as save, \
         patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=[httpx.Response(503), httpx.Response(200, content=valid)])) as get, \
         patch("app.services.cutout_service.asyncio.sleep", new=AsyncMock()):
        result, provenance = asyncio.run(service.fetch_cutout_with_source("https://archive.example/image", 1, 2))
    assert get.await_count == 2
    assert result == valid and provenance == "live_archive_cutout"
    save.assert_called_once()


def test_failed_archive_cutout_never_becomes_a_synthetic_observation(monkeypatch):
    import pytest
    from app.services.irsa_client import OBSERVATION_REGISTRY
    service = CutoutService()
    failure = AsyncMock(side_effect=httpx.ConnectError("unavailable"))
    monkeypatch.setattr(service, "fetch_cutout_with_source", failure)
    for provenance in ("irsa_query", "saved_irsa_search"):
        monkeypatch.setitem(OBSERVATION_REGISTRY, "missing-image", {
            "obs_id": "missing", "collection": "spherex_dr1", "detector": "SPHEREx-D1",
            "utc_date": "2025-01-01", "access_url": "https://example.invalid/image.fits",
            "ra": 1.0, "dec": 2.0, "search_provenance": provenance,
        })
        with pytest.raises(ValueError, match="could not deliver"):
            asyncio.run(service.get_frame("missing-image"))


def test_live_search_samples_across_time_instead_of_returning_first_rows():
    client = IRSAClient("https://archive.example/sia")
    csv = "obs_id,energy_bandpassname,access_url,t_min\n" + "".join(
        f"obs{i},SPHEREx-D6,https://archive.example/{i}.fits,{60000+i}\n" for i in reversed(range(10))
    )
    with patch("app.services.irsa_client.DEMO_CACHE_ONLY", False), patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(200, text=csv))):
        rows = asyncio.run(client.query_observations(1, 2, collection="spherex_dr1", limit=3))
    assert [r.obs_id for r in rows] == ["obs0", "obs4", "obs9"]


def test_unexpected_success_html_is_not_mistaken_for_live_observations():
    client = IRSAClient("https://archive.example/sia")
    with patch("app.services.irsa_client.DEMO_CACHE_ONLY", False), \
         patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(200, text="<html>maintenance</html>"))), \
         patch("app.services.saved_observation_search.saved_observations", return_value=[]), \
         patch("app.services.demo_service.demo_service.find_matching_observations", return_value=[]):
        rows = asyncio.run(client.query_observations(1, 2, collection="spherex_dr1"))
    assert rows == []
    assert client._offline_by_collection["spherex_dr1"] > 0


def test_archive_cooldown_does_not_requery_for_uncached_position():
    import time
    client = IRSAClient("https://archive.example/sia")
    client._offline_until = time.time() + 60
    with patch("app.services.irsa_client.DEMO_CACHE_ONLY", False), \
         patch.object(client, "_offline_observations", return_value=[]), \
         patch("httpx.AsyncClient.get", new=AsyncMock()) as get:
        assert asyncio.run(client.query_observations(1, 2, collection="spherex_dr1")) == []
    get.assert_not_awaited()


def test_connectivity_probe_rejects_successful_maintenance_page():
    client = IRSAClient("https://archive.example/sia")
    responses = [httpx.Response(200, text="<html>maintenance</html>"),
                 httpx.Response(200, text="obs_id,energy_bandpassname,access_url,t_min\n"),
                 httpx.Response(503)]
    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=responses)):
        assert asyncio.run(client.check_connectivity()) is False
        assert asyncio.run(client.check_connectivity()) is True
        assert asyncio.run(client.check_connectivity()) is False


def test_live_search_tolerates_missing_optional_numbers_and_all_detector_filter():
    client = IRSAClient("https://archive.example/sia")
    csv = "obs_id,energy_bandpassname,access_url,t_min,em_min,s_ra\nexample,SPHEREx-D6,https://archive.example/image,nan,bad,not-a-number\n"
    with patch("app.services.irsa_client.DEMO_CACHE_ONLY", False), patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(200, text=csv))):
        rows = asyncio.run(client.query_observations(1, 2, collection="spherex_dr1", detector="ALL"))
    assert len(rows) == 1
    assert rows[0].mjd is None and rows[0].utc_date is None and rows[0].em_min is None


def test_same_exposure_at_different_sky_positions_has_separate_registry_ids():
    from app.services.irsa_client import OBSERVATION_REGISTRY
    client = IRSAClient("https://archive.example/sia")
    csv = "obs_id,energy_bandpassname,access_url,t_min\nshared,SPHEREx-D6,https://archive.example/image,60000\n"
    with patch("app.services.irsa_client.DEMO_CACHE_ONLY", False), patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(200, text=csv))):
        first = asyncio.run(client.query_observations(1, 2, collection="spherex_dr1"))[0]
        second = asyncio.run(client.query_observations(1.01, 2, collection="spherex_dr1"))[0]
    assert first.id != second.id
    assert OBSERVATION_REGISTRY[first.id]["ra"] == 1
    assert OBSERVATION_REGISTRY[second.id]["ra"] == 1.01
    OBSERVATION_REGISTRY.pop(first.id, None)
    OBSERVATION_REGISTRY.pop(second.id, None)


def test_observation_response_marks_historical_results_as_incomplete(monkeypatch):
    from app.api import observations
    from app.models.schemas import ObservationRecord
    row = ObservationRecord(id="sample", obs_id="sample", detector="SPHEREx-D6", access_url="https://example.invalid/image", ra=1, dec=2, search_provenance="saved_irsa_search")
    monkeypatch.setattr(observations.irsa_client, "query_observations", AsyncMock(return_value=[row]))
    result = asyncio.run(observations.get_observations(ra="1", dec="2", fov=.04, collection="spherex_dr1", detector=None, limit=60))
    assert result.total_found == 1 and result.total_found_is_lower_bound is True


def test_health_remains_available_when_archive_probe_times_out(monkeypatch):
    from app.api import health
    monkeypatch.setattr(health, "DEMO_CACHE_ONLY", False)
    async def timeout(coro, timeout):
        coro.close()
        raise asyncio.TimeoutError()
    monkeypatch.setattr(health.asyncio, "wait_for", timeout)
    result = asyncio.run(health.get_health())
    assert result.status == "healthy" and result.irsa_connected is False


def test_readiness_never_calls_the_external_archive(monkeypatch):
    from app.api import health
    probe = AsyncMock(side_effect=AssertionError("readiness must not query IRSA"))
    monkeypatch.setattr(health.irsa_client, "check_connectivity", probe)
    result = asyncio.run(health.get_readiness())
    assert result["status"] == "healthy"
    probe.assert_not_awaited()
