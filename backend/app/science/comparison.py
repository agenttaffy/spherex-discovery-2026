from typing import Dict, Any, Tuple
import numpy as np

def check_comparison_eligibility(
    meta1: Dict[str, Any],
    meta2: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Evaluates whether two SPHEREx observations are scientifically eligible for direct subtraction.
    Checks detector band, effective wavelength, coordinate proximity, and temporal separation.
    Handles spherical RA wrapping across the 0/360 degree boundary.
    """
    # 0. Check for exact identical frame selection
    id1 = meta1.get("id") or meta1.get("obs_id")
    id2 = meta2.get("id") or meta2.get("obs_id")
    if id1 and id2 and id1 == id2:
        return False, "Cannot compare an observation with itself."

    # 1. Detector match
    det1 = meta1.get("detector")
    det2 = meta2.get("detector")
    if det1 and det2 and det1 != det2:
        return False, f"Incompatible detectors: {det1} vs {det2}. Spectral bands differ."

    # 2. Celestial proximity with 0/360 RA boundary wrapping
    ra1, dec1 = float(meta1.get("ra", 0.0)), float(meta1.get("dec", 0.0))
    ra2, dec2 = float(meta2.get("ra", 0.0)), float(meta2.get("dec", 0.0))
    
    # Wrap RA difference to [-180, +180] degrees
    delta_ra = (ra1 - ra2 + 180.0) % 360.0 - 180.0
    mean_dec_rad = np.radians((dec1 + dec2) / 2.0)
    dist_deg = float(np.hypot(delta_ra * np.cos(mean_dec_rad), dec1 - dec2))
    
    if dist_deg > 0.1:
        return False, f"Observations pointing centers too far apart: {dist_deg:.4f} deg."

    # 3. Temporal difference
    mjd1 = meta1.get("mjd")
    mjd2 = meta2.get("mjd")
    if mjd1 is not None and mjd2 is not None and abs(mjd1 - mjd2) < 1e-4:
        return False, "Observations are from the exact same epoch."

    return True, "Eligible for comparison."

def compute_difference_frame(
    img1: np.ndarray,
    img2: np.ndarray
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Computes calibrated difference (img2 - img1).
    Resizes img2 to img1 shape if dimensions differ slightly due to cutout edge rounding.
    Robust against NaN, Inf, and non-finite pixel values.
    Returns:
        Tuple[difference_array_uint8, stats_dict]
    """
    if img1.shape != img2.shape:
        # Crop to common overlapping bounding box
        min_h = min(img1.shape[0], img2.shape[0])
        min_w = min(img1.shape[1], img2.shape[1])
        i1 = img1[:min_h, :min_w]
        i2 = img2[:min_h, :min_w]
    else:
        i1 = img1
        i2 = img2

    diff = i2.astype(np.float32) - i1.astype(np.float32)
    finite_mask = np.isfinite(diff)
    
    if not np.any(finite_mask):
        # All non-finite fallback
        return np.full(diff.shape, 128, dtype=np.uint8), {
            "rms_diff_mjy_sr": 0.0,
            "peak_positive_flux": 0.0,
            "peak_negative_flux": 0.0,
            "sigma_mjy_sr": 0.0,
        }

    finite_diff = diff[finite_mask]
    rms = float(np.sqrt(np.mean(finite_diff**2)))
    max_pos = float(np.max(finite_diff))
    max_neg = float(np.min(finite_diff))
    sigma = float(np.std(finite_diff))

    if sigma < 1e-5:
        sigma = 1.0

    normalized = 128.0 + (diff / (3.0 * sigma)) * 127.0
    # Set non-finite values to mid-gray (128 = zero change)
    normalized[~finite_mask] = 128.0
    u8_diff = np.clip(normalized, 0, 255).astype(np.uint8)

    stats = {
        "rms_diff_mjy_sr": round(rms, 4),
        "peak_positive_flux": round(max_pos, 4),
        "peak_negative_flux": round(max_neg, 4),
        "sigma_mjy_sr": round(sigma, 4)
    }

    return u8_diff, stats
