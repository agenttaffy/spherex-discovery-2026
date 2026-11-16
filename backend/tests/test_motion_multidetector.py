import sys
from pathlib import Path

import numpy as np
import pytest
from astropy.coordinates import SkyCoord

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import study_motion_multidetector as study


def test_polygon_rank_handles_ra_wrap_and_rejects_outside_sources():
    region = "POLYGON ICRS 359 -1 1 -1 1 1 359 1 359 -1"
    assert study.footprint_coordinates(region, 0, 0) == pytest.approx([.5, .5])
    assert study.footprint_coordinates(region, 4, 0) is None


def test_selection_uses_one_detector_and_distinct_exposures(monkeypatch):
    monkeypatch.setattr(study, "apparent_position", lambda target, time, cat:
                        SkyCoord(np.full(len(time), 10), np.zeros(len(time)), unit="deg"))
    region = "POLYGON ICRS 9 -1 11 -1 11 1 9 1 9 -1"
    rows = [dict(obs_id=oid, t_min=mjd, t_max=mjd, s_region=region,
                 energy_bandpassname=f"SPHEREx-D{detector}")
            for oid, mjd, detector in [("a", 60900, 1), ("short", 60950, 1), ("b", 61265, 1), ("c", 61265, 2)]]
    queries = [dict(target="wise_0855", release="spherex_dr1", rows=rows),
               dict(target="wise_0855", release="spherex_qr3", rows=[rows[0]])]
    selected, eligible = study.select_pairs(queries, {})
    assert len(selected) == len(eligible) == 1
    assert selected[0]["detector"] == "SPHEREx-D1"
    assert [ep["obs_id"] for ep in selected[0]["endpoints"]] == ["a", "b"]


def test_catalog_artifact_requires_exact_plane_and_detector(tmp_path):
    art = tmp_path / "spectral-artifacts.csv"
    art.write_text("planeid,uri,contentchecksum\n"
                   "p,ibe/data/spherex/dr1/spectral_wcs/v5/3/example.fits,md5:" + "a" * 32 + "\n")
    record = dict(plane_id="p", detector="SPHEREx-D3", release="spherex_qr3")
    assert study.calibration_from_catalog(art, record)["checksum"] == "a" * 32
    assert study.calibration_from_catalog(art, dict(record, detector="SPHEREx-D4")) is None
    assert study.calibration_from_catalog(art, dict(record, plane_id="other")) is None


def test_clean_core_does_not_override_missing_calibration():
    a = dict(observation="a", core=[19, 19], core_contained=True, mjd=61000, predicted_deg=[10, 0])
    b = dict(a, observation="b", mjd=61365, calibration_error="archive lookup failed")
    result = study.evaluate((a, None), (b, None))
    assert result["baseline_days"] == 365
    assert result["source_core_overlap"] is None
    assert result["rejection_reasons"] == ["release/detector spectral calibration unverified"]
    assert not result["validated_motion"]
