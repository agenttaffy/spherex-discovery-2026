from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from astropy.wcs import WCS

def compute_aperture_photometry(
    image: np.ndarray,
    center_y: Optional[float] = None,
    center_x: Optional[float] = None,
    target_coord: Optional[Tuple[float, float]] = None,
    wcs: Optional[Any] = None,
    variance: Optional[np.ndarray] = None,
    mask: Optional[np.ndarray] = None,
    source_mask: Optional[np.ndarray] = None,
    aperture_radius: float = 3.0,
    annulus_inner: float = 4.5,
    annulus_outer: float = 7.0,
) -> Dict[str, float]:
    """
    Computes circular aperture photometry with local background annulus subtraction.
    Pixel values are assumed in calibrated units of MJy/sr.
    When target_coord (ra, dec) and celestial WCS are provided, transforms the requested
    celestial position into exact pixel coordinates (x, y) rather than peak-seeking.
    Uses VARIANCE array when available to compute real photometric flux uncertainties.
    Excludes fatal quality mask pixels from aperture and background calculations.
    Distinguishes nominal source masks from fatal defects: source_mask is excluded
    from the background annulus to prevent background inflation, but preserved in aperture.
    """
    h, w = image.shape

    # 1. Coordinate transformation from celestial (RA, Dec) via WCS if provided
    if target_coord is not None:
        target_projected = False
        if wcs is not None:
            try:
                from app.science.fits_processing import extract_astropy_wcs
                w_obj = wcs if isinstance(wcs, WCS) else extract_astropy_wcs(wcs)
                if w_obj is not None:
                    from astropy.coordinates import SkyCoord
                    import astropy.units as u
                    sc = SkyCoord(target_coord[0] * u.deg, target_coord[1] * u.deg, frame="icrs")
                    px, py = w_obj.world_to_pixel(sc)
                    if np.isfinite(px) and np.isfinite(py):
                        center_x, center_y = float(px), float(py)
                        target_projected = True
            except Exception:
                try:
                    px, py = w_obj.all_world2pix(target_coord[0], target_coord[1], 0)
                    if np.isfinite(px) and np.isfinite(py):
                        center_x, center_y = float(px), float(py)
                        target_projected = True
                except Exception:
                    pass

        if not target_projected or center_x is None or center_y is None or not np.isfinite(center_x) or not np.isfinite(center_y):
            # Target coordinates were provided but WCS projection failed or returned non-finite coordinates.
            # Never silently measure image center or substitute brightest source.
            return {
                "status": "unavailable",
                "valid": False,
                "reason": "Target coordinates could not be projected via WCS (missing WCS or non-finite projection)",
                "aperture_flux_sum": None,
                "aperture_mean": None,
                "background_median": None,
                "background_std": None,
                "net_flux": None,
                "flux_err": None,
                "peak_flux": None,
                "snr": None,
                "coverage_fraction": 0.0,
                "aperture_area_pixels": 0,
                "valid_pixel_count": 0,
            }
    elif center_y is None or center_x is None:
        # Blind peak-seeking only when NO target coordinates were specified
        from app.science.motion import _find_brightest_centroid
        cen = _find_brightest_centroid(image)
        if cen is not None:
            center_y, center_x, _ = cen
        else:
            center_y = (h - 1) / 2.0
            center_x = (w - 1) / 2.0

    y_indices, x_indices = np.indices((h, w))
    dist_sq = (y_indices - center_y) ** 2 + (x_indices - center_x) ** 2
    dist = np.sqrt(dist_sq)

    # Valid pixel mask: must be finite and not flagged by fatal quality mask
    valid_mask = np.isfinite(image)
    if mask is not None and mask.shape == image.shape:
        valid_mask &= (~mask)

    if not np.any(valid_mask):
        return {
            "status": "unavailable",
            "valid": False,
            "reason": "No finite, unmasked pixels available in image",
            "aperture_flux_sum": None,
            "aperture_mean": None,
            "background_median": None,
            "background_std": None,
            "net_flux": None,
            "flux_err": None,
            "peak_flux": None,
            "snr": None,
            "coverage_fraction": 0.0,
            "aperture_area_pixels": 0,
            "valid_pixel_count": 0,
        }

    # Theoretical full circular aperture area
    r_int = int(np.ceil(aperture_radius))
    dy_grid, dx_grid = np.ogrid[-r_int:r_int+1, -r_int:r_int+1]
    n_geom = int(np.sum(dy_grid**2 + dx_grid**2 <= aperture_radius**2))

    # Aperture mask on image pixels (directly slice image without fabricating fill values)
    geom_ap_mask = dist <= aperture_radius
    ap_mask = geom_ap_mask & valid_mask
    ap_pixels = image[ap_mask]
    n_ap = int(np.sum(ap_mask))
    coverage_fraction = float(n_ap / max(1, n_geom))

    # Background annulus mask: exclude fatal mask and optionally exclude detected field sources
    ann_mask = (dist >= annulus_inner) & (dist <= annulus_outer) & valid_mask
    if source_mask is not None and source_mask.shape == image.shape:
        pure_bg_mask = ann_mask & (~source_mask)
        if np.any(pure_bg_mask):
            ann_mask = pure_bg_mask
    ann_pixels = image[ann_mask]
    n_ann = int(np.sum(ann_mask))

    if n_ann > 0:
        bg_med = float(np.median(ann_pixels))
        bg_std = float(np.std(ann_pixels))
    else:
        bg_med = float(np.median(image[valid_mask]))
        bg_std = float(np.std(image[valid_mask]))

    if bg_std < 1e-6:
        bg_std = 1.0

    if n_ap == 0:
        return {
            "status": "unavailable",
            "valid": False,
            "reason": "Target aperture contains zero valid, unmasked pixels within the frame",
            "aperture_flux_sum": 0.0,
            "aperture_mean": 0.0,
            "background_median": round(bg_med, 4),
            "background_std": round(bg_std, 4),
            "net_flux": None,
            "flux_err": None,
            "peak_flux": None,
            "snr": None,
            "coverage_fraction": 0.0,
            "aperture_area_pixels": n_geom,
            "valid_pixel_count": 0,
        }

    ap_sum = float(np.sum(ap_pixels))
    ap_mean = float(np.mean(ap_pixels))
    peak_val = float(np.max(ap_pixels))
    # Net flux = aperture sum minus background contribution
    raw_net_flux = float(ap_sum - (bg_med * n_ap))

    # Real Photometric Flux Uncertainty Propagation (sigma_F = sqrt(sum(sigma_i^2)))
    if variance is not None and variance.shape == image.shape:
        var_clean = np.where(np.isfinite(variance) & (variance >= 0), variance, 0.0)
        ap_var_sum = float(np.sum(var_clean[ap_mask]))
        ann_var_mean = float(np.mean(var_clean[ann_mask])) if n_ann > 0 else (bg_std ** 2)
        bg_var_contrib = (n_ap ** 2 / max(1, n_ann)) * ann_var_mean
        raw_flux_err = float(np.sqrt(max(0.0, ap_var_sum + bg_var_contrib)))
    else:
        # Poisson + background uncertainty estimate
        raw_flux_err = float(np.sqrt(n_ap * (bg_std ** 2) + (n_ap ** 2 / max(1, n_ann)) * (bg_std ** 2)))

    # Astronomical aperture boundary clipping correction:
    # If the target is located near the frame border or has masked pixels within the aperture,
    # scale the net flux and error by the aperture coverage fraction (1 / f_cov)
    if coverage_fraction >= 0.15:
        net_flux = float(raw_net_flux / coverage_fraction)
        flux_err = float(raw_flux_err / coverage_fraction)
    else:
        net_flux = raw_net_flux
        flux_err = raw_flux_err

    snr = float(net_flux / flux_err) if flux_err > 1e-6 else float((peak_val - bg_med) / bg_std)

    return {
        "status": "measured",
        "valid": True,
        "reason": None,
        "aperture_flux_sum": round(ap_sum, 4),
        "aperture_mean": round(ap_mean, 4),
        "background_median": round(bg_med, 4),
        "background_std": round(bg_std, 4),
        "net_flux": round(net_flux, 4),
        "flux_err": round(flux_err, 4),
        "peak_flux": round(peak_val, 4),
        "snr": round(max(0.0, snr), 2),
        "coverage_fraction": round(coverage_fraction, 3),
        "aperture_area_pixels": n_geom,
        "valid_pixel_count": n_ap,
    }

