import numpy as np
import pytest
from astropy.wcs import WCS
from fastapi.testclient import TestClient
from app.main import app
from app.science.stacking import compute_coadd_stack
from app.science.spectrum import generate_spectrum_for_target, SPHEREX_DETECTOR_CONFIG
from app.services.demo_service import demo_service

client = TestClient(app)


@pytest.fixture
def cached_stack_fixtures(monkeypatch):
    """Two independent synthetic exposures, with all network access forbidden."""
    import io
    from unittest.mock import AsyncMock, Mock
    from astropy.io import fits
    from app.api import frames
    from app.science.calibrated_comparison import CalibratedExposure
    from app.services.cache_service import cache_service

    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [269.45208, 4.69339]
    wcs.wcs.crpix = [3, 3]
    wcs.wcs.cdelt = [-6.2 / 3600, 6.2 / 3600]
    cutouts, exposures = {}, {}
    ids = ["stack-fixture-a", "stack-fixture-b"]
    for index, frame_id in enumerate(ids):
        pixels = np.full((5, 5), 3.0 + 2 * index)
        header = wcs.to_header()
        header["OBSID"], header["DETECTOR"] = frame_id, 3
        header["MJD-BEG"], header["MJD-END"] = 60000.0 + index, 60000.01 + index
        out = io.BytesIO()
        fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(pixels, header=header, name="IMAGE")]).writeto(out)
        cutouts[frame_id] = out.getvalue()
        exposures[frame_id] = CalibratedExposure(pixels, np.full_like(pixels, 4.0 + 4 * index),
            np.zeros_like(pixels, dtype=bool), np.full_like(pixels, 1.7), np.full_like(pixels, .03), wcs)
        monkeypatch.setitem(frames.OBSERVATION_REGISTRY, frame_id, {
            "obs_id": frame_id, "detector": "SPHEREx-D3", "collection": "spherex_dr1",
            "cached_cutout_url": frame_id,
        })
    monkeypatch.setattr(cache_service, "get", lambda key: cutouts.get(key))
    monkeypatch.setattr("app.services.cutout_service.cloud_cutout", Mock(side_effect=AssertionError("unexpected cloud request")))
    monkeypatch.setattr("httpx.AsyncClient.get", AsyncMock(side_effect=AssertionError("unexpected IRSA request")))
    return ids, exposures

def test_compute_coadd_stack_mean_median_sum():
    # 3 frames, base flux 10.0
    img1 = np.ones((16, 16), dtype=np.float32) * 10.0
    img2 = np.ones((16, 16), dtype=np.float32) * 10.0
    img3 = np.ones((16, 16), dtype=np.float32) * 10.0
    # Add an outlier cosmic ray in frame 2
    img2[8, 8] = 999.0

    # Median stack should reject the cosmic ray
    stacked_med, stats_med = compute_coadd_stack([img1, img2, img3], method="median")
    assert stacked_med.shape == (16, 16)
    assert abs(stacked_med[8, 8] - 10.0) < 1e-3
    assert stats_med["frame_count"] == 3
    assert stats_med["theoretical_snr_gain"] == pytest.approx(np.sqrt(3), rel=1e-2)

    # Mean stack should average the cosmic ray
    stacked_mean, stats_mean = compute_coadd_stack([img1, img2, img3], method="mean")
    assert stacked_mean[8, 8] > 300.0
    assert stats_mean["frame_count"] == 3

    # Sum stack should sum the frames
    img_clean2 = np.ones((16, 16), dtype=np.float32) * 10.0
    stacked_sum, stats_sum = compute_coadd_stack([img1, img_clean2, img3], method="sum")
    assert abs(stacked_sum[0, 0] - 30.0) < 1e-3
    assert stats_sum["theoretical_snr_gain"] == pytest.approx(np.sqrt(3), rel=1e-2)

def test_compute_coadd_stack_nan_handling():
    img1 = np.ones((10, 10), dtype=np.float32) * 5.0
    img2 = np.ones((10, 10), dtype=np.float32) * 5.0
    img1[3, 3] = np.nan
    img2[7, 7] = np.nan

    stacked, stats = compute_coadd_stack([img1, img2], method="mean")
    assert np.all(np.isfinite(stacked))
    assert abs(stacked[3, 3] - 5.0) < 1e-3
    assert abs(stacked[7, 7] - 5.0) < 1e-3
    assert stats["frame_count"] == 2

