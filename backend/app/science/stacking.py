from typing import List, Dict, Any, Tuple, Optional, Literal
import numpy as np
from astropy.wcs import WCS
from app.science.image_registration import estimate_pixel_shift

def compute_robust_noise_sigma(img: np.ndarray) -> float:
    """
    Robust astronomical noise estimation using iterative sigma-clipped standard deviation
    with fallback to Median Absolute Deviation (MAD), preventing bright point sources
    and cosmic rays from corrupting the measured background noise floor.
    """
    finite = img[np.isfinite(img)]
    if len(finite) == 0:
        return 1.0
    try:
        from astropy.stats import sigma_clipped_stats
        _, _, s = sigma_clipped_stats(finite, sigma=2.5, maxiters=5)
        sigma = float(s)
    except Exception:
        med = float(np.median(finite))
        sigma = float(1.4826 * np.median(np.abs(finite - med)))
    if not np.isfinite(sigma) or sigma < 1e-6:
        sigma = float(np.std(finite)) if len(finite) > 0 else 1.0
    return max(float(sigma), 1e-6)

def compute_coadd_stack(
    images: List[np.ndarray],
    wcs_list: Optional[List[Optional[Any]]] = None,
    method: Literal["mean", "median", "sum"] = "mean",
    variances: Optional[List[Optional[np.ndarray]]] = None,
    masks: Optional[List[Optional[np.ndarray]]] = None,
    detectors: Optional[List[Optional[str]]] = None,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Co-adds / stacks a list of astronomical frames aligned on a shared celestial WCS grid.
    Only stacks compatible detector bands and wavelengths.
    Uses astropy / reproject_interp for celestial WCS alignment, with fallback to FFT shift.
    Propagates error variance: Var_stack = (1/N^2) * sum(Var_i) for mean stacking.
    Propagates data quality masks (bitwise/boolean OR of fatal defect masks).
    Accurately computes and reports measured SNR improvement factor.
    Robust against NaNs, infs, and varying image dimensions.

    Returns:
        Tuple[stacked_image_float32, stats_dict]
    """
    if not images:
        raise ValueError("Cannot stack an empty list of images.")

    # 0. Check detector band compatibility
    if detectors is not None:
        valid_dets = [str(d).strip().upper() for d in detectors if d]
        if len(valid_dets) > 1 and len(set(valid_dets)) > 1:
            raise ValueError(
                f"Incompatible detector bands for co-addition: {valid_dets[0]} vs {valid_dets[1]}. "
                "Co-addition requires compatible detector arrays."
            )

    if len(images) == 1:
        img = images[0].astype(np.float32)
        finite = img[np.isfinite(img)]
        sigma = compute_robust_noise_sigma(img)
        return img, {
            "method": method,
            "frame_count": 1,
            "snr_improvement_factor": 1.0,
            "theoretical_snr_gain": 1.0,
            "reference_noise_sigma": round(sigma, 4),
            "stacked_noise_sigma": round(sigma, 4),
            "mean_flux_mjy_sr": round(float(np.nanmean(img)), 4) if len(finite) > 0 else 0.0,
            "max_flux_mjy_sr": round(float(np.nanmax(img)), 4) if len(finite) > 0 else 0.0,
            "min_flux_mjy_sr": round(float(np.nanmin(img)), 4) if len(finite) > 0 else 0.0,
            "alignment_method": "single_frame",
        }

    # Reference frame is frame 0
    ref_img = images[0].copy().astype(np.float32)
    ref_wcs = wcs_list[0] if (wcs_list and len(wcs_list) > 0) else None
    ref_var = variances[0] if (variances and len(variances) > 0) else None
    ref_mask = masks[0] if (masks and len(masks) > 0) else None

    # Apply quality mask on reference image
    if ref_mask is not None:
        ref_img[ref_mask] = np.nan
    
    # Calculate single-frame robust reference noise floor across input frames
    ref_sigmas = [compute_robust_noise_sigma(im) for im in images]
    ref_sigma = float(np.median(ref_sigmas))
    if ref_sigma < 1e-6:
        ref_sigma = 1.0

    aligned_frames: List[np.ndarray] = [ref_img]
    aligned_vars: List[np.ndarray] = []
    aligned_masks: List[np.ndarray] = []

    # Init frame 0 variance and mask
    if ref_var is not None:
        aligned_vars.append(ref_var.copy().astype(np.float32))
    else:
        aligned_vars.append(np.full(ref_img.shape, ref_sigma**2, dtype=np.float32))

    if ref_mask is not None:
        aligned_masks.append(ref_mask.copy().astype(bool))
    else:
        aligned_masks.append(~np.isfinite(ref_img))

    alignment_methods_used = []

    ref_w_obj = None
    if ref_wcs is not None:
        try:
            ref_w_obj = WCS(ref_wcs) if not isinstance(ref_wcs, WCS) else ref_wcs
            if hasattr(ref_w_obj, "has_celestial") and ref_w_obj.has_celestial and ref_w_obj.naxis > 2:
                ref_w_obj = ref_w_obj.celestial
        except Exception:
            ref_w_obj = None

    for idx in range(1, len(images)):
        curr_img = images[idx].copy().astype(np.float32)
        curr_wcs = wcs_list[idx] if (wcs_list and idx < len(wcs_list)) else None
        curr_var = variances[idx] if (variances and idx < len(variances)) else None
        curr_mask = masks[idx] if (masks and idx < len(masks)) else None

        if curr_mask is not None:
            curr_img[curr_mask] = np.nan

        aligned = False

        # 1. Celestial WCS Reprojection
        if ref_w_obj is not None and curr_wcs is not None and ref_w_obj.naxis == 2:
            try:
                from reproject import reproject_interp
                c_w_obj = WCS(curr_wcs) if not isinstance(curr_wcs, WCS) else curr_wcs
                if hasattr(c_w_obj, "has_celestial") and c_w_obj.has_celestial and c_w_obj.naxis > 2:
                    c_w_obj = c_w_obj.celestial
                
                if c_w_obj.naxis == 2:
                    reproj_arr, footprint = reproject_interp(
                        (curr_img, c_w_obj),
                        ref_w_obj,
                        shape_out=ref_img.shape,
                        order="bilinear",
                    )
                    if np.any(footprint > 0) and np.any(np.isfinite(reproj_arr)):
                        curr_img = reproj_arr.astype(np.float32)
                        curr_img[footprint == 0] = np.nan
                        aligned = True
                        alignment_methods_used.append("wcs_reproject")

                        # Reproject variance and mask if present
                        if curr_var is not None:
                            var_reproj, _ = reproject_interp(
                                (curr_var.astype(np.float32), c_w_obj),
                                ref_w_obj,
                                shape_out=ref_img.shape,
                                order="bilinear",
                            )
                            aligned_vars.append(var_reproj.astype(np.float32))
                        else:
                            aligned_vars.append(np.full(ref_img.shape, ref_sigma**2, dtype=np.float32))

                        if curr_mask is not None:
                            m_reproj, _ = reproject_interp(
                                (curr_mask.astype(np.float32), c_w_obj),
                                ref_w_obj,
                                shape_out=ref_img.shape,
                                order="nearest",
                            )
                            aligned_masks.append((m_reproj > 0.5) | (footprint == 0))
                        else:
                            aligned_masks.append((footprint == 0) | (~np.isfinite(curr_img)))
                    else:
                        raise ValueError("Frames have no overlapping celestial sky coverage.")
            except ValueError:
                raise
            except Exception:
                pass

        # 2. Crop to common bounding box if shapes differ
        if not aligned and curr_img.shape != ref_img.shape:
            min_h = min(ref_img.shape[0], curr_img.shape[0])
            min_w = min(ref_img.shape[1], curr_img.shape[1])
            curr_img = curr_img[:min_h, :min_w]
            if curr_img.shape != ref_img.shape:
                padded = np.full(ref_img.shape, np.nan, dtype=np.float32)
                padded[:curr_img.shape[0], :curr_img.shape[1]] = curr_img
                curr_img = padded

        # 3. FFT Shift Fallback
        if not aligned:
            try:
                dy, dx = estimate_pixel_shift(ref_img, curr_img)
                if abs(dy) >= 0.5 or abs(dx) >= 0.5:
                    from scipy.ndimage import shift
                    curr_img = shift(curr_img, (-dy, -dx), order=1, mode="constant", cval=np.nan)
                    alignment_methods_used.append("fft_shift")
                else:
                    alignment_methods_used.append("direct")
            except Exception:
                alignment_methods_used.append("direct")

            aligned_vars.append(curr_var.copy() if curr_var is not None else np.full(ref_img.shape, ref_sigma**2, dtype=np.float32))
            aligned_masks.append(curr_mask.copy() if curr_mask is not None else ~np.isfinite(curr_img))

        aligned_frames.append(curr_img)

    # Stack along axis 0: (N, H, W)
    cube = np.stack(aligned_frames, axis=0)
    n_frames = len(aligned_frames)

    # Perform stacking
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        with np.errstate(all="ignore"):
            if method == "median":
                stacked = np.nanmedian(cube, axis=0)
            elif method == "sum":
                stacked = np.nansum(cube, axis=0)
                all_nan_mask = np.all(~np.isfinite(cube), axis=0)
                stacked[all_nan_mask] = np.nan
            else:  # default "mean"
                stacked = np.nanmean(cube, axis=0)

    # Propagate Variance: Var_stack = (1/N^2) * sum(Var_i) for mean coaddition
    valid_data_mask = np.isfinite(cube)
    valid_counts = np.sum(valid_data_mask, axis=0)
    safe_n = np.maximum(1, valid_counts).astype(np.float32)
    var_cube = np.stack(aligned_vars, axis=0)
    # Mask out variance of pixels that were invalid/masked in the image cube
    var_cube = np.where(valid_data_mask & np.isfinite(var_cube) & (var_cube >= 0), var_cube, np.nan)

    if method == "sum":
        stacked_var = np.where(valid_counts > 0, np.nansum(var_cube, axis=0), np.nan)
    elif method == "median":
        # Median coadd variance has asymptotic factor ~ pi / (2 * N)
        stacked_var = np.where(valid_counts > 0, (np.pi / (2.0 * safe_n**2)) * np.nansum(var_cube, axis=0), np.nan)
    else:  # "mean"
        stacked_var = np.where(valid_counts > 0, (1.0 / (safe_n**2)) * np.nansum(var_cube, axis=0), np.nan)

    finite_var = stacked_var[np.isfinite(stacked_var)]
    propagated_sigma = float(np.sqrt(max(1e-6, float(np.nanmedian(finite_var))))) if len(finite_var) > 0 else float(ref_sigma)

    # Propagate data quality masks: bitwise / boolean OR across overlapping frames
    mask_cube = np.stack(aligned_masks, axis=0)
    propagated_mask_any = np.any(mask_cube, axis=0)
    propagated_mask_all = np.all(mask_cube, axis=0)

    # Preserve invalid pixels as masks; do NOT fabricate background fill values in stacked data
    # (stacked pixels that are non-finite remain NaN)

    # Compute stacked noise statistics using robust sigma clipping on finite pixels
    stacked_sigma = compute_robust_noise_sigma(stacked)

    theoretical_gain = float(np.sqrt(n_frames))
    
    # Actual uncensored empirical SNR improvement estimator
    finite_stacked = stacked[np.isfinite(stacked)]
    if len(finite_stacked) < 4 or ref_sigma <= 1e-6 or stacked_sigma <= 1e-6:
        measured_snr_gain = None
        snr_gain_status = "unavailable"
    else:
        if method == "sum":
            raw_gain = (n_frames * ref_sigma) / stacked_sigma
        else:
            raw_gain = ref_sigma / stacked_sigma

        if np.isfinite(raw_gain) and raw_gain > 0:
            measured_snr_gain = round(float(raw_gain), 3)
            snr_gain_status = "measured"
        else:
            measured_snr_gain = None
            snr_gain_status = "unavailable"

    primary_alignment = "wcs_reproject" if "wcs_reproject" in alignment_methods_used else (
        "fft_shift" if "fft_shift" in alignment_methods_used else "direct"
    )

    stats = {
        "method": method,
        "frame_count": n_frames,
        "snr_improvement_factor": measured_snr_gain,
        "snr_gain_status": snr_gain_status,
        "theoretical_snr_gain": round(theoretical_gain, 3),
        "theoretical_gain_model": "sqrt(N) ideal Gaussian noise reduction",
        "reference_noise_sigma": round(ref_sigma, 4),
        "stacked_noise_sigma": round(stacked_sigma, 4),
        "propagated_noise_sigma": round(propagated_sigma, 4),
        "mean_flux_mjy_sr": round(float(np.nanmean(stacked)), 4) if len(finite_stacked) > 0 else 0.0,
        "max_flux_mjy_sr": round(float(np.nanmax(stacked)), 4) if len(finite_stacked) > 0 else 0.0,
        "min_flux_mjy_sr": round(float(np.nanmin(stacked)), 4) if len(finite_stacked) > 0 else 0.0,
        "alignment_method": primary_alignment,
        "flagged_pixels_count": int(np.count_nonzero(propagated_mask_any)),
        "unusable_pixels_count": int(np.count_nonzero(propagated_mask_all)),
        "propagated_mask": propagated_mask_any,
    }

    return stacked, stats
