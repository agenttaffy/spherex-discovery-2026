import asyncio
from unittest.mock import AsyncMock, patch

import httpx

from app.api import observations
from app.models.schemas import ObservationRecord
from app.services.irsa_client import IRSAClient, OBSERVATION_REGISTRY


def test_opt_in_deep_search_queries_both_releases_and_bounds_results():
    client = IRSAClient("https://archive.example/SIA")
    requested = []
    async def get(url, params):
        collection = params["COLLECTION"]
        requested.append(collection)
        prefix = "dr" if collection == "spherex_dr1_deep" else "qr"
        base = 60000 if prefix == "dr" else 61000
        rows = "".join(f"{prefix}{i},SPHEREx-D6,https://archive.example/{prefix}{i}.fits,{base+i}\n" for i in range(3))
        return httpx.Response(200, text="obs_id,energy_bandpassname,access_url,t_min\n" + rows)
    with patch("app.services.irsa_client.DEMO_CACHE_ONLY", False), \
         patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=get)):
        rows = asyncio.run(client.query_observations(1, 2, .04, "DEEP", None, 4))
    assert set(requested) == {"spherex_dr1_deep", "spherex_qr3_deep"}
    assert len(rows) == 4
    assert {row.collection for row in rows} == {"spherex_dr1_deep", "spherex_qr3_deep"}
    assert all(row.search_provenance == "irsa_query" for row in rows)
    assert [row.mjd for row in rows] == sorted(row.mjd for row in rows)
    for row in rows:
        OBSERVATION_REGISTRY.pop(row.id, None)


def test_default_all_queries_wide_only():
    client = IRSAClient("https://archive.example/SIA")
    requested = []
    async def get(url, params):
        requested.append(params["COLLECTION"])
        return httpx.Response(200, text="obs_id,energy_bandpassname,access_url,t_min\n")
    with patch("app.services.irsa_client.DEMO_CACHE_ONLY", False), \
         patch("app.services.irsa_client.SEARCH_COLLECTIONS", ("spherex_dr1", "spherex_qr3")), \
         patch("app.services.demo_service.demo_service.find_matching_observations", return_value=[]), \
         patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=get)):
        assert asyncio.run(client.query_observations(1, 2, .04, "ALL", None, 60)) == []
    assert set(requested) == {"spherex_dr1", "spherex_qr3"}


def test_deep_search_keeps_successful_release_when_the_other_fails():
    client = IRSAClient("https://archive.example/SIA")
    async def get(url, params):
        if params["COLLECTION"] == "spherex_dr1_deep":
            return httpx.Response(503)
        return httpx.Response(200, text="obs_id,energy_bandpassname,access_url,t_min\n"
                                       "real,SPHEREx-D6,https://archive.example/real.fits,61000\n")
    with patch("app.services.irsa_client.DEMO_CACHE_ONLY", False), \
         patch.object(client, "_offline_observations", return_value=[]), \
         patch("app.services.demo_service.demo_service.find_matching_observations", return_value=[]), \
         patch("app.services.irsa_client.asyncio.sleep", new=AsyncMock()), \
         patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=get)):
        rows = asyncio.run(client.query_observations(1, 2, .04, "DEEP", None, 60))
    assert [(row.obs_id, row.collection) for row in rows] == [("real", "spherex_qr3_deep")]
    OBSERVATION_REGISTRY.pop(rows[0].id, None)


def test_unavailable_deep_search_does_not_relabel_wide_demo():
    client = IRSAClient()
    client._offline_until = float("inf")
    wide = ObservationRecord(id="wide", obs_id="wide", collection="spherex_dr1", detector="SPHEREx-D6",
                             access_url="https://example.test/image", ra=1, dec=2, search_provenance="cached_demo")
    with patch("app.services.irsa_client.DEMO_CACHE_ONLY", False), \
         patch("app.services.demo_service.demo_service.find_matching_observations", return_value=[wide]), \
         patch("app.services.saved_observation_search.saved_observations", return_value=[wide]), \
         patch("app.services.saved_observation_search.cloud_header_observations", return_value=[wide]):
        assert asyncio.run(client.query_observations(1, 2, .04, "DEEP", None, 60)) == []


def test_combined_deep_results_conservatively_report_incomplete(monkeypatch):
    async def search(**kwargs): return []
    monkeypatch.setattr(observations.irsa_client, "query_observations", search)
    result = asyncio.run(observations.get_observations(ra="1", dec="2", fov=.04,
                                                       collection="DEEP", detector=None, limit=60))
    assert result.total_found == 0 and result.total_found_is_lower_bound