def test_compute_coadd_stack_wcs_reproject():
    w1 = WCS(naxis=2)
    w1.wcs.crpix = [10.0, 10.0]
    w1.wcs.cdelt = [-0.01, 0.01]
    w1.wcs.crval = [100.0, 20.0]
    w1.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    w2 = WCS(naxis=2)
    w2.wcs.crpix = [11.0, 10.0]
    w2.wcs.cdelt = [-0.01, 0.01]
    w2.wcs.crval = [100.0, 20.0]
    w2.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    i1 = np.ones((20, 20), dtype=np.float32) * 5.0
    i2 = np.ones((20, 20), dtype=np.float32) * 5.0
    i2[10, 10] = 20.0

    stacked, stats = compute_coadd_stack([i1, i2], wcs_list=[w1, w2], method="mean")
    assert stacked.shape == (20, 20)
    assert stats["alignment_method"] == "wcs_reproject"
    assert stats["frame_count"] == 2

def test_spectrum_without_measurements_has_no_synthetic_values():
    res = generate_spectrum_for_target(269.45208, 4.69339, [], None)
    assert res["total_observed_bands"] == 0
    assert res["bands"] == []
    assert res["channels_102"] == []
    assert res["continuum_curve"] == []
    assert res["summary"]["integrated_flux_mjy_sr_um"] is None

def test_spectrum_endpoint_barnard():
    resp = client.get("/api/science/spectrum?ra=269.45208&dec=4.69339&fov=0.04")
    assert resp.status_code == 200
    data = resp.json()
    assert "target" in data
    assert len(data["bands"]) == data["total_observed_bands"]
    assert data["channels_102"] == []
    assert "continuum_shape" in data["summary"]
    assert "spectral_class" not in data["summary"]
    assert data["summary"]["total_channels"] == 0
    assert data["total_observed_bands"] == len(data["observed_detector_bands"])
    if data["total_observed_bands"] == 0:
        assert data["summary"]["peak_wavelength_um"] is None

def test_spectrum_endpoint_wise0855_brown_dwarf():
    resp = client.get("/api/science/spectrum?ra=133.79513&dec=-7.24515&fov=0.04")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["bands"]) == data["total_observed_bands"]
    assert data["channels_102"] == []
    # A target name cannot guarantee a measurement or spectral classification.
    if data["total_observed_bands"] == 0:
        assert data["summary"]["peak_wavelength_um"] is None
    assert "Brown Dwarf" not in data["summary"]["continuum_shape"]

def test_spectrum_endpoint_sexagesimal():
    resp = client.get("/api/science/spectrum?ra=17h57m48.5s&dec=+04d41m36s")
    assert resp.status_code == 200
    data = resp.json()
    assert abs(data["target"]["ra"] - 269.452) < 0.01

def test_spectrum_endpoint_invalid_coords():
    resp = client.get("/api/science/spectrum?ra=100.0&dec=95.0")
    assert resp.status_code == 400

def test_stack_frames_endpoint_rejects_unverified_fixture_calibration(cached_stack_fixtures):
    ids, _ = cached_stack_fixtures
    resp = client.post("/api/frames/stack", json={
        "frame_ids": ids,
        "method": "mean",
        "format": "png",
    })
    assert resp.status_code == 422
    assert "per-pixel wavelength compatibility" in resp.json()["detail"]
    assert "Exactly one spectral calibration ID" in resp.json()["detail"]

def test_stack_frames_endpoint_validation():
    # Empty list -> 400
    resp_empty = client.post("/api/frames/stack", json={"frame_ids": []})
    assert resp_empty.status_code == 400

    # Only 1 frame provided -> 400
    resp = client.post("/api/frames/stack", json={
        "frame_ids": ["single_frame"],
        "method": "mean",
    })
    assert resp.status_code == 400

    # Non-existent frame -> 404
    resp = client.post("/api/frames/stack", json={
        "frame_ids": ["non_existent_1", "non_existent_2"],
        "method": "mean",
    })
    assert resp.status_code == 404

