import asyncio
from unittest.mock import AsyncMock, patch

import httpx

from app.api import observations
from app.services.irsa_client import IRSAClient, ObservationResults

EMPTY_CSV = "obs_id,energy_bandpassname,access_url,t_min\n"


def query(client, collection="spherex_dr1"):
    async def run():
        return await observations.get_observations(ra="283.3962", dec="33.0292", fov=.04,
                                                    collection=collection, detector=None, limit=60)
    with patch.object(observations, "irsa_client", client):
        return asyncio.run(run())


def test_live_valid_empty_table_is_distinct_from_archive_outage():
    with patch("app.services.irsa_client.DEMO_CACHE_ONLY", False), \
         patch("app.services.demo_service.demo_service.find_matching_observations", return_value=[]), \
         patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(200, text=EMPTY_CSV))):
        result = query(IRSAClient("https://archive.example/SIA"))
    assert result.observations == []
    assert result.archive_search_status == "available"
    assert not result.total_found_is_lower_bound


def test_unavailable_archive_with_no_saved_rows_is_explicit():
    client = IRSAClient("https://archive.example/SIA")
    with patch("app.services.irsa_client.DEMO_CACHE_ONLY", False), \
         patch.object(client, "_offline_observations", return_value=[]), \
         patch("app.services.demo_service.demo_service.find_matching_observations", return_value=[]), \
         patch("app.services.irsa_client.asyncio.sleep", new=AsyncMock()), \
         patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(503))):
        result = query(client)
    assert result.observations == []
    assert result.archive_search_status == "unavailable"
    assert result.total_found_is_lower_bound


def test_combined_search_reports_partial_when_one_empty_release_fails():
    client = IRSAClient("https://archive.example/SIA")
    async def get(url, params):
        return (httpx.Response(200, text=EMPTY_CSV) if params["COLLECTION"] == "spherex_dr1"
                else httpx.Response(503))
    with patch("app.services.irsa_client.DEMO_CACHE_ONLY", False), \
         patch("app.services.irsa_client.SEARCH_COLLECTIONS", ("spherex_dr1", "spherex_qr3")), \
         patch.object(client, "_offline_observations", return_value=[]), \
         patch("app.services.demo_service.demo_service.find_matching_observations", return_value=[]), \
         patch("app.services.irsa_client.asyncio.sleep", new=AsyncMock()), \
         patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=get)):
        result = query(client, "ALL")
    assert result.observations == [] and result.archive_search_status == "partial"
    assert result.total_found_is_lower_bound


def test_cache_only_mode_reports_live_search_was_not_checked():
    client = IRSAClient("https://archive.example/SIA")
    with patch("app.services.irsa_client.DEMO_CACHE_ONLY", True), \
         patch.object(client, "_offline_observations", return_value=[]), \
         patch("httpx.AsyncClient.get", new=AsyncMock()) as network:
        result = query(client, "ALL")
    assert result.archive_search_status == "not_checked" and result.total_found_is_lower_bound
    network.assert_not_awaited()


def test_results_remain_list_compatible_and_request_scoped():
    one = ObservationResults([], "available")
    two = ObservationResults([], "unavailable")
    assert isinstance(one, list) and one == []
    assert one.archive_search_status == "available" and two.archive_search_status == "unavailable"


def test_concurrent_searches_keep_independent_statuses():
    client = IRSAClient("https://archive.example/SIA")
    async def run():
        entered = asyncio.Event()
        first_calls = set()
        async def get(url, params):
            position = params["POS"]
            first_calls.add(position)
            if len(first_calls) == 2:
                entered.set()
            await entered.wait()
            return (httpx.Response(200, text=EMPTY_CSV) if "1.000000 " in position
                    else httpx.Response(503))
        with patch("app.services.irsa_client.DEMO_CACHE_ONLY", False), \
             patch.object(client, "_offline_observations", return_value=[]), \
             patch("app.services.demo_service.demo_service.find_matching_observations", return_value=[]), \
             patch("app.services.irsa_client.asyncio.sleep", new=AsyncMock()), \
             patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=get)):
            return await asyncio.gather(client.query_observations(1, 2), client.query_observations(3, 4))
    available, unavailable = asyncio.run(run())
    assert available.archive_search_status == "available"
    assert unavailable.archive_search_status == "unavailable"
