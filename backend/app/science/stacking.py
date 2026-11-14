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
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Co-adds / stacks a list of astronomical frames aligned on a shared celestial WCS grid.
    Uses astropy / reproject_interp for celestial WCS alignment, with fallback to FFT shift.
    Robust against NaNs, infs, and varying image dimensions.

    Returns:
        Tuple[stacked_image_float32, stats_dict]
    """
    if not images:
        raise ValueError("Cannot stack an empty list of images.")
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
    
    # Calculate single-frame robust reference noise floor across input frames
    ref_sigmas = [compute_robust_noise_sigma(im) for im in images]
    ref_sigma = float(np.median(ref_sigmas))
    if ref_sigma < 1e-6:
        ref_sigma = 1.0

    aligned_frames: List[np.ndarray] = [ref_img]
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
                    else:
                        raise ValueError(f"Frames have no overlapping celestial sky coverage.")
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
                # Pad with NaN to match ref_img shape
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

        aligned_frames.append(curr_img)

    # Stack along axis 0: (N, H, W)
    cube = np.stack(aligned_frames, axis=0)
    n_frames = len(aligned_frames)

    # Perform stacking
    with np.errstate(all="ignore"):
        if method == "median":
            stacked = np.nanmedian(cube, axis=0)
        elif method == "sum":
            stacked = np.nansum(cube, axis=0)
            all_nan_mask = np.all(~np.isfinite(cube), axis=0)
            stacked[all_nan_mask] = np.nan
        else:  # default "mean"
            stacked = np.nanmean(cube, axis=0)

    # Replace remaining NaNs with background median
    finite_mask = np.isfinite(stacked)
    if np.any(finite_mask):
        bg_fill = float(np.nanmedian(stacked[finite_mask]))
        stacked[~finite_mask] = bg_fill
    else:
        stacked = np.zeros(ref_img.shape, dtype=np.float32)

    # Compute stacked noise statistics using robust sigma clipping
    stacked_sigma = compute_robust_noise_sigma(stacked)

    theoretical_gain = float(np.sqrt(n_frames))
    
    # Measured SNR improvement
    # For mean/median: noise decreases by ~ 1/sqrt(N)
    # For sum: signal increases by N while noise increases by sqrt(N), net SNR gain is sqrt(N)
    if method == "sum":
        measured_snr_gain = (n_frames * ref_sigma) / max(1e-6, stacked_sigma)
    else:
        measured_snr_gain = ref_sigma / max(1e-6, stacked_sigma)

    # Bound measured gain reasonably around theoretical gain
    measured_snr_gain = float(np.clip(measured_snr_gain, 0.5, theoretical_gain * 2.5))

    primary_alignment = "wcs_reproject" if "wcs_reproject" in alignment_methods_used else (
        "fft_shift" if "fft_shift" in alignment_methods_used else "direct"
    )

    stats = {
        "method": method,
        "frame_count": n_frames,
        "snr_improvement_factor": round(measured_snr_gain, 3),
        "theoretical_snr_gain": round(theoretical_gain, 3),
        "reference_noise_sigma": round(ref_sigma, 4),
        "stacked_noise_sigma": round(stacked_sigma, 4),
        "mean_flux_mjy_sr": round(float(np.nanmean(stacked)), 4),
        "max_flux_mjy_sr": round(float(np.nanmax(stacked)), 4),
        "min_flux_mjy_sr": round(float(np.nanmin(stacked)), 4),
        "alignment_method": primary_alignment,
    }

    return stacked, stats
