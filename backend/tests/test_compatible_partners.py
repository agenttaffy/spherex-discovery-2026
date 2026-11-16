import io
from unittest.mock import patch

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from fastapi.testclient import TestClient

from app.api import frames
from app.main import app
from app.science.calibrated_comparison import CalibratedExposure


def exposure(wavelength):
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [3, 3]
    wcs.wcs.cdelt = [-.001, .001]
    wcs.wcs.crval = [1, 2]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    ones = np.ones((5, 5))
    return CalibratedExposure(ones, ones, np.zeros((5, 5), dtype=bool), ones * wavelength, ones * .1, wcs)


def test_scanner_filters_and_counts_without_network(monkeypatch):
    registry = {
        "ref": {"detector": "SPHEREx-D1", "ra": 1, "dec": 2},
        "good": {"detector": "SPHEREx-D1", "ra": 1, "dec": 2},
        "different_wave": {"detector": "SPHEREx-D1", "ra": 1, "dec": 2},
        "missing": {"detector": "SPHEREx-D1", "ra": 1, "dec": 2},
        "other_center": {"detector": "SPHEREx-D1", "ra": 1.1, "dec": 2},
        "other_detector": {"detector": "SPHEREx-D2", "ra": 1, "dec": 2},
    }
    monkeypatch.setattr(frames, "OBSERVATION_REGISTRY", registry)
    names = {id(value): key for key, value in registry.items()}
    monkeypatch.setattr(frames, "_cached_partner_cutout", lambda meta, fov: None if names[id(meta)] == "missing" else names[id(meta)].encode())
    def prepare(data, meta):
        name = data.decode()
        return exposure(2 if name == "different_wave" else 1), ((1, 2) if name == "ref" else (3, 4)), name
    monkeypatch.setattr(frames, "_prepare_cached_partner", prepare)
    with patch.object(frames.cutout_service, "fetch_cutout_fits", side_effect=AssertionError("network forbidden")), \
         patch.object(frames, "load_calibrated_exposure", side_effect=AssertionError("network forbidden")):
        result = frames._scan_cached_partners("ref", ["good", "different_wave", "missing", "other_center", "other_detector"], .04)
    assert result["checked"] == 2 and result["unavailable"] == 1
    assert len(result["matches"]) == 1 and result["matches"][0]["frame_id"] == "good"
    assert result["matches"][0]["retained_pixels"] == 25


def test_cached_preparation_rejects_wrong_identity_and_bad_exposure_time(monkeypatch):
    image = fits.ImageHDU(np.ones((5, 5)), name="IMAGE")
    image.header["OBSID"] = "expected"
    image.header["DETECTOR"] = 1
    image.header["MJD-BEG"] = 60000
    image.header["MJD-END"] = 60001
    stream = io.BytesIO()
    fits.HDUList([fits.PrimaryHDU(), image]).writeto(stream)
    monkeypatch.setattr(frames, "load_cached_calibrated_exposure", lambda *args: (exposure(1), None))
    meta = {"obs_id": "expected", "detector": "SPHEREx-D1", "collection": "spherex_dr1"}
    _, interval, name = frames._prepare_cached_partner(stream.getvalue(), meta)
    assert interval == (60000, 60001) and name == "expected"
    try:
        frames._prepare_cached_partner(stream.getvalue(), {**meta, "obs_id": "wrong"})
        assert False, "mismatched FITS identity must fail"
    except ValueError:
        pass


def test_endpoint_rejects_more_than_twelve_candidates():
    with TestClient(app) as client:
        response = client.post("/api/frames/compatible-partners", json={"frame_id": "x", "candidate_ids": [str(i) for i in range(13)], "fov": .04})
    assert response.status_code == 422


def test_reference_not_cached_reports_candidates_unavailable(monkeypatch):
    registry = {"ref": {"detector": "SPHEREx-D1", "ra": 1, "dec": 2},
                "candidate": {"detector": "SPHEREx-D1", "ra": 1, "dec": 2}}
    monkeypatch.setattr(frames, "OBSERVATION_REGISTRY", registry)
    monkeypatch.setattr(frames, "_cached_partner_cutout", lambda *args: None)
    result = frames._scan_cached_partners("ref", ["candidate"], .04)
    assert result == {"checked": 0, "unavailable": 1, "matches": []}
