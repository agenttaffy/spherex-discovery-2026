import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from app.services import saved_observation_search as saved
from app.services.irsa_client import OBSERVATION_REGISTRY


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("refresh_search_snapshot", ROOT / "scripts/refresh_search_snapshot.py")
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)
REQUEST = "https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=circle+248.16723+66.75502+0.001&RESPONSEFORMAT=CSV"
CSV = ("obs_id,energy_bandpassname,t_min,access_url\n"
       "new,SPHEREx-D6,61001,https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/new.fits\n")


def test_csv_append_preserves_search_dates_and_provenance(tmp_path, monkeypatch):
    old = [{"job": ["old", "spherex_dr1"], "request": REQUEST, "rows": [{
        "obs_id": "old", "energy_bandpassname": "SPHEREx-D6", "t_min": "61000",
        "access_url": "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/old.fits"}]}]
    packed = gzip.compress(json.dumps(old).encode(), mtime=0)
    snapshot = tmp_path / "observation_search_snapshot.json.gz"
    metadata = tmp_path / "observation_search_snapshot_sources.json"
    snapshot.write_bytes(packed)
    metadata.write_text(json.dumps({"snapshot_sha256": hashlib.sha256(packed).hexdigest(),
                                    "source_file_sha256": "original", "saved_date_local": "2026-01-01"}))
    source = tmp_path / "search.csv"
    source.write_text(CSV, encoding="utf-8")
    monkeypatch.setattr(refresh, "DEST", tmp_path)
    monkeypatch.setattr(sys, "argv", ["refresh", str(source), "--saved-date", "2026-11-15",
                                      "--csv-request", REQUEST, "--append"])
    refresh.main()
    provenance = json.loads(metadata.read_text())
    assert len(provenance["sources"]) == 2
    assert provenance["previous_snapshot_sha256"] == hashlib.sha256(packed).hexdigest()
    monkeypatch.setattr(saved, "SNAPSHOT", snapshot)
    monkeypatch.setattr(saved, "SNAPSHOT_SOURCES", metadata)
    records = saved.saved_observations(248.16723, 66.75502, .04, "spherex_dr1", None, 10)
    assert [(r.obs_id, r.search_snapshot_saved) for r in records] == [("old", "2026-01-01"), ("new", "2026-11-15")]
    for record in records:
        OBSERVATION_REGISTRY.pop(record.id, None)


@pytest.mark.parametrize("bad_csv", ["wrong,columns\na,b\n", "obs_id,energy_bandpassname,t_min,access_url\na,D6,NaN,https://example.com/a\n"])
def test_invalid_csv_does_not_change_existing_snapshot(tmp_path, monkeypatch, bad_csv):
    source = tmp_path / "search.csv"
    source.write_text(bad_csv, encoding="utf-8")
    snapshot = tmp_path / "observation_search_snapshot.json.gz"
    snapshot.write_bytes(b"keep this")
    monkeypatch.setattr(refresh, "DEST", tmp_path)
    monkeypatch.setattr(sys, "argv", ["refresh", str(source), "--saved-date", "2026-11-15", "--csv-request", REQUEST])
    with pytest.raises(ValueError):
        refresh.main()
    assert snapshot.read_bytes() == b"keep this"
