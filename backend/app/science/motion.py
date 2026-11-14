import numpy as np
from typing import Dict, Any, Tuple, Optional
from app.science.image_registration import estimate_pixel_shift

# SPHEREx nominal detector pixel scale is 6.2 arcseconds per pixel
NOMINAL_PIXEL_SCALE_ARCSEC = 6.2

def _find_brightest_centroid(img: np.ndarray) -> Optional[Tuple[float, float, float]]:
    """
    Locates sub-pixel centroid (y, x) of the brightest peak in the image.
    Returns (y_cen, x_cen, peak_snr) or None if flat.
    """
    finite_mask = np.isfinite(img)
    if not np.any(finite_mask):
        return None
    
    clean_img = img.copy()
    bg_median = float(np.median(clean_img[finite_mask]))
    bg_std = float(np.std(clean_img[finite_mask]))
    if bg_std < 1e-6:
        bg_std = 1.0

    clean_img[~finite_mask] = bg_median
    
    # 3x3 max filter or argmax
    y_max, x_max = np.unravel_index(np.argmax(clean_img), clean_img.shape)
    peak_val = float(clean_img[y_max, x_max])
    snr = (peak_val - bg_median) / bg_std

    if snr < 2.5:
        return None

    # Local 5x5 window centroid around peak
    h, w = clean_img.shape
    y_min, y_high = max(0, y_max - 2), min(h, y_max + 3)
    x_min, x_high = max(0, x_max - 2), min(w, x_max + 3)

    sub = clean_img[y_min:y_high, x_min:x_high] - bg_median
    sub = np.maximum(sub, 0.0)
    total_flux = np.sum(sub)
    if total_flux <= 0:
        return float(y_max), float(x_max), snr

    yy, xx = np.indices(sub.shape)
    cen_y = y_min + np.sum(yy * sub) / total_flux
    cen_x = x_min + np.sum(xx * sub) / total_flux

    return float(cen_y), float(cen_x), snr

def measure_astrometric_motion(
    img1: np.ndarray,
    img2: np.ndarray,
    meta1: Dict[str, Any],
    meta2: Dict[str, Any],
    pixel_scale_arcsec: float = NOMINAL_PIXEL_SCALE_ARCSEC,
) -> Dict[str, Any]:
    """
    Computes astrometric displacement and annual proper motion vector between two observation epochs.
    Returns displacement in pixels and arcseconds, annual proper motion (arcsec/yr),
    position angle (deg), and candidate motion classification.
    """
    # 1. 2D FFT Cross-correlation overall translation shift
    fft_dy, fft_dx = estimate_pixel_shift(img1, img2)

    # 2. Centroid tracking on primary point source
    c1 = _find_brightest_centroid(img1)
    c2 = _find_brightest_centroid(img2)

    if c1 is not None and c2 is not None:
        y1, x1, snr1 = c1
        y2, x2, snr2 = c2
        dx_pix = x2 - x1
        dy_pix = y2 - y1
        centroid_detected = True
        confidence = min(1.0, max(0.2, (snr1 + snr2) / 20.0))
    else:
        dx_pix = fft_dx
        dy_pix = fft_dy
        centroid_detected = False
        confidence = 0.5 if abs(fft_dx) > 0.05 or abs(fft_dy) > 0.05 else 0.1

    # Total displacement
    disp_pix = float(np.hypot(dx_pix, dy_pix))
    disp_arcsec = float(disp_pix * pixel_scale_arcsec)

    # Position Angle: North is up (-y), East is left (-x) in astronomical WCS standard
    # PA is measured from North through East
    pa_deg = float((np.degrees(np.arctan2(-dx_pix, -dy_pix)) + 360.0) % 360.0)

    # Temporal separation
    mjd1 = float(meta1.get("mjd") or 0.0)
    mjd2 = float(meta2.get("mjd") or 0.0)
    dt_days = abs(mjd2 - mjd1)
    dt_years = dt_days / 365.25 if dt_days > 0 else 1.0

    # Annual proper motion rate
    proper_motion_arcsec_yr = float(disp_arcsec / dt_years) if dt_years > 0.001 else 0.0
    proper_motion_mas_yr = float(proper_motion_arcsec_yr * 1000.0)

    # Classification
    if disp_pix >= 0.3 and proper_motion_arcsec_yr > 0.5:
        motion_class = "High Proper Motion Candidate"
    elif disp_pix >= 0.15 and proper_motion_arcsec_yr > 0.1:
        motion_class = "Moderate Proper Motion Source"
    else:
        motion_class = "Stationary / Sub-threshold"

    return {
        "dx_pixels": round(dx_pix, 3),
        "dy_pixels": round(dy_pix, 3),
        "displacement_pixels": round(disp_pix, 3),
        "displacement_arcsec": round(disp_arcsec, 3),
        "position_angle_deg": round(pa_deg, 1),
        "delta_time_days": round(dt_days, 2),
        "delta_time_years": round(dt_years, 3),
        "proper_motion_arcsec_yr": round(proper_motion_arcsec_yr, 3),
        "proper_motion_mas_yr": round(proper_motion_mas_yr, 1),
        "motion_class": motion_class,
        "centroid_detected": centroid_detected,
        "pixel_scale_arcsec": pixel_scale_arcsec,
        "confidence_score": round(confidence, 2),
    }
