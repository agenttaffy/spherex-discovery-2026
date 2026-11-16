import asyncio
import time
from pathlib import Path

from app.api import observations
from app.services import demo_service as demo_module
from app.services import irsa_client as irsa_module
from app.services import saved_observation_search as saved
from app.services.demo_service import DemoService
from app.services.irsa_client import IRSAClient, OBSERVATION_REGISTRY

RA, DEC = 331.09813086506205, -56.801144263858404
WISE_RA, WISE_DEC = 133.75896227492004, -7.242116064321349


def test_cloud_index_is_partial_spatially_bounded_and_filters_detector():
    rows = saved.cloud_header_observations(RA, DEC, "spherex_dr1", None, 60)
    assert len(rows) == 6
    assert all(row.search_provenance == "cloud_header_survey" and row.search_snapshot_saved == "2026-11-16" for row in rows)
    assert len(saved.cloud_header_observations(RA, DEC, "spherex_dr1", "SPHEREx-D2", 60)) == 3
    assert len(saved.cloud_header_observations(RA, DEC, "spherex_dr1", "SPHEREx-D5", 60)) == 3
    assert not saved.cloud_header_observations(RA + .01, DEC, "spherex_dr1", None, 60)
    assert not saved.cloud_header_observations(RA, DEC, "spherex_qr3", None, 60)
    for row in rows:
        OBSERVATION_REGISTRY.pop(row.id, None)


def test_cloud_index_rejects_tampered_package(tmp_path, monkeypatch):
    index = tmp_path / "index.gz"
    index.write_bytes(saved.CLOUD_INDEX.read_bytes() + b"tamper")
    monkeypatch.setattr(saved, "CLOUD_INDEX", index)
    assert not saved.cloud_header_observations(RA, DEC, "spherex_dr1", None, 60)


def test_wise_index_is_bounded_to_verified_coordinate_and_release():
    rows = saved.cloud_header_observations(WISE_RA, WISE_DEC, "spherex_dr1", None, 200)
    assert len(rows) == 72
    assert all(row.search_provenance == "cloud_header_survey" for row in rows)
    assert not saved.cloud_header_observations(WISE_RA + .01, WISE_DEC, "spherex_dr1", None, 200)
    assert not saved.cloud_header_observations(WISE_RA, WISE_DEC, "spherex_qr3", None, 200)
    for row in rows:
        OBSERVATION_REGISTRY.pop(row.id, None)


def test_all_releases_merge_cloud_index_and_preview_demo_without_duplication(monkeypatch):
    preview = Path(__file__).resolve().parents[2] / "data/manifests/demo_preview.json"
    demo = DemoService(preview)
    monkeypatch.setattr(demo_module, "demo_service", demo)
    monkeypatch.setattr(irsa_module, "DEMO_CACHE_ONLY", False)
    monkeypatch.setattr(irsa_module, "SEARCH_COLLECTIONS", ("spherex_dr1", "spherex_qr3"))
    client = IRSAClient()
    client._offline_until = time.time() + 60
    rows = asyncio.run(client.query_observations(RA, DEC, .04, "ALL", None, 60))
    assert len(rows) == 8
    assert sum(row.search_provenance == "cloud_header_survey" for row in rows) == 6
    assert sum(row.search_provenance == "cached_demo" for row in rows) == 2
    assert len({(row.collection, row.obs_id, row.detector) for row in rows}) == 8
    assert [row.mjd for row in rows] == sorted(row.mjd for row in rows)
    for row in rows:
        OBSERVATION_REGISTRY.pop(row.id, None)


def test_wise_cloud_sampling_keeps_two_cached_demo_records(monkeypatch):
    preview = Path(__file__).resolve().parents[2] / "data/manifests/demo_preview.json"
    monkeypatch.setattr(demo_module, "demo_service", DemoService(preview))
    monkeypatch.setattr(irsa_module, "DEMO_CACHE_ONLY", False)
    client = IRSAClient()
    client._offline_until = time.time() + 60
    rows = asyncio.run(client.query_observations(WISE_RA, WISE_DEC, .04, "spherex_dr1", None, 60))
    assert len(rows) == 60
    assert sum(row.search_provenance == "cached_demo" for row in rows) == 2
    assert sum(row.search_provenance == "cloud_header_survey" for row in rows) == 58
    for row in rows:
        OBSERVATION_REGISTRY.pop(row.id, None)


def test_cloud_index_results_marked_incomplete(monkeypatch):
    row = saved.cloud_header_observations(RA, DEC, "spherex_dr1", None, 1)[0]
    async def search(**kwargs): return [row]
    monkeypatch.setattr(observations.irsa_client, "query_observations", search)
    result = asyncio.run(observations.get_observations(ra=str(RA), dec=str(DEC), fov=.04,
                                                       collection="spherex_dr1", detector=None, limit=60))
    assert result.total_found == 1 and result.total_found_is_lower_bound
    OBSERVATION_REGISTRY.pop(row.id, None)
