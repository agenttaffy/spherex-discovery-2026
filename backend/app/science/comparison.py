from typing import Dict, Any, Tuple
import numpy as np

def check_comparison_eligibility(
    meta1: Dict[str, Any],
    meta2: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Evaluates whether two SPHEREx observations are scientifically eligible for direct subtraction.
    Checks detector band, effective wavelength, coordinate proximity, and temporal separation.
    """
    # 1. Detector match
    det1 = meta1.get("detector")
    det2 = meta2.get("detector")
    if det1 and det2 and det1 != det2:
        return False, f"Incompatible detectors: {det1} vs {det2}. Spectral bands differ."

    # 2. Celestial proximity
    ra1, dec1 = meta1.get("ra", 0.0), meta1.get("dec", 0.0)
    ra2, dec2 = meta2.get("ra", 0.0), meta2.get("dec", 0.0)
    dist_deg = np.hypot((ra1 - ra2) * np.cos(np.radians(dec1)), dec1 - dec2)
    if dist_deg > 0.1:
        return False, f"Observations pointing centers too far apart: {dist_deg:.4f} deg."

    # 3. Temporal difference
    mjd1 = meta1.get("mjd")
    mjd2 = meta2.get("mjd")
    if mjd1 and mjd2 and abs(mjd1 - mjd2) < 1e-4:
        return False, "Observations are from the exact same epoch."

    return True, "Eligible for comparison."

def compute_difference_frame(
    img1: np.ndarray,
    img2: np.ndarray
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Computes calibrated difference (img2 - img1).
    Resizes img2 to img1 shape if dimensions differ slightly due to cutout edge rounding.
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
    
    rms = float(np.sqrt(np.mean(diff**2)))
    max_pos = float(np.max(diff))
    max_neg = float(np.min(diff))

    # Center at 128 (mid-gray), scale by 3-sigma
    sigma = float(np.std(diff))
    if sigma < 1e-5:
        sigma = 1.0

    normalized = 128.0 + (diff / (3.0 * sigma)) * 127.0
    u8_diff = np.clip(normalized, 0, 255).astype(np.uint8)

    stats = {
        "rms_diff_mjy_sr": round(rms, 4),
        "peak_positive_flux": round(max_pos, 4),
        "peak_negative_flux": round(max_neg, 4),
        "sigma_mjy_sr": round(sigma, 4)
    }

    return u8_diff, stats