def test_stack_frames_endpoint_webp_and_median(cached_stack_fixtures, monkeypatch):
    import base64
    import io
    from PIL import Image
    from app.api import frames
    from app.services.spectral_calibration_service import CalibrationArtifact
    ids, exposures = cached_stack_fixtures
    artifact = CalibrationArtifact("fixture", "https://example.invalid/calibration.fits", "0" * 32)
    monkeypatch.setattr(frames, "load_calibrated_exposure", lambda science, release: (
        exposures[science["IMAGE"].header["OBSID"]], artifact,
    ))
    resp = client.post("/api/frames/stack", json={
        "frame_ids": ids,
        "method": "median",
        "format": "webp",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["method"] == "median" and data["calibration"]["retained_pixels"] == 25
    np.testing.assert_allclose(data["surface_brightness_mjy_sr"], np.full((5, 5), 4.0))
    np.testing.assert_allclose(data["variance_mjy_sr_squared"], np.full((5, 5), 3.0))
    raw = base64.b64decode(data["image_base64"].split(",", 1)[1], validate=True)
    with Image.open(io.BytesIO(raw)) as image:
        assert image.format == "WEBP" and image.size == (5, 5)

def test_compute_coadd_stack_edge_cases():
    with pytest.raises(ValueError, match="Cannot stack an empty list"):
        compute_coadd_stack([])

    img1 = np.ones((10, 10), dtype=np.float32) * 4.0
    single_res, stats = compute_coadd_stack([img1])
    assert stats["frame_count"] == 1
    assert stats["snr_improvement_factor"] == 1.0

def test_stack_frames_endpoint_duplicate_frames_rejected():
    barnard_recs = demo_service.find_matching_observations(269.45208, 4.69339, radius_deg=0.1)
    fid = barnard_recs[0].id
    resp = client.post("/api/frames/stack", json={
        "frame_ids": [fid, fid],
        "method": "mean",
    })
    assert resp.status_code == 400
    assert "At least 2 distinct frame IDs" in resp.json()["detail"]

def test_compute_coadd_stack_non_overlapping_wcs_raises():
    w1 = WCS(naxis=2)
    w1.wcs.crpix = [10.0, 10.0]
    w1.wcs.cdelt = [-0.01, 0.01]
    w1.wcs.crval = [10.0, 10.0]
    w1.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    w2 = WCS(naxis=2)
    w2.wcs.crpix = [10.0, 10.0]
    w2.wcs.cdelt = [-0.01, 0.01]
    w2.wcs.crval = [60.0, 60.0]  # 70+ degrees away
    w2.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    i1 = np.ones((20, 20), dtype=np.float32)
    i2 = np.ones((20, 20), dtype=np.float32)

    with pytest.raises(ValueError, match="no overlapping celestial sky coverage"):
        compute_coadd_stack([i1, i2], wcs_list=[w1, w2], method="mean")

def test_stack_frames_endpoint_distant_pointings_rejected():
    barnard_recs = demo_service.find_matching_observations(269.45208, 4.69339, radius_deg=0.1)
    wise_recs = demo_service.find_matching_observations(133.79513, -7.24515, radius_deg=0.1)
    assert len(barnard_recs) >= 1 and len(wise_recs) >= 1

    resp = client.post("/api/frames/stack", json={
        "frame_ids": [barnard_recs[0].id, wise_recs[0].id],
        "method": "mean",
    })
    assert resp.status_code == 400
    assert "too far from reference frame" in resp.json()["detail"]

def test_spectrum_endpoint_fov_validation():
    # Negative FOV
    resp_neg = client.get("/api/science/spectrum?ra=269.45208&dec=4.69339&fov=-0.05")
    assert resp_neg.status_code == 400
    assert "FOV must be between" in resp_neg.json()["detail"]

    # Excessive FOV (>2.0 deg)
    resp_huge = client.get("/api/science/spectrum?ra=269.45208&dec=4.69339&fov=5.0")
    assert resp_huge.status_code == 400

def test_robust_noise_sigma_point_source_insensitivity():
    np.random.seed(42)
    # Background Gaussian noise sigma = 0.5
    bg1 = np.random.normal(0, 0.5, (40, 40)).astype(np.float32)
    bg2 = np.random.normal(0, 0.5, (40, 40)).astype(np.float32)
    # Add huge 500 MJy/sr point source at center
    bg1[20, 20] += 500.0
    bg2[20, 20] += 500.0

    stacked, stats = compute_coadd_stack([bg1, bg2], method="mean")
    # Robust noise estimation should measure the true ~0.5 / ~0.35 background, NOT 500 MJy!
    assert stats["reference_noise_sigma"] < 1.0
    assert stats["stacked_noise_sigma"] < stats["reference_noise_sigma"]
    # Gain should be approximately sqrt(2) ~ 1.41
    assert stats["snr_improvement_factor"] >= 1.2


