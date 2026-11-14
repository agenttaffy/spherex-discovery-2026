import numpy as np
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