def build_lightcurve_series(
    epoch_frames: List[Dict[str, Any]],
    target_ra: Optional[float] = None,
    target_dec: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Takes a chronological list of epoch frame data and produces a lightcurve dataset
    with variability indicators.
    Each item in epoch_frames should contain:
    - obs_id
    - mjd
    - utc_date
    - detector
    - collection
    - image (numpy 2D array)
    Optional: wcs / header, variance, mask
    """
    points = []
    target_coord = (target_ra, target_dec) if (target_ra is not None and target_dec is not None) else None

    for item in epoch_frames:
        img = item.get("image")
        if img is None:
            continue
        wcs = item.get("wcs") or item.get("header")
        var = item.get("variance")
        mask = item.get("mask")
        source_mask = item.get("source_mask")

        phot = compute_aperture_photometry(
            image=img,
            target_coord=target_coord,
            wcs=wcs,
            variance=var,
            mask=mask,
            source_mask=source_mask,
        )
        points.append({
            "obs_id": item.get("obs_id", "unknown"),
            "frame_id": item.get("frame_id", ""),
            "mjd": item.get("mjd"),
            "utc_date": item.get("utc_date"),
            "detector": item.get("detector", "SPHEREx"),
            "collection": item.get("collection", "spherex_dr1"),
            "status": phot.get("status", "measured"),
            "valid": phot.get("valid", True),
            "reason": phot.get("reason"),
            "net_flux_mjy_sr": phot["net_flux"],
            "flux_err_mjy_sr": phot["flux_err"],
            "peak_flux_mjy_sr": phot["peak_flux"],
            "aperture_flux_sum": phot["aperture_flux_sum"],
            "background_median": phot["background_median"],
            "snr": phot["snr"],
            "coverage_fraction": phot.get("coverage_fraction", 0.0),
        })

    # Sort chronologically by MJD
    points.sort(key=lambda p: p["mjd"] or 0.0)

    # Overall series statistics (only include valid measurements with non-None flux)
    net_fluxes = [
        p["net_flux_mjy_sr"]
        for p in points
        if p.get("valid", True) and p["net_flux_mjy_sr"] is not None
    ]
    if net_fluxes:
        mean_flux = float(np.mean(net_fluxes))
        std_flux = float(np.std(net_fluxes))
        min_flux = float(np.min(net_fluxes))
        max_flux = float(np.max(net_fluxes))
        amplitude_delta = max_flux - min_flux
    else:
        mean_flux = std_flux = min_flux = max_flux = amplitude_delta = 0.0

    # Group by detector to evaluate photometric variability within consistent spectral bands
    from collections import defaultdict
    by_detector = defaultdict(list)
    for p in points:
        if p.get("valid", True) and p["net_flux_mjy_sr"] is not None:
            by_detector[p.get("detector", "SPHEREx")].append(p["net_flux_mjy_sr"])

    is_variable = False
    max_var_index = 0.0

    for det, fluxes in by_detector.items():
        if len(fluxes) >= 2:
            m = float(np.mean(fluxes))
            s = float(np.std(fluxes))
            d_amp = float(np.max(fluxes) - np.min(fluxes))
            # Require mean to exceed background noise floor (> 1.0 MJy/sr) for fractional variability
            v_idx = s / abs(m) if abs(m) > 1.0 else 0.0
            if v_idx > max_var_index:
                max_var_index = v_idx
            # Confirm variability if significant relative variation (>15%) and amplitude (>20.0 MJy/sr) OR large amplitude (>50.0 MJy/sr)
            if (v_idx > 0.15 and d_amp > 20.0) or d_amp > 50.0:
                is_variable = True

    return {
        "total_points": len(points),
        "is_variable": is_variable,
        "variability_index": round(max_var_index, 3),
        "mean_flux_mjy_sr": round(mean_flux, 4),
        "std_flux_mjy_sr": round(std_flux, 4),
        "min_flux_mjy_sr": round(min_flux, 4),
        "max_flux_mjy_sr": round(max_flux, 4),
        "amplitude_delta_mjy_sr": round(amplitude_delta, 4),
        "points": points,
    }
