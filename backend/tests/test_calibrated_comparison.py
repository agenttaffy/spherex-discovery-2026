import io

import numpy as np
import pytest
from astropy.wcs import WCS
from astropy.io import fits
from fastapi.testclient import TestClient

from app.api import frames
from app.main import app
from app.science.calibrated_comparison import CalibratedExposure, compare_calibrated_pair, coadd_calibrated_exposures
from app.services.spectral_calibration_service import CalibrationArtifact


def exposure(value, variance, x_offset=0):
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [269.45, 4.69]
    wcs.wcs.crpix = [2 + x_offset, 2]
    wcs.wcs.cdelt = [-6.15 / 3600, 6.15 / 3600]
    shape = (3, 4)
    return CalibratedExposure(
        np.full(shape, value, dtype=float), np.full(shape, variance, dtype=float),
        np.zeros(shape, dtype=bool), np.full(shape, 1.3), np.full(shape, 0.03), wcs,
    )


def test_shifted_comparison_masks_shifted_pixel_and_propagates_variance():
    a = exposure(4, 2)
    b = exposure(10, 6, x_offset=1)
    b.bad[1, 1] = True
    b.variance[2, 2] = np.nan
    b.wavelength[0, 2] += 0.02
    result = compare_calibrated_pair(a, b, minimum_passband_overlap=0.9)
    valid = np.isfinite(result["difference"])
    assert result["retained_pixels"] == 6
    assert not valid[:, -1].any()
    assert not valid[1, 0]
    assert not valid[2, 1]
    assert not valid[0, 1]
    np.testing.assert_array_equal(result["difference"][valid], 6)
    np.testing.assert_array_equal(result["difference_variance"][valid], 8)
    np.testing.assert_array_equal(result["mean"][valid], 7)
    np.testing.assert_array_equal(result["mean_variance"][valid], 2)
    assert np.isnan(result["mean_variance"][~valid]).all()


@pytest.mark.parametrize("center_shift,width,offset,reason", [
    (0.02, 0.03, 0, "passband overlap"),
    (0, 0.05, 0, "passband overlap"),
    (0, 0.03, 10, "celestial pixel footprints"),
])
def test_pair_rejects_incompatible_passbands_and_disjoint_footprints(center_shift, width, offset, reason):
    a = exposure(4, 2)
    b = exposure(10, 6, x_offset=offset)
    b.wavelength += center_shift
    b.bandwidth[:] = width
    with pytest.raises(ValueError, match=reason):
        compare_calibrated_pair(a, b, minimum_passband_overlap=0.9)


def test_comparison_api_reports_variance_and_masks_then_rejects_wavelength_mismatch(monkeypatch):
    a, b = exposure(4, 2), exposure(10, 6)
    b.bad[0, 0] = True
    artifact = CalibrationArtifact("fixture", "https://example.test/calibration.fits", "0" * 32)
    cutouts = {}
    for index, (frame_id, product) in enumerate((("comparison-test-a", a), ("comparison-test-b", b))):
        header = fits.Header({
            "OBSID": frame_id, "DETECTOR": 6,
            "MJD-BEG": 60000 + index, "MJD-END": 60000.005 + index,
        })
        output = io.BytesIO()
        fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(product.image, header, name="IMAGE")]).writeto(output)
        monkeypatch.setitem(frames.OBSERVATION_REGISTRY, frame_id, {
            "obs_id": frame_id, "detector": "SPHEREx-D6",
            "collection": "spherex_dr1", "cached_cutout_url": frame_id,
        })
        cutouts[frame_id] = output.getvalue()

    first, second = "comparison-test-a", "comparison-test-b"
    products = {first: a, second: b}
    monkeypatch.setattr(frames.cache_service, "get", cutouts.get)
    monkeypatch.setattr(frames, "load_calibrated_exposure", lambda science, _: (
        products[science["IMAGE"].header["OBSID"]], artifact,
    ))
    with TestClient(app) as client:
        diff_request = {"frame_id_1": first, "frame_id_2": second}
        response = client.post("/api/frames/diff", json=diff_request)
        assert response.status_code == 200
        data = response.json()
        assert data["calibration"]["retained_pixels"] == 11
        assert data["variance_mjy_sr_squared"][0][:2] == [None, 8]
        assert data["surface_brightness_mjy_sr"][0][:2] == [None, 6]
        stack = client.post("/api/frames/stack", json={"frame_ids": [first, second]})
        assert stack.status_code == 200
        assert stack.json()["variance_mjy_sr_squared"][0][:2] == [None, 2]
        b.wavelength += 0.06
        rejected = client.post("/api/frames/diff", json=diff_request)
        assert rejected.status_code == 422
        assert "passband overlap" in rejected.json()["detail"]


