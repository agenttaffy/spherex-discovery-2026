from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import cube
from app.main import app
from app.science.spectral_cube import CubeCoverageError
from app.services import cube_preview as preview

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from refresh_cube_preview import atomic_publish, verify_local


EXPECTED = {
    "barnards_star": (8, 90, 2, 2),
    "wise_0855": (99, 0, 1, 2),
    "rw_aurigae": (35, 15, 50, 2),
    "r_draconis": (0, 100, 0, 2),
    "epsilon_indi_b": (100, 0, 0, 2),
}


@pytest.fixture(scope="module")
def samples():
    return preview.read_preview(preview.PREVIEW_FILE)["samples"]


def test_exact_and_rounded_keys_match_only_their_own_preview(samples):
    for key, row in samples.items():
        for ra, dec in ((row["ra"], row["dec"]), (round(row["ra"], 5), round(row["dec"], 5))):
            reply = preview.lookup_preview(ra, dec, 102, "archive_unreachable")
            assert reply["source"] == "cached_dr1_preview"
            assert reply["preview"]["preset_id"] == key
            assert reply["preview"]["sample_coordinate"] == {"ra": row["ra"], "dec": row["dec"]}
            assert reply["tile"] == row["tile"] and reply["pixel"] == row["pixel"]
            assert (reply["ra"], reply["dec"]) == (ra, dec)
        tolerance = preview.COORDINATE_TOLERANCE_DEG
        assert preview.lookup_preview(row["ra"] + tolerance * .999, row["dec"], None, "archive_unreachable")
        assert preview.lookup_preview(row["ra"] + tolerance * 1.001, row["dec"], None, "archive_unreachable") is None
        assert preview.lookup_preview(row["ra"], row["dec"] - tolerance * 1.001, None, "archive_unreachable") is None
    assert preview.lookup_preview(samples["wise_0855"]["ra"], samples["r_draconis"]["dec"], 1, "archive_unreachable") is None
    assert preview.lookup_preview(269.45208, 4.69339, None, "archive_unreachable") is None


def test_bundle_matches_pinned_spectra_and_every_native_map(samples):
    pins = {row["id"]: row for row in json.loads(preview.SOURCE_PINS.read_text(encoding="utf-8"))}
    for key, row in samples.items():
        assert row["source"] == pins[key]["source"]
        assert row["source"]["bytes"] == 320909760
        assert len(row["source"]["etag_md5"]) == 32
        assert preview.channel_digest(row["channels"]) == pins[key]["channels_sha256"]
        counts = Counter(item["status"] for item in row["channels"])
        assert tuple(counts[status] for status in ("measured", "no_coverage", "flagged", "blank_channel")) == EXPECTED[key]
        assert counts["missing_wavelength"] == 0
        for record in row["channels"]:
            window = row["maps"][str(record["channel"])]
            assert len(window["pixels"]) == 25 and {len(line) for line in window["pixels"]} == {25}
            assert (window["center_x"], window["center_y"]) == (12, 12)
            assert window["pixels"][12][12] == record["surface_brightness_mjy_sr"]
            if record["status"] == "blank_channel":
                assert all(value is None for line in window["pixels"] for value in line)


def test_refresh_refuses_bad_source_and_leaves_existing_artifact(tmp_path, samples):
    original = tmp_path / "preview.json.gz"
    original.write_bytes(b"previous preview")
    document = {"schema": 1, "generated_on": "2026-11-15", "samples": dict(samples)}
    document["samples"]["wise_0855"] = {**samples["wise_0855"], "tile": 7945}
    with pytest.raises(ValueError, match="provenance mismatch"):
        atomic_publish(document, original)
    assert original.read_bytes() == b"previous preview"
    assert list(tmp_path.glob("*.pending")) == []

    source = tmp_path / "test.fits"
    source.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_local(source, {"bytes": 7, "sha256": hashlib.sha256(b"science").hexdigest()})


def test_live_precedence_and_failure_boundaries(samples, monkeypatch):
    row = samples["wise_0855"]
    params = {"ra": row["ra"], "dec": row["dec"], "channel": 51}
    monkeypatch.setattr(cube, "load_cube_spectrum", lambda *_: {"tile": 9, "channels": []})
    with TestClient(app) as client:
        live = client.get("/api/cube/spectrum", params=params).json()
        assert live["source"] == "irsa_archive" and live["tile"] == 9 and "preview" not in live

        def archive_unreachable(*_):
            raise httpx.ConnectError("offline test")

        monkeypatch.setattr(cube, "load_cube_spectrum", archive_unreachable)
        cached = client.get("/api/cube/spectrum", params=params).json()
        assert cached["sample_kind"] == "coadded_dr1_sky_pixel"
        assert cached["observation_epoch"] is None and cached["source_association"] == "unconfirmed"
        assert cached["source"] == "cached_dr1_preview" and cached["tile"] == 10226
        assert cached["preview"]["archive_failure"] == "archive_unreachable"
        assert cached["channel_map"]["pixels"] == [[None] * 25 for _ in range(25)]
        assert client.get("/api/cube/spectrum", params={**params, "ra": 2}).status_code == 503

        def no_coverage(*_):
            raise CubeCoverageError("Position falls outside this HPX tile")

        monkeypatch.setattr(cube, "load_cube_spectrum", no_coverage)
        assert client.get("/api/cube/spectrum", params=params).status_code == 404

        def unreadable(*_):
            raise OSError("bad archive tile")

        monkeypatch.setattr(cube, "load_cube_spectrum", unreadable)
        assert client.get("/api/cube/spectrum", params=params).json()["preview"]["archive_failure"] == "archive_unreadable"
        assert client.get("/api/cube/spectrum", params={**params, "ra": 2}).status_code == 502


def test_invalid_local_preview_fails_closed(tmp_path, monkeypatch):
    path = tmp_path / "corrupt-preview.json.gz"
    path.write_bytes(b"not the validated artifact")
    monkeypatch.setattr(preview, "PREVIEW_FILE", path)

    def archive_unreachable(*_):
        raise httpx.ConnectError("offline test")

    monkeypatch.setattr(cube, "load_cube_spectrum", archive_unreachable)
    with TestClient(app) as client:
        response = client.get("/api/cube/spectrum", params={"ra": 133.75896227492004, "dec": -7.242116064321349})
    assert response.status_code == 503


def test_explicit_preview_channel_does_not_requery_archive(monkeypatch, samples):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("archive should not be queried for cached channel navigation")
    monkeypatch.setattr(cube, "load_cube_spectrum", fail_if_called)
    sample = samples["epsilon_indi_b"]
    result = cube.get_cube_spectrum(ra=sample["ra"], dec=sample["dec"], channel=75, source="preview_only")
    assert result["source"] == "cached_dr1_preview"
    assert result["channel_map"]["channel"] == 75
    assert result["preview"]["archive_failure"] == "cached_preview_requested"
