import asyncio
import shutil
from pathlib import Path

from app.api import observations
from app.services import demo_service as module
from app.services.demo_service import DemoService
from app.services.irsa_client import OBSERVATION_REGISTRY

ROOT = Path(__file__).resolve().parents[2]
RA, DEC = 269.4461286205729, 4.769998359667445


def setup_manifests(tmp_path, monkeypatch, cache_only=False):
    for name in ("demo_dataset.json", "demo_preview.json", "demo_preview_assets.json"):
        shutil.copyfile(ROOT / "data/manifests" / name, tmp_path / name)
    monkeypatch.setattr(module, "MANIFESTS_DIR", tmp_path)
    monkeypatch.setattr(module, "DEMO_CACHE_ONLY", cache_only)
    return tmp_path / "demo_dataset.json"


def test_default_checkout_uses_vetted_metadata_without_claiming_cached_images(tmp_path, monkeypatch):
    path = setup_manifests(tmp_path, monkeypatch)
    service = DemoService(path)
    monkeypatch.setattr(module.cache_service, "get", lambda *args: None)
    rows = service.find_matching_observations(RA, DEC, .04, "ALL", "ALL")
    assert len(rows) == 2
    assert {row.collection for row in rows} == {"spherex_dr1", "spherex_qr3"}
    assert all(row.search_provenance == "demo_metadata" for row in rows)
    assert all("cached_cutout_url" not in OBSERVATION_REGISTRY[row.id] for row in rows)
    assert all((row.ra, row.dec) == (RA, DEC) for row in rows)
    preset = next(row for row in service.get_presets() if row.id == "barnards_star")
    assert (preset.ra, preset.dec) == (RA, DEC) and preset.default_collection == "ALL"
    for row in rows:
        OBSERVATION_REGISTRY.pop(row.id, None)


def test_custom_manifest_and_cache_only_do_not_add_unavailable_metadata(tmp_path, monkeypatch):
    default = setup_manifests(tmp_path, monkeypatch)
    custom = tmp_path / "custom.json"
    shutil.copyfile(default, custom)
    assert not DemoService(custom).preview_metadata
    monkeypatch.setattr(module, "DEMO_CACHE_ONLY", True)
    assert not DemoService(default).preview_metadata


def test_modified_preview_manifest_fails_closed(tmp_path, monkeypatch):
    path = setup_manifests(tmp_path, monkeypatch)
    with (tmp_path / "demo_preview.json").open("a", encoding="utf-8") as stream:
        stream.write(" ")
    assert not DemoService(path).preview_metadata


def test_metadata_search_records_do_not_share_coordinate_registry_ids(tmp_path, monkeypatch):
    service = DemoService(setup_manifests(tmp_path, monkeypatch))
    first = service.find_matching_observations(RA, DEC, .04, "spherex_dr1", None)[0]
    second = service.find_matching_observations(RA + .001, DEC, .04, "spherex_dr1", None)[0]
    assert first.id != second.id
    assert OBSERVATION_REGISTRY[first.id]["ra"] == RA
    assert OBSERVATION_REGISTRY[second.id]["ra"] == RA + .001
    OBSERVATION_REGISTRY.pop(first.id, None)
    OBSERVATION_REGISTRY.pop(second.id, None)


def test_demo_metadata_results_are_marked_incomplete(tmp_path, monkeypatch):
    service = DemoService(setup_manifests(tmp_path, monkeypatch))
    row = service.find_matching_observations(RA, DEC, .04, "spherex_dr1", None)[0]
    async def search(**kwargs): return [row]
    monkeypatch.setattr(observations.irsa_client, "query_observations", search)
    result = asyncio.run(observations.get_observations(ra=str(RA), dec=str(DEC), fov=.04,
                                                       collection="spherex_dr1", detector=None, limit=60))
    assert result.total_found_is_lower_bound
    OBSERVATION_REGISTRY.pop(row.id, None)