def test_three_exposure_coadd_propagates_variance_and_rejects_bad_pixels():
    a, b, c = exposure(4, 2), exposure(10, 6), exposure(16, 10)
    c.bad[0, 0] = True
    result = coadd_calibrated_exposures([a, b, c], minimum_passband_overlap=0.9)
    valid = np.isfinite(result["mean"])
    assert result["retained_pixels"] == 11
    assert not valid[0, 0]
    np.testing.assert_allclose(result["mean"][valid], 10)
    np.testing.assert_allclose(result["mean_variance"][valid], 2)
    assert np.isnan(result["mean_variance"][0, 0])


def test_multi_exposure_requires_common_not_just_pairwise_passband():
    a, b, c = exposure(4, 2), exposure(10, 6), exposure(16, 10)
    b.wavelength -= 0.002
    c.wavelength += 0.002
    compare_calibrated_pair(a, b, minimum_passband_overlap=0.9)
    compare_calibrated_pair(a, c, minimum_passband_overlap=0.9)
    with pytest.raises(ValueError, match="common passband"):
        coadd_calibrated_exposures([a, b, c], minimum_passband_overlap=0.9)


def test_three_exposure_stack_endpoint_scales_sum_and_variance(monkeypatch):
    import asyncio
    a, b, c = exposure(4, 2), exposure(10, 6), exposure(16, 10)
    result = coadd_calibrated_exposures([a, b, c], minimum_passband_overlap=0.9)
    result["calibrations"] = []
    async def fake_compare(ids, fov):
        assert ids == ["a", "b", "c"]
        return result
    monkeypatch.setattr(frames, "_compare_selected", fake_compare)
    response = asyncio.run(frames.stack_frames(frames.StackRequest(frame_ids=["a", "b", "c"], method="sum")))
    assert response["frame_count"] == 3
    assert response["surface_brightness_mjy_sr"][0][0] == pytest.approx(30)
    assert response["variance_mjy_sr_squared"][0][0] == pytest.approx(18)
    with pytest.raises(frames.HTTPException, match="Median"):
        asyncio.run(frames.stack_frames(frames.StackRequest(frame_ids=["a", "b", "c"], method="median")))


def test_three_exposure_stack_validates_fits_metadata_and_rejects_time_overlap(monkeypatch):
    import asyncio
    products = {name: exposure(value, variance) for name, value, variance in [("m1", 4, 2), ("m2", 10, 6), ("m3", 16, 10)]}
    artifact = CalibrationArtifact("fixture", "https://example.test/calibration.fits", "0" * 32)
    cutouts = {}
    metadata = {}
    for index, (name, product) in enumerate(products.items()):
        header = fits.Header({"OBSID": name, "DETECTOR": 6, "MJD-BEG": 60000 + index, "MJD-END": 60000.1 + index})
        out = io.BytesIO()
        fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(product.image, header, name="IMAGE")]).writeto(out)
        cutouts[name] = out.getvalue()
        metadata[name] = {"obs_id": name, "detector": "SPHEREx-D6", "collection": "spherex_dr1", "cached_cutout_url": name}
        monkeypatch.setitem(frames.OBSERVATION_REGISTRY, name, metadata[name])
    monkeypatch.setattr(frames.cache_service, "get", cutouts.get)
    monkeypatch.setattr(frames, "load_calibrated_exposure", lambda science, _: (products[science["IMAGE"].header["OBSID"]], artifact))
    result = asyncio.run(frames.stack_frames(frames.StackRequest(frame_ids=list(products), method="mean")))
    assert result["frame_count"] == 3
    assert result["surface_brightness_mjy_sr"][0][0] == pytest.approx(10)
    assert len(result["calibration"]["calibrations"]) == 3
    with fits.open(io.BytesIO(cutouts["m3"])) as hdul:
        hdul["IMAGE"].header["MJD-BEG"] = 60001.05
        hdul["IMAGE"].header["MJD-END"] = 60001.15
        out = io.BytesIO()
        hdul.writeto(out)
        cutouts["m3"] = out.getvalue()
    with pytest.raises(frames.HTTPException) as exc:
        asyncio.run(frames.stack_frames(frames.StackRequest(frame_ids=list(products))))
    assert exc.value.status_code == 422
    assert "intervals overlap" in exc.value.detail
