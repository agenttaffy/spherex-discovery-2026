import numpy as np
import pytest
from astropy.io import fits
from fastapi.testclient import TestClient

from app.main import app
from app.science.photometry_evidence import inspect_photometry
from app.services.cutout_service import cutout_service
from app.services.irsa_client import OBSERVATION_REGISTRY


def exposure():
    image = fits.ImageHDU(np.ones((20, 20)), name="IMAGE")
    image.header["BUNIT"] = "MJy / sr"
    variance = fits.ImageHDU(np.ones((20, 20)), name="VARIANCE")
    variance.header["BUNIT"] = "MJy2 / sr2"
    flags = fits.ImageHDU(np.zeros((20, 20), dtype=np.int32), name="FLAGS")
    flags.header["MSKN0021"] = "SOURCE"
    flags.header["MSKM0021"] = 1 << 21
    flags.header["MSKN0001"] = "OVERFLOW"
    flags.header["MSKM0001"] = 2
    return fits.HDUList([fits.PrimaryHDU(), image, variance, flags])


def position(x=9.25, y=9.7):
    return {"pixel": {"x": x, "y": y, "inside": 0 <= x < 19.5 and 0 <= y < 19.5}}


def test_clean_no_source_control_never_returns_a_target_flux():
    result = inspect_photometry(exposure(), position())
    assert result.status == "unavailable"
    assert result.aperture_status == "field_sample_only"
    assert "no source detection or target flux" in result.reason
    assert "flux" not in result.model_dump()
    assert result.usable_core_pixels == result.core_pixels
    assert result.background_pixels > 0


def test_archive_outage_does_not_create_synthetic_frame(monkeypatch):
    frame_id = "synthetic_evidence_test"
    monkeypatch.setitem(OBSERVATION_REGISTRY, frame_id, {
        "obs_id": frame_id, "collection": "spherex_dr1", "detector": "SPHEREx-D6",
        "utc_date": "2025-05-01T00:00:00", "access_url": "https://example.invalid/test.fits",
        "ra": 269.44635, "dec": 4.76712,
    })

    async def unavailable(*args, **kwargs):
        raise RuntimeError("Test archive outage")

    monkeypatch.setattr(cutout_service, "fetch_cutout_with_source", unavailable)
    response = TestClient(app).get(f"/api/frames/{frame_id}")
    assert response.status_code == 422
    assert "could not deliver" in response.json()["detail"]


@pytest.mark.parametrize("mask", ["overflow", "unknown_flag", "zero_variance", "nonfinite_variance"])
def test_central_flag_or_invalid_variance_remains_unusable(mask):
    hdul = exposure()
    if mask == "overflow":
        hdul["FLAGS"].data[10, 9] = 2
    elif mask == "unknown_flag":
        hdul["FLAGS"].data[10, 9] = 1 << 28
    else:
        hdul["VARIANCE"].data[10, 9] = 0 if mask == "zero_variance" else np.nan
    result = inspect_photometry(hdul, position())
    assert result.usable_core_pixels == result.core_pixels - 1
    assert result.aperture_status == "unavailable"


def test_source_bit_excludes_neighbors_from_background_without_claiming_identity():
    hdul = exposure()
    yy, xx = np.indices((20, 20))
    radius = np.hypot(xx - 9.25, yy - 9.7)
    hdul["FLAGS"].data[radius > 4] = 1 << 21
    hdul["FLAGS"].data[10, 9] = 1 << 21
    result = inspect_photometry(hdul, position())
    assert result.usable_core_pixels == result.core_pixels
    assert result.background_pixels == 0
    assert result.aperture_status == "unavailable"
    assert "background annulus" in result.reason


@pytest.mark.parametrize("x, reason", [(1.25, "clipped"), (4.25, "annulus crosses"), (-1, "outside")])
def test_subpixel_aperture_and_annulus_edge_guards(x, reason):
    result = inspect_photometry(exposure(), position(x=x))
    assert result.status == "unavailable"
    assert reason in result.reason


def test_all_bad_core_and_missing_products_are_explicit():
    hdul = exposure()
    hdul["VARIANCE"].data[:] = 0
    result = inspect_photometry(hdul, position())
    assert result.usable_core_pixels == 0
    assert "No unmasked core" in result.reason
    del hdul["VARIANCE"]
    assert "variance plane" in inspect_photometry(hdul, position()).reason
