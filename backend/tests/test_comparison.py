import numpy as np
from astropy.wcs import WCS
from app.science.comparison import check_comparison_eligibility, compute_difference_frame

def test_comparison_eligibility():
    meta1 = {"id": "f1", "detector": "SPHEREx-D1", "ra": 100.0, "dec": 20.0, "mjd": 60000.0}
    meta2 = {"id": "f2", "detector": "SPHEREx-D1", "ra": 100.01, "dec": 20.01, "mjd": 60100.0}
    eligible, reason = check_comparison_eligibility(meta1, meta2)
    assert eligible is True

    # Incompatible detector
    meta_diff_det = {"id": "f3", "detector": "SPHEREx-D4", "ra": 100.0, "dec": 20.0, "mjd": 60100.0}
    eligible_det, reason_det = check_comparison_eligibility(meta1, meta_diff_det)
    assert eligible_det is False
    assert "Incompatible detectors" in reason_det

    # Same frame
    eligible_same, reason_same = check_comparison_eligibility(meta1, meta1)
    assert eligible_same is False
    assert "Cannot compare" in reason_same

def test_comparison_ra_boundary_wrapping():
    # 0.01 deg and 359.99 deg are separated by only 0.02 deg
    meta1 = {"id": "f1", "detector": "SPHEREx-D1", "ra": 0.01, "dec": 10.0, "mjd": 60000.0}
    meta2 = {"id": "f2", "detector": "SPHEREx-D1", "ra": 359.99, "dec": 10.0, "mjd": 60100.0}
    eligible, reason = check_comparison_eligibility(meta1, meta2)
    assert eligible is True
    assert reason == "Eligible for comparison."

def test_compute_difference_frame():
    i1 = np.ones((20, 20), dtype=np.float32) * 5.0
    i2 = np.ones((20, 20), dtype=np.float32) * 5.0
    # Add a transient source in frame 2
    i2[10, 10] = 25.0

    diff_u8, stats = compute_difference_frame(i1, i2)
    assert diff_u8.shape == (20, 20)
    assert stats["peak_positive_flux"] == 20.0
    assert stats["peak_negative_flux"] == 0.0

def test_compute_difference_frame_nan_handling():
    i1 = np.ones((20, 20), dtype=np.float32) * 5.0
    i1[5, 5] = np.nan
    i2 = np.ones((20, 20), dtype=np.float32) * 5.0
    i2[10, 10] = 15.0

    diff_u8, stats = compute_difference_frame(i1, i2)
    assert diff_u8.shape == (20, 20)
    assert not np.isnan(stats["rms_diff_mjy_sr"])
    assert stats["peak_positive_flux"] == 10.0
    assert diff_u8[5, 5] == 128  # masked to mid-gray

def test_compute_difference_frame_wcs_reproject():
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
    i2[10, 10] = 25.0

    diff_u8, stats = compute_difference_frame(i1, i2, wcs1=w1, wcs2=w2)
    assert diff_u8.shape == (20, 20)
    assert stats["alignment_method"] == "wcs_reproject"

def test_compute_difference_frame_fft_shift_fallback():
    # Two images with a distinct Gaussian feature shifted by 2 pixels, without WCS
    y, x = np.mgrid[0:30, 0:30]
    i1 = 5.0 + 20.0 * np.exp(-((x - 15)**2 + (y - 15)**2) / 8.0).astype(np.float32)
    i2 = 5.0 + 20.0 * np.exp(-((x - 17)**2 + (y - 15)**2) / 8.0).astype(np.float32)

    diff_u8, stats = compute_difference_frame(i1, i2, wcs1=None, wcs2=None)
    assert diff_u8.shape == (30, 30)
    assert stats["alignment_method"] == "fft_shift"

def test_compute_difference_frame_spectral_3d_wcs():
    # 3D WCS with RA, Dec, and Spectral Wave channel
    w1 = WCS(naxis=3)
    w1.wcs.ctype = ['RA---TAN', 'DEC--TAN', 'WAVE']
    w1.wcs.crval = [100.0, 20.0, 1.5]
    w1.wcs.cdelt = [-0.01, 0.01, 0.1]
    w1.wcs.crpix = [10.0, 10.0, 1.0]

    w2 = WCS(naxis=3)
    w2.wcs.ctype = ['RA---TAN', 'DEC--TAN', 'WAVE']
    w2.wcs.crval = [100.0, 20.0, 1.5]
    w2.wcs.cdelt = [-0.01, 0.01, 0.1]
    w2.wcs.crpix = [11.0, 10.0, 1.0]

    i1 = np.ones((20, 20), dtype=np.float32) * 5.0
    i2 = np.ones((20, 20), dtype=np.float32) * 5.0
    i2[10, 10] = 30.0

    diff_u8, stats = compute_difference_frame(i1, i2, wcs1=w1, wcs2=w2)
    assert diff_u8.shape == (20, 20)
    assert stats["alignment_method"] == "wcs_reproject"

def test_compute_difference_frame_rotated_wcs():
    # Target image
    w1 = WCS(naxis=2)
    w1.wcs.crpix = [10.0, 10.0]
    w1.wcs.cdelt = [-0.001, 0.001]
    w1.wcs.crval = [150.0, 2.0]
    w1.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    # 90 degree rotated image
    w2 = WCS(naxis=2)
    w2.wcs.crpix = [10.0, 10.0]
    w2.wcs.pc = [[0, -1], [1, 0]]
    w2.wcs.cdelt = [-0.001, 0.001]
    w2.wcs.crval = [150.0, 2.0]
    w2.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    img1 = np.zeros((20, 20), dtype=np.float32)
    img1[10, 12] = 50.0

    sky_coord = w1.pixel_to_world(12, 10)
    px2, py2 = w2.world_to_pixel(sky_coord)
    img2 = np.zeros((20, 20), dtype=np.float32)
    img2[int(round(float(py2))), int(round(float(px2)))] = 50.0

    diff_u8, stats = compute_difference_frame(img1, img2, wcs1=w1, wcs2=w2)
    assert diff_u8.shape == (20, 20)
    assert stats["alignment_method"] == "wcs_reproject"
    assert stats["rms_diff_mjy_sr"] < 0.1

