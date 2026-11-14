import numpy as np
from app.science.comparison import check_comparison_eligibility, compute_difference_frame

def test_comparison_eligibility():
    meta1 = {"detector": "SPHEREx-D1", "ra": 100.0, "dec": 20.0, "mjd": 60000.0}
    meta2 = {"detector": "SPHEREx-D1", "ra": 100.01, "dec": 20.01, "mjd": 60100.0}
    eligible, reason = check_comparison_eligibility(meta1, meta2)
    assert eligible is True

    # Incompatible detector
    meta_diff_det = {"detector": "SPHEREx-D4", "ra": 100.0, "dec": 20.0, "mjd": 60100.0}
    eligible_det, reason_det = check_comparison_eligibility(meta1, meta_diff_det)
    assert eligible_det is False
    assert "Incompatible detectors" in reason_det

def test_compute_difference_frame():
    i1 = np.ones((20, 20), dtype=np.float32) * 5.0
    i2 = np.ones((20, 20), dtype=np.float32) * 5.0
    # Add a transient source in frame 2
    i2[10, 10] = 25.0

    diff_u8, stats = compute_difference_frame(i1, i2)
    assert diff_u8.shape == (20, 20)
    assert stats["peak_positive_flux"] == 20.0
    assert stats["peak_negative_flux"] == 0.0
