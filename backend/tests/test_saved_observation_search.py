import json

from app.services import saved_observation_search as saved
from app.services.irsa_client import OBSERVATION_REGISTRY


def test_saved_search_is_limited_to_recorded_position_and_release(tmp_path, monkeypatch):
    path = tmp_path / "saved.json"
    path.write_text(json.dumps([{
        "job": ["r_draconis", "spherex_dr1", 2025.6],
        "request": "https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=circle+248.16723888+66.75502314+0.001&RESPONSEFORMAT=CSV",
        "rows": [{"obs_id": f"obs{i}", "energy_bandpassname": "SPHEREx-D6", "t_min": str(60000+i),
                  "access_url": f"https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/{i}.fits"} for i in range(10)],
    }]), encoding="utf-8")
    monkeypatch.setattr(saved, "SNAPSHOT", path)
    records = saved.saved_observations(248.16722768, 66.75502446, .04, "spherex_dr1", None, 3)
    assert [item.obs_id for item in records] == ["obs0", "obs4", "obs9"]
    assert all(item.search_provenance == "saved_irsa_search" for item in records)
    assert all(OBSERVATION_REGISTRY[item.id]["ra"] == 248.16722768 for item in records)
    assert not saved.saved_observations(248.2, 66.755, .04, "spherex_dr1", None, 3)
    assert not saved.saved_observations(248.16722768, 66.75502446, .0005, "spherex_dr1", None, 3)
    assert not saved.saved_observations(248.16722768, 66.75502446, .04, "spherex_qr3", None, 3)
    for item in records:
        OBSERVATION_REGISTRY.pop(item.id, None)


def test_packaged_snapshot_supplies_historical_results_without_local_cache():
    records = saved.saved_observations(248.16722768, 66.75502446, .04, "spherex_dr1", None, 60)
    assert len(records) > 2
    assert all(r.search_provenance == "saved_irsa_search" for r in records)
    for item in records:
        OBSERVATION_REGISTRY.pop(item.id, None)


def test_packaged_snapshot_rejects_checksum_mismatch(tmp_path, monkeypatch):
    import gzip
    snapshot = tmp_path / "observation_search_snapshot.json.gz"
    snapshot.write_bytes(gzip.compress(b"[]"))
    metadata = tmp_path / "observation_search_snapshot_sources.json"
    metadata.write_text(json.dumps({"snapshot_sha256": "0" * 64, "saved_date_local": "2026-11-14"}))
    monkeypatch.setattr(saved, "SNAPSHOT", snapshot)
    monkeypatch.setattr(saved, "SNAPSHOT_SOURCES", metadata)
    assert saved.saved_observations(248.16722768, 66.75502446, .04, "spherex_dr1", None, 60) == []


def test_packaged_snapshot_rejects_missing_checksum(tmp_path, monkeypatch):
    import gzip
    import hashlib
    snapshot = tmp_path / "observation_search_snapshot.json.gz"
    row = {"obs_id": "obs1", "energy_bandpassname": "SPHEREx-D6", "t_min": "61000",
           "access_url": "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/example.fits"}
    data = [{"job": ["r_draconis", "spherex_dr1"], "request":
             "https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=circle+248.16723+66.75502+0.001",
             "rows": [row]}]
    compressed = gzip.compress(json.dumps(data).encode())
    snapshot.write_bytes(compressed)
    metadata = tmp_path / "observation_search_snapshot_sources.json"
    metadata.write_text(json.dumps({"saved_date_local": "2026-11-14"}))
    monkeypatch.setattr(saved, "SNAPSHOT", snapshot)
    monkeypatch.setattr(saved, "SNAPSHOT_SOURCES", metadata)
    assert saved.saved_observations(248.16722768, 66.75502446, .04, "spherex_dr1", None, 60) == []
    metadata.write_text(json.dumps({"saved_date_local": "2026-11-14",
                                    "snapshot_sha256": hashlib.sha256(compressed).hexdigest()}))
    records = saved.saved_observations(248.16722768, 66.75502446, .04, "spherex_dr1", None, 60)
    assert [record.obs_id for record in records] == ["obs1"]
    OBSERVATION_REGISTRY.pop(records[0].id, None)
