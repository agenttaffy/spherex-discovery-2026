import numpy as np
import pytest
from astropy.wcs import WCS
from fastapi.testclient import TestClient
from app.main import app
from app.science.stacking import compute_coadd_stack
from app.science.spectrum import generate_spectrum_for_target, SPHEREX_DETECTOR_CONFIG
from app.services.demo_service import demo_service

client = TestClient(app)

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

def test_spectrum_generation_102_channels():
    # Test SED builder directly with synthetic observation
    ra, dec = 269.45208, 4.69339
    recs = demo_service.find_matching_observations(ra, dec, radius_deg=0.1)
    res = generate_spectrum_for_target(ra, dec, recs, None)
    
    assert res["target"]["ra"] == pytest.approx(ra, rel=1e-4)
    assert len(res["bands"]) == 6
    assert len(res["channels_102"]) == 102
    assert len(res["continuum_curve"]) > 10
    
    # Check that channel indices are 1 through 102 sequentially
    indices = [ch["channel_index"] for ch in res["channels_102"]]
    assert indices == list(range(1, 103))

    # Check that each detector has 17 channels
    from collections import Counter
    det_counts = Counter(ch["detector"] for ch in res["channels_102"])
    for cfg in SPHEREX_DETECTOR_CONFIG:
        assert det_counts[cfg["detector"]] == 17

def test_spectrum_endpoint_barnard():
    resp = client.get("/api/science/spectrum?ra=269.45208&dec=4.69339&fov=0.04")
    assert resp.status_code == 200
    data = resp.json()
    assert "target" in data
    assert len(data["bands"]) == 6
    assert len(data["channels_102"]) == 102
    assert "spectral_class" in data["summary"]
    assert data["summary"]["total_channels"] == 102
    assert data["total_observed_bands"] >= 1

def test_spectrum_endpoint_wise0855_brown_dwarf():
    resp = client.get("/api/science/spectrum?ra=133.79513&dec=-7.24515&fov=0.04")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["bands"]) == 6
    assert len(data["channels_102"]) == 102
    # Cold brown dwarf should peak at longer mid-IR wavelengths (D5 or D6, > 4.0 µm)
    assert data["summary"]["peak_wavelength_um"] >= 4.0
    assert "Brown Dwarf" in data["summary"]["spectral_class"]

def test_spectrum_endpoint_sexagesimal():
    resp = client.get("/api/science/spectrum?ra=17h57m48.5s&dec=+04d41m36s")
    assert resp.status_code == 200
    data = resp.json()
    assert abs(data["target"]["ra"] - 269.452) < 0.01

def test_spectrum_endpoint_invalid_coords():
    resp = client.get("/api/science/spectrum?ra=100.0&dec=95.0")
    assert resp.status_code == 400

def test_stack_frames_endpoint_on_demo_epochs():
    barnard_recs = demo_service.find_matching_observations(269.45208, 4.69339, radius_deg=0.1)
    d3_recs = [r for r in barnard_recs if "D3" in r.detector]
    assert len(d3_recs) >= 2

    resp = client.post("/api/frames/stack", json={
        "frame_ids": [d3_recs[0].id, d3_recs[1].id],
        "method": "mean",
        "format": "png",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["frame_count"] == 2
    assert data["theoretical_snr_gain"] == pytest.approx(1.414, rel=1e-2)
    assert "image_base64" in data
    assert data["image_base64"].startswith("data:image/png;base64,")
    assert "noise_stats" in data

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

def test_stack_frames_endpoint_webp_and_median():
    barnard_recs = demo_service.find_matching_observations(269.45208, 4.69339, radius_deg=0.1)
    d3_recs = [r for r in barnard_recs if "D3" in r.detector]
    assert len(d3_recs) >= 2

    resp = client.post("/api/frames/stack", json={
        "frame_ids": [d3_recs[0].id, d3_recs[1].id],
        "method": "median",
        "format": "webp",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["method"] == "median"
    assert data["image_base64"].startswith("data:image/webp;base64,")

def test_compute_coadd_stack_edge_cases():
    with pytest.raises(ValueError, match="Cannot stack an empty list"):
        compute_coadd_stack([])

    img1 = np.ones((10, 10), dtype=np.float32) * 4.0
    single_res, stats = compute_coadd_stack([img1])
    assert stats["frame_count"] == 1
    assert stats["snr_improvement_factor"] == 1.0

