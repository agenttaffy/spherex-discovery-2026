from typing import Dict, Any, Tuple, Optional
import numpy as np
from astropy.wcs import WCS
from app.science.image_registration import estimate_pixel_shift

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

    # 1. Detector match & LVF passband compatibility
    det1 = meta1.get("detector")
    det2 = meta2.get("detector")
    if det1 and det2 and det1 != det2:
        return False, f"Incompatible detectors: {det1} vs {det2}. Spectral bands differ."

    # Check LVF effective wavelength coverage if available
    em_min1 = meta1.get("em_min")
    em_max1 = meta1.get("em_max")
    em_min2 = meta2.get("em_min")
    em_max2 = meta2.get("em_max")
    if em_min1 is not None and em_max1 is not None and em_min2 is not None and em_max2 is not None:
        try:
            overlap = min(float(em_max1), float(em_max2)) - max(float(em_min1), float(em_min2))
            if overlap <= 0:
                return False, f"Incompatible LVF wavelength coverage: [{float(em_min1):.2f}, {float(em_max1):.2f}] µm vs [{float(em_min2):.2f}, {float(em_max2):.2f}] µm. Linear Variable Filter differencing requires overlapping spectral coverage."
        except (ValueError, TypeError):
            pass

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
    img2: np.ndarray,
    wcs1: Optional[Any] = None,
    wcs2: Optional[Any] = None,
    mask1: Optional[np.ndarray] = None,
    mask2: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Computes calibrated scientific difference (img2 - img1).
    When celestial WCS coordinates are provided, reprojects img2 onto img1's celestial grid
    using astropy / reproject_interp to account for differing WCS geometries, pixel scales,
    or rotations.
    Preserves data quality masks (setting masked and non-overlapping pixels to mid-gray).
    Returns clear errors when celestial coverage does not overlap.
    Gracefully falls back to FFT shift registration if WCS is absent, and crops to overlapping
    bounding boxes when dimensions differ.
    Robust against NaN, Inf, and non-finite pixel values.
    Returns:
        Tuple[difference_array_uint8, stats_dict]
    """
    alignment_method = "direct"
    i1 = img1.copy().astype(np.float32)
    i2 = img2.copy().astype(np.float32)

    # Apply quality masks before subtraction
    if mask1 is not None and mask1.shape == i1.shape:
        i1[mask1] = np.nan
    if mask2 is not None and mask2.shape == i2.shape:
        i2[mask2] = np.nan

    # 1. Scientific WCS Reprojection via reproject_interp
    if wcs1 is not None and wcs2 is not None:
        from reproject import reproject_interp
        w_obj1 = WCS(wcs1) if not isinstance(wcs1, WCS) else wcs1
        w_obj2 = WCS(wcs2) if not isinstance(wcs2, WCS) else wcs2

        # Extract 2D celestial sub-WCS if headers contain extra axes (e.g., spectral NAXIS=3)
        if hasattr(w_obj1, "has_celestial") and w_obj1.has_celestial and w_obj1.naxis > 2:
            w_obj1 = w_obj1.celestial
        if hasattr(w_obj2, "has_celestial") and w_obj2.has_celestial and w_obj2.naxis > 2:
            w_obj2 = w_obj2.celestial

        if w_obj1.naxis == 2 and w_obj2.naxis == 2:
            try:
                reproj_arr, footprint = reproject_interp(
                    (i2, w_obj2),
                    w_obj1,
                    shape_out=i1.shape,
                    order="bilinear",
                )
            except Exception as reproj_err:
                raise ValueError(f"WCS reprojection failed: {reproj_err}")

            if footprint is None or np.sum(footprint > 0) == 0 or not np.any(np.isfinite(reproj_arr)):
                raise ValueError("Frames have no overlapping celestial sky coverage.")

            i2 = reproj_arr.astype(np.float32)
            i2[footprint == 0] = np.nan
            alignment_method = "wcs_reproject"

    # 2. Crop to common overlapping bounding box if dimensions differ
    if i1.shape != i2.shape:
        min_h = min(i1.shape[0], i2.shape[0])
        min_w = min(i1.shape[1], i2.shape[1])
        i1 = i1[:min_h, :min_w]
        i2 = i2[:min_h, :min_w]

    # 3. FFT Shift Registration Fallback (if WCS reprojection was not applied)
    if alignment_method != "wcs_reproject":
        try:
            dy, dx = estimate_pixel_shift(i1, i2)
            if abs(dy) >= 0.5 or abs(dx) >= 0.5:
                from scipy.ndimage import shift
                # Shift img2 to register with img1
                i2 = shift(i2, (-dy, -dx), order=1, mode="constant", cval=np.nan)
                alignment_method = "fft_shift"
        except Exception:
            pass

    diff = i2.astype(np.float32) - i1.astype(np.float32)
    finite_mask = np.isfinite(diff)
    
    if not np.any(finite_mask):
        # All non-finite fallback
        return np.full(diff.shape, 128, dtype=np.uint8), {
            "rms_diff_mjy_sr": 0.0,
            "peak_positive_flux": 0.0,
            "peak_negative_flux": 0.0,
            "sigma_mjy_sr": 0.0,
            "alignment_method": alignment_method,
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
        "sigma_mjy_sr": round(sigma, 4),
        "alignment_method": alignment_method,
        "overlap_pixels_count": int(np.count_nonzero(finite_mask)),
        "masked_pixels_count": int(np.count_nonzero(~finite_mask)),
    }

    return u8_diff, stats
