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

def _find_local_centroid(
    img: np.ndarray,
    expected_y: float,
    expected_x: float,
    search_radius: int = 4
) -> Optional[Tuple[float, float, float]]:
    """
    Locates sub-pixel centroid (y, x) in a local neighborhood centered around an expected
    celestial position (expected_y, expected_x). Prevents wandering off to an unrelated brighter star.
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

    h, w = clean_img.shape
    int_y = int(round(expected_y))
    int_x = int(round(expected_x))

    if int_y < 0 or int_y >= h or int_x < 0 or int_x >= w:
        return None

    y_min, y_high = max(0, int_y - search_radius), min(h, int_y + search_radius + 1)
    x_min, x_high = max(0, int_x - search_radius), min(w, int_x + search_radius + 1)

    local_patch = clean_img[y_min:y_high, x_min:x_high]
    if local_patch.size == 0:
        return None

    loc_y_max, loc_x_max = np.unravel_index(np.argmax(local_patch), local_patch.shape)
    peak_y = y_min + loc_y_max
    peak_x = x_min + loc_x_max
    peak_val = float(clean_img[peak_y, peak_x])
    snr = (peak_val - bg_median) / bg_std

    # Sub-pixel center of mass in 5x5 box around local peak
    box_y_min, box_y_max = max(0, peak_y - 2), min(h, peak_y + 3)
    box_x_min, box_x_max = max(0, peak_x - 2), min(w, peak_x + 3)
    sub = clean_img[box_y_min:box_y_max, box_x_min:box_x_max] - bg_median
    sub = np.maximum(sub, 0.0)
    total_flux = np.sum(sub)
    if total_flux <= 0:
        return float(peak_y), float(peak_x), snr

    yy, xx = np.indices(sub.shape)
    cen_y = box_y_min + np.sum(yy * sub) / total_flux
    cen_x = box_x_min + np.sum(xx * sub) / total_flux

    return float(cen_y), float(cen_x), snr

def measure_astrometric_motion(
    img1: np.ndarray,
    img2: np.ndarray,
    meta1: Dict[str, Any],
    meta2: Dict[str, Any],
    wcs1: Optional[Any] = None,
    wcs2: Optional[Any] = None,
    target_coord: Optional[Tuple[float, float]] = None,
    pixel_scale_arcsec: float = NOMINAL_PIXEL_SCALE_ARCSEC,
) -> Dict[str, Any]:
    """
    Computes astrometric displacement and annual proper motion vector between two observation epochs.
    Tracks the requested celestial target (RA, Dec) through each image WCS rather than the global
    brightest pixel. Converts shifts through celestial WCS and uses true epoch baselines.
    Returns displacement in pixels and arcseconds, annual proper motion (arcsec/yr),
    position angle (deg), and candidate motion classification.
    """
    # 1. 2D FFT Cross-correlation overall translation shift
    fft_dy, fft_dx = estimate_pixel_shift(img1, img2)

    # 2. Celestial target coordinates and WCS extraction
    from app.science.fits_processing import extract_astropy_wcs
    from astropy.wcs import WCS
    from astropy.coordinates import SkyCoord
    import astropy.units as u

    w_obj1 = wcs1 if isinstance(wcs1, WCS) else (extract_astropy_wcs(wcs1) if wcs1 is not None else None)
    w_obj2 = wcs2 if isinstance(wcs2, WCS) else (extract_astropy_wcs(wcs2) if wcs2 is not None else None)

    if w_obj1 is None and "header" in meta1:
        w_obj1 = extract_astropy_wcs(meta1["header"])
    if w_obj2 is None and "header" in meta2:
        w_obj2 = extract_astropy_wcs(meta2["header"])

    # Establish target coordinates
    if target_coord is None:
        tgt_ra = meta1.get("target_ra") or meta1.get("ra")
        tgt_dec = meta1.get("target_dec") or meta1.get("dec")
        if tgt_ra is not None and tgt_dec is not None:
            target_coord = (float(tgt_ra), float(tgt_dec))

    c1 = None
    c2 = None
    used_wcs = False

    if target_coord is not None and w_obj1 is not None and w_obj2 is not None:
        try:
            sc = SkyCoord(target_coord[0] * u.deg, target_coord[1] * u.deg, frame="icrs")
            px1, py1 = w_obj1.world_to_pixel(sc)
            px2, py2 = w_obj2.world_to_pixel(sc)

            if np.isfinite(px1) and np.isfinite(py1) and np.isfinite(px2) and np.isfinite(py2):
                c1 = _find_local_centroid(img1, float(py1), float(px1), search_radius=4)
                c2 = _find_local_centroid(img2, float(py2), float(px2), search_radius=4)
                
                # If target peak is faint in local window, anchor strictly to expected WCS target coordinates
                # rather than wandering off to arbitrary brightest field stars
                if c1 is None:
                    c1 = (float(py1), float(px1), 1.0)
                if c2 is None:
                    c2 = (float(py2), float(px2), 1.0)
                used_wcs = True
        except Exception:
            used_wcs = False

    # Centroid tracking fallback when WCS tracking was not used or centroids not yet found
    if c1 is None:
        c1 = _find_brightest_centroid(img1)
    if c2 is None:
        c2 = _find_brightest_centroid(img2)

    celestial_shift_arcsec = None
    celestial_pa_deg = None
    d_ra_cosdec_arcsec = None
    d_dec_arcsec = None
    pm_ra_cosdec_mas_yr = None
    pm_dec_mas_yr = None

    # Temporal separation using true epoch baselines
    mjd1 = float(meta1.get("mjd") or 0.0)
    mjd2 = float(meta2.get("mjd") or 0.0)
    dt_days = abs(mjd2 - mjd1)

    if dt_days < 1e-4:
        utc1 = meta1.get("utc_date")
        utc2 = meta2.get("utc_date")
        if utc1 and utc2:
            try:
                from astropy.time import Time
                dt_days = abs((Time(utc2) - Time(utc1)).jd)
            except Exception:
                pass

    dt_years = dt_days / 365.25 if dt_days > 0 else 1.0

    if c1 is not None and c2 is not None:
        y1, x1, snr1 = c1
        y2, x2, snr2 = c2
        centroid_detected = True
        confidence = min(1.0, max(0.2, (snr1 + snr2) / 20.0))
        centroid_1 = [round(x1, 2), round(y1, 2)]

        # Transform sub-pixel centroids through celestial WCS
        if w_obj1 is not None and w_obj2 is not None:
            try:
                sky1 = w_obj1.pixel_to_world(x1, y1)
                sky2 = w_obj2.pixel_to_world(x2, y2)
                celestial_shift_arcsec = float(sky1.separation(sky2).arcsec)
                celestial_pa_deg = float(sky1.position_angle(sky2).degree)

                # Convert shifts through WCS to celestial (delta_ra * cos(dec), delta_dec)
                d_ra_deg = (sky2.ra.deg - sky1.ra.deg + 180.0) % 360.0 - 180.0
                mean_dec_rad = np.radians((sky1.dec.deg + sky2.dec.deg) / 2.0)
                d_ra_cosdec_arcsec = float(d_ra_deg * np.cos(mean_dec_rad) * 3600.0)
                d_dec_arcsec = float((sky2.dec.deg - sky1.dec.deg) * 3600.0)

                if dt_years > 0:
                    pm_ra_cosdec_mas_yr = float((d_ra_cosdec_arcsec / dt_years) * 1000.0)
                    pm_dec_mas_yr = float((d_dec_arcsec / dt_years) * 1000.0)

                # Project epoch 2 celestial position back into epoch 1 (reference) WCS grid.
                # This ensures target displacement (dx_pix, dy_pix) reflects TRUE physical motion on the sky,
                # completely isolating it from telescope pointing/registration shifts between epochs.
                proj_x2, proj_y2 = w_obj1.world_to_pixel(sky2)
                if np.isfinite(proj_x2) and np.isfinite(proj_y2):
                    dx_pix = float(proj_x2 - x1)
                    dy_pix = float(proj_y2 - y1)
                    centroid_2 = [round(float(proj_x2), 2), round(float(proj_y2), 2)]
                else:
                    dx_pix = x2 - x1
                    dy_pix = y2 - y1
                    centroid_2 = [round(x2, 2), round(y2, 2)]
            except Exception:
                dx_pix = x2 - x1
                dy_pix = y2 - y1
                centroid_2 = [round(x2, 2), round(y2, 2)]
        else:
            dx_pix = x2 - x1
            dy_pix = y2 - y1
            centroid_2 = [round(x2, 2), round(y2, 2)]
    else:
        # Centroid was not detected for the target in both epochs.
        # Do NOT attribute overall image registration / pointing shift (fft_dx, fft_dy) to target motion!
        dx_pix = 0.0
        dy_pix = 0.0
        centroid_detected = False
        confidence = 0.0
        centroid_1 = None
        centroid_2 = None

    # Total displacement
    if celestial_shift_arcsec is not None:
        disp_arcsec = celestial_shift_arcsec
        disp_pix = float(disp_arcsec / pixel_scale_arcsec) if pixel_scale_arcsec > 0 else float(np.hypot(dx_pix, dy_pix))
    else:
        disp_pix = float(np.hypot(dx_pix, dy_pix))
        disp_arcsec = float(disp_pix * pixel_scale_arcsec)

    # Position Angle
    if celestial_pa_deg is not None:
        pa_deg = celestial_pa_deg
    else:
        pa_deg = float((np.degrees(np.arctan2(-dx_pix, -dy_pix)) + 360.0) % 360.0) if (abs(dx_pix) > 1e-4 or abs(dy_pix) > 1e-4) else 0.0

    # Annual proper motion rate
    proper_motion_arcsec_yr = float(disp_arcsec / dt_years) if dt_days > 1e-4 else 0.0
    proper_motion_mas_yr = float(proper_motion_arcsec_yr * 1000.0)

    # Classification: require detected centroid and significant physical celestial motion
    if centroid_detected and disp_arcsec >= (0.3 * pixel_scale_arcsec) and proper_motion_arcsec_yr > 0.5:
        motion_class = "High Proper Motion Candidate"
    elif centroid_detected and disp_arcsec >= (0.15 * pixel_scale_arcsec) and proper_motion_arcsec_yr > 0.1:
        motion_class = "Moderate Proper Motion Source"
    else:
        motion_class = "Stationary / Sub-threshold"

    res = {
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
        "centroid_1": centroid_1,
        "centroid_2": centroid_2,
        "pixel_scale_arcsec": pixel_scale_arcsec,
        "confidence_score": round(confidence, 2),
        "wcs_tracking": used_wcs,
        "frame_registration_shift_pixels": [round(fft_dx, 3), round(fft_dy, 3)],
    }

    if d_ra_cosdec_arcsec is not None:
        res["d_ra_cosdec_arcsec"] = round(d_ra_cosdec_arcsec, 4)
        res["d_dec_arcsec"] = round(d_dec_arcsec, 4)
    if pm_ra_cosdec_mas_yr is not None:
        res["pm_ra_cosdec_mas_yr"] = round(pm_ra_cosdec_mas_yr, 1)
        res["pm_dec_mas_yr"] = round(pm_dec_mas_yr, 1)

    return res
