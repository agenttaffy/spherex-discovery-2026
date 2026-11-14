from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from app.science.photometry import compute_aperture_photometry
from app.science.fits_processing import load_fits_cutout, extract_primary_image

SPHEREX_DETECTOR_CONFIG = [
    {
        "detector": "SPHEREx-D1",
        "band_idx": 1,
        "wave_min": 0.75,
        "wave_max": 1.12,
        "wave_eff": 0.935,
        "channel_count": 17,
        "color": "#06b6d4",  # Cyan
    },
    {
        "detector": "SPHEREx-D2",
        "band_idx": 2,
        "wave_min": 1.12,
        "wave_max": 1.68,
        "wave_eff": 1.400,
        "channel_count": 17,
        "color": "#10b981",  # Emerald
    },
    {
        "detector": "SPHEREx-D3",
        "band_idx": 3,
        "wave_min": 1.68,
        "wave_max": 2.42,
        "wave_eff": 2.050,
        "channel_count": 17,
        "color": "#f59e0b",  # Amber
    },
    {
        "detector": "SPHEREx-D4",
        "band_idx": 4,
        "wave_min": 2.42,
        "wave_max": 3.82,
        "wave_eff": 3.120,
        "channel_count": 17,
        "color": "#f97316",  # Orange
    },
    {
        "detector": "SPHEREx-D5",
        "band_idx": 5,
        "wave_min": 3.82,
        "wave_max": 4.42,
        "wave_eff": 4.120,
        "channel_count": 17,
        "color": "#ef4444",  # Red
    },
    {
        "detector": "SPHEREx-D6",
        "band_idx": 6,
        "wave_min": 4.42,
        "wave_max": 5.00,
        "wave_eff": 4.710,
        "channel_count": 17,
        "color": "#8b5cf6",  # Purple
    },
]

# Physical constants for Planck function: B_nu(T, lambda)
# h = 6.626e-34 J*s, c = 2.998e8 m/s, k = 1.381e-23 J/K
def planck_b_nu(wave_um: float, temp_k: float) -> float:
    """Computes relative Planck spectral radiance B_nu(T) for a given wavelength in microns."""
    if temp_k <= 0 or wave_um <= 0:
        return 0.0
    c1 = 1.438777e4  # h*c / k in micron*K
    nu = 2.99792e14 / wave_um  # frequency in Hz
    try:
        x = c1 / (wave_um * temp_k)
        if x > 200:
            return 0.0
        exp_val = np.exp(x) - 1.0
        if exp_val <= 0:
            return 0.0
        val = (nu**3) / exp_val
        return float(val)
    except Exception:
        return 0.0

def fit_blackbody_continuum(obs_measurements: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Fits a single-temperature Planck blackbody B_nu(T) to measured broad-band detector fluxes.
    Requires at least 3 distinct measured detector bands to provide positive residual degrees
    of freedom (dof >= 1) for a 2-parameter (amplitude + temperature) fit.
    Every input measurement must have a valid propagated photometric uncertainty.
    Never substitutes placeholder error estimates (e.g. 10% of flux).
    Returns status: "unavailable" when fit conditions, identifiability, or uncertainty calculation
    are inadequate.
    """
    has_missing_error = False
    valid_obs: List[Dict[str, Any]] = []

    for m in obs_measurements:
        flux = m.get("flux_mjy_sr")
        wave = m.get("wavelength_um")
        err = m.get("flux_err_mjy_sr")

        if flux is None or wave is None:
            continue
        try:
            flux_f = float(flux)
            wave_f = float(wave)
            if not np.isfinite(flux_f) or not np.isfinite(wave_f) or flux_f <= 0 or wave_f <= 0:
                continue
        except (ValueError, TypeError):
            continue

        if err is None:
            has_missing_error = True
            continue
        try:
            err_f = float(err)
            if not np.isfinite(err_f) or err_f <= 0:
                has_missing_error = True
                continue
        except (ValueError, TypeError):
            has_missing_error = True
            continue

        valid_obs.append({
            "detector": m.get("detector"),
            "wavelength_um": wave_f,
            "flux_mjy_sr": flux_f,
            "flux_err_mjy_sr": err_f,
        })

    if has_missing_error:
        return {
            "status": "unavailable",
            "temperature_k": None,
            "uncertainty_k": None,
            "reduced_chi2": None,
            "degrees_of_freedom": 0,
            "amplitude": None,
            "inputs": [
                {
                    "detector": m.get("detector"),
                    "wavelength_um": m.get("wavelength_um"),
                    "flux_mjy_sr": m.get("flux_mjy_sr"),
                    "flux_err_mjy_sr": m.get("flux_err_mjy_sr"),
                }
                for m in obs_measurements
                if m.get("flux_mjy_sr") is not None
            ],
            "model": "Single-temperature Planck blackbody continuum fit B_nu(T)",
            "limitations": "Missing valid propagated photometric uncertainty on one or more input measurements. Unsupported 10% error substitution is disallowed.",
            "reason": "Missing valid propagated photometric uncertainty on input measurements",
        }

    distinct_waves = np.unique(np.round([m["wavelength_um"] for m in valid_obs], 3))
    if len(distinct_waves) < 3 or len(valid_obs) < 3:
        dof_val = max(0, len(valid_obs) - 2)
        return {
            "status": "unavailable",
            "temperature_k": None,
            "uncertainty_k": None,
            "reduced_chi2": None,
            "degrees_of_freedom": dof_val,
            "amplitude": None,
            "inputs": [
                {
                    "detector": m.get("detector"),
                    "wavelength_um": round(float(m.get("wavelength_um", 0.0)), 4),
                    "flux_mjy_sr": round(float(m.get("flux_mjy_sr", 0.0)), 4),
                    "flux_err_mjy_sr": round(float(m.get("flux_err_mjy_sr", 0.0)), 4) if m.get("flux_err_mjy_sr") is not None else None,
                }
                for m in valid_obs
            ],
            "model": "Single-temperature Planck blackbody continuum fit B_nu(T)",
            "limitations": "Insufficient degrees of freedom. A two-parameter (amplitude + temperature) fit requires at least 3 distinct measured detector bands to provide positive residual degrees of freedom (dof >= 1).",
            "reason": "Insufficient observed detector bands (minimum 3 distinct bands required for dof >= 1)",
        }

    waves = np.array([m["wavelength_um"] for m in valid_obs], dtype=np.float64)
    fluxes = np.array([m["flux_mjy_sr"] for m in valid_obs], dtype=np.float64)
    errors = np.array([m["flux_err_mjy_sr"] for m in valid_obs], dtype=np.float64)

    def compute_chi2(t_val: float) -> Tuple[float, float]:
        b_vals = np.array([planck_b_nu(w, t_val) for w in waves], dtype=np.float64)
        if np.all(b_vals <= 0):
            return 1e12, 0.0
        weights = 1.0 / (errors ** 2)
        denom = float(np.sum(weights * (b_vals ** 2)))
        if denom <= 0:
            return 1e12, 0.0
        amp = max(0.0, float(np.sum(weights * fluxes * b_vals) / denom))
        residuals = fluxes - amp * b_vals
        chi2 = float(np.sum(weights * (residuals ** 2)))
        return chi2, amp

    grid_temps = np.geomspace(150.0, 12000.0, 120)
    best_chi2 = 1e12
    best_temp = 3000.0
    best_amp = 1.0

    for t_cand in grid_temps:
        c2, a_cand = compute_chi2(t_cand)
        if c2 < best_chi2:
            best_chi2 = c2
            best_temp = float(t_cand)
            best_amp = a_cand

    try:
        from scipy.optimize import minimize_scalar
        res = minimize_scalar(
            lambda t: compute_chi2(t)[0],
            bounds=(max(100.0, best_temp * 0.5), min(15000.0, best_temp * 2.0)),
            method="bounded"
        )
        if res.success and np.isfinite(res.fun):
            best_temp = float(res.x)
            best_chi2, best_amp = compute_chi2(best_temp)
    except Exception:
        pass

    dof = len(valid_obs) - 2

    if best_amp <= 0 or not np.isfinite(best_amp):
        return {
            "status": "unavailable",
            "temperature_k": None,
            "uncertainty_k": None,
            "reduced_chi2": None,
            "degrees_of_freedom": dof,
            "amplitude": None,
            "inputs": [
                {
                    "detector": m.get("detector"),
                    "wavelength_um": round(float(m["wavelength_um"]), 4),
                    "flux_mjy_sr": round(float(m["flux_mjy_sr"]), 4),
                    "flux_err_mjy_sr": round(float(m["flux_err_mjy_sr"]), 4),
                }
                for m in valid_obs
            ],
            "model": "Single-temperature Planck blackbody continuum fit B_nu(T)",
            "limitations": "Non-physical fit amplitude (amplitude <= 0).",
            "reason": "Non-physical fit amplitude",
        }

    dt = max(10.0, best_temp * 0.02)
    c_plus, _ = compute_chi2(best_temp + dt)
    c_minus, _ = compute_chi2(best_temp - dt)
    d2chi2 = (c_plus - 2.0 * best_chi2 + c_minus) / (dt ** 2)

    if d2chi2 <= 0 or not np.isfinite(d2chi2):
        return {
            "status": "unavailable",
            "temperature_k": None,
            "uncertainty_k": None,
            "reduced_chi2": None,
            "degrees_of_freedom": dof,
            "amplitude": None,
            "inputs": [
                {
                    "detector": m.get("detector"),
                    "wavelength_um": round(float(m["wavelength_um"]), 4),
                    "flux_mjy_sr": round(float(m["flux_mjy_sr"]), 4),
                    "flux_err_mjy_sr": round(float(m["flux_err_mjy_sr"]), 4),
                }
                for m in valid_obs
            ],
            "model": "Single-temperature Planck blackbody continuum fit B_nu(T)",
            "limitations": "Fit unidentifiable; chi-square curvature is non-positive across the temperature parameter space.",
            "reason": "Unconstrained chi-square curvature (temperature parameter not identifiable)",
        }

    temp_unc = float(np.sqrt(2.0 / d2chi2))
    if not np.isfinite(temp_unc) or temp_unc > best_temp * 3.0:
        return {
            "status": "unavailable",
            "temperature_k": None,
            "uncertainty_k": None,
            "reduced_chi2": None,
            "degrees_of_freedom": dof,
            "amplitude": None,
            "inputs": [
                {
                    "detector": m.get("detector"),
                    "wavelength_um": round(float(m["wavelength_um"]), 4),
                    "flux_mjy_sr": round(float(m["flux_mjy_sr"]), 4),
                    "flux_err_mjy_sr": round(float(m["flux_err_mjy_sr"]), 4),
                }
                for m in valid_obs
            ],
            "model": "Single-temperature Planck blackbody continuum fit B_nu(T)",
            "limitations": "Temperature uncertainty calculation is unconstrained across sampled bands.",
            "reason": "Temperature uncertainty unconstrained",
        }

    if best_temp <= 155.0 or best_temp >= 11950.0:
        return {
            "status": "unavailable",
            "temperature_k": None,
            "uncertainty_k": None,
            "reduced_chi2": None,
            "degrees_of_freedom": dof,
            "amplitude": None,
            "inputs": [
                {
                    "detector": m.get("detector"),
                    "wavelength_um": round(float(m["wavelength_um"]), 4),
                    "flux_mjy_sr": round(float(m["flux_mjy_sr"]), 4),
                    "flux_err_mjy_sr": round(float(m["flux_err_mjy_sr"]), 4),
                }
                for m in valid_obs
            ],
            "model": "Single-temperature Planck blackbody continuum fit B_nu(T)",
            "limitations": "Fit reached search boundary without a bounded physical minimum.",
            "reason": "Fit reached search boundary without a bounded minimum",
        }

    red_chi2 = best_chi2 / dof
    if not np.isfinite(red_chi2) or red_chi2 > 500.0:
        return {
            "status": "unavailable",
            "temperature_k": None,
            "uncertainty_k": None,
            "reduced_chi2": None,
            "degrees_of_freedom": dof,
            "amplitude": None,
            "inputs": [
                {
                    "detector": m.get("detector"),
                    "wavelength_um": round(float(m["wavelength_um"]), 4),
                    "flux_mjy_sr": round(float(m["flux_mjy_sr"]), 4),
                    "flux_err_mjy_sr": round(float(m["flux_err_mjy_sr"]), 4),
                }
                for m in valid_obs
            ],
            "model": "Single-temperature Planck blackbody continuum fit B_nu(T)",
            "limitations": "Fit quality inadequate (reduced chi-square exceeds threshold).",
            "reason": "Reduced chi-square exceeds threshold",
        }

    return {
        "status": "converged",
        "temperature_k": round(best_temp, 1),
        "uncertainty_k": round(temp_unc, 1),
        "reduced_chi2": round(red_chi2, 3),
        "degrees_of_freedom": dof,
        "amplitude": round(best_amp, 6),
        "inputs": [
            {
                "detector": m.get("detector"),
                "wavelength_um": round(float(m["wavelength_um"]), 4),
                "flux_mjy_sr": round(float(m["flux_mjy_sr"]), 4),
                "flux_err_mjy_sr": round(float(m["flux_err_mjy_sr"]), 4),
            }
            for m in valid_obs
        ],
        "model": "Single-temperature Planck blackbody continuum fit B_nu(T)",
        "limitations": "Single-temperature broadband continuum fit across measured broad-band detector filters; not an object's known physical temperature. Does not account for molecular absorption bands, non-LTE line physics, surface gravity, or multi-component dust emission.",
    }

def generate_spectrum_for_target(
    ra: float,
    dec: float,
    observations: List[Any],
    cutout_fetcher: Any,
    fov_deg: float = 0.04,
) -> Dict[str, Any]:
    """
    Computes calibrated Spectral Energy Distribution (SED: Flux vs. Wavelength) across
    the 6 SPHEREx detector arrays (0.75 - 5.00 µm) and all 102 individual spectroscopic channels.
    Measured detector bands are kept distinct from illustrative estimated continuum models.
    Physical claims are derived strictly from documented blackbody fits with explicit uncertainties
    and limitations, never from preset target identities or hardcoded names.
    """
    measured_by_detector: Dict[str, Dict[str, Any]] = {}

    # 1. Process available observations and extract aperture flux
    for obs in observations:
        det = obs.detector if hasattr(obs, "detector") else obs.get("detector")
        if not det:
            continue
        
        # Match detector name (e.g. SPHEREx-D1, SPHEREx-D3)
        matched_cfg = None
        for cfg in SPHEREX_DETECTOR_CONFIG:
            if cfg["detector"].lower() in det.lower():
                matched_cfg = cfg
                break
        if not matched_cfg:
            continue

        det_key = matched_cfg["detector"]
        
        b = None
        obs_id = obs.id if hasattr(obs, "id") else obs.get("id")
        obs_access = obs.access_url if hasattr(obs, "access_url") else obs.get("access_url")
        obs_ra = obs.ra if hasattr(obs, "ra") else obs.get("ra", ra)
        obs_dec = obs.dec if hasattr(obs, "dec") else obs.get("dec", dec)

        if not b and obs_id:
            from app.services.irsa_client import OBSERVATION_REGISTRY
            reg_item = OBSERVATION_REGISTRY.get(obs_id)
            if reg_item and "cached_cutout_url" in reg_item:
                from app.services.cache_service import cache_service
                b = cache_service.get(reg_item["cached_cutout_url"])

        if not b and obs_access:
            from app.services.demo_service import demo_service
            b = demo_service.get_cached_cutout_for_url(obs_access)
            if not b:
                from app.services.cache_service import cache_service
                exact_cutout_url = f"{obs_access}?center={obs_ra:.6f},{obs_dec:.6f}&size={fov_deg:.4f}"
                b = cache_service.get(exact_cutout_url)
                if not b:
                    exact_cutout_url_target = f"{obs_access}?center={ra:.6f},{dec:.6f}&size={fov_deg:.4f}"
                    b = cache_service.get(exact_cutout_url_target)
                if not b:
                    b = cache_service.get(obs_access)

        if b:
            try:
                hd = load_fits_cutout(b)
                img, hdr = extract_primary_image(hd, preserve_nan=True)
                from app.science.fits_processing import (
                    extract_variance_data,
                    extract_fatal_quality_mask,
                    extract_source_mask,
                    extract_calibrated_wavelength,
                )
                var = extract_variance_data(hd)
                mask = extract_fatal_quality_mask(hd)
                src_mask = extract_source_mask(hd)
                wave_cal = extract_calibrated_wavelength(hd, target_coord=(ra, dec))

                phot = compute_aperture_photometry(
                    image=img,
                    target_coord=(ra, dec),
                    wcs=hdr,
                    variance=var,
                    mask=mask,
                    source_mask=src_mask,
                )
                if not phot.get("valid", True) or phot.get("net_flux") is None:
                    continue

                snr = phot.get("snr", 0.0)

                if det_key not in measured_by_detector or snr > measured_by_detector[det_key]["snr"]:
                    meas_entry = {
                        "detector": det_key,
                        "wavelength_um": matched_cfg["wave_eff"],
                        "flux_mjy_sr": phot["net_flux"],
                        "peak_flux_mjy_sr": phot["peak_flux"],
                        "flux_err_mjy_sr": phot.get("flux_err", phot["background_std"]),
                        "snr": snr,
                        "obs_id": obs_id,
                        "observed": True,
                    }
                    if wave_cal is not None:
                        meas_entry["wavelength_um"] = wave_cal["wavelength_um"]
                        meas_entry["calibrated_wave_um"] = wave_cal["wavelength_um"]
                        meas_entry["bandwidth_um"] = wave_cal["bandwidth_um"]
                        meas_entry["calibration_source"] = wave_cal["calibration_method"]

                    measured_by_detector[det_key] = meas_entry
            except Exception:
                pass

    # 2. Documented physical fit from observed detector bands (no preset coordinates or identity matching)
    obs_list = list(measured_by_detector.values())
    bb_fit = fit_blackbody_continuum(obs_list)

    # 3. Build output for all 6 detector bands
    bands_output: List[Dict[str, Any]] = []

    for cfg in SPHEREX_DETECTOR_CONFIG:
        det_name = cfg["detector"]
        wave_eff = cfg["wave_eff"]
        calibrated_wave = None
        bandwidth_val = None
        cal_source = "Detector Nominal Bandpass"

        if det_name in measured_by_detector:
            meas = measured_by_detector[det_name]
            flux = float(meas["flux_mjy_sr"])
            peak = float(meas["peak_flux_mjy_sr"])
            err = float(meas["flux_err_mjy_sr"])
            snr = float(meas["snr"])
            is_obs = True
            obs_id_val = meas.get("obs_id")
            if "calibrated_wave_um" in meas:
                wave_eff = float(meas["calibrated_wave_um"])
                calibrated_wave = wave_eff
                bandwidth_val = meas.get("bandwidth_um")
                cal_source = meas.get("calibration_source", "WCS-WAVE")
            model_lbl = "Measured SPHEREx Detector Band"
            meas_status = "measured"
        else:
            # Illustrative estimated flux evaluated from documented blackbody fit or median observed scaling
            if bb_fit["status"] == "converged" and bb_fit.get("temperature_k") and bb_fit.get("amplitude"):
                b_val = planck_b_nu(wave_eff, float(bb_fit["temperature_k"]))
                flux = float(bb_fit["amplitude"]) * b_val
                model_lbl = "Estimated Continuum Model (Interpolated from Single-T Fit) - Illustrative Continuum, Never Observed Resolution"
                meas_status = "unobserved_estimated"
            elif obs_list:
                med_obs = float(np.median([m["flux_mjy_sr"] for m in obs_list]))
                flux = med_obs
                model_lbl = "Estimated Continuum Model (Interpolated from Observed Bands) - Illustrative Continuum, Never Observed Resolution"
                meas_status = "unobserved_estimated"
            else:
                flux = 0.05
                model_lbl = "Illustrative Placeholder Model (No Observed Archive Bands) - Never Observed Resolution"
                meas_status = "unobserved_placeholder"

            flux = max(0.01, float(flux))
            peak = flux * 1.3
            err = max(0.05, flux * 0.15)
            snr = round(flux / err, 1)
            is_obs = False
            obs_id_val = None

        flux_density_mjy = flux * 0.9035

        bands_output.append({
            "detector": det_name,
            "band_idx": cfg["band_idx"],
            "wavelength_um": round(wave_eff, 4),
            "wavelength_min_um": cfg["wave_min"],
            "wavelength_max_um": cfg["wave_max"],
            "bandwidth_um": bandwidth_val,
            "calibration_source": cal_source,
            "color": cfg["color"],
            "flux_mjy_sr": round(flux, 4),
            "flux_density_mjy": round(flux_density_mjy, 4),
            "peak_flux_mjy_sr": round(peak, 4),
            "flux_err_mjy_sr": round(err, 4),
            "snr": round(snr, 1),
            "is_observed": is_obs,
            "obs_id": obs_id_val,
            "measurement_status": meas_status,
            "model_label": model_lbl,
        })

    # 4. Illustrative 102 individual spectral channels across the 6 arrays
    channels_102: List[Dict[str, Any]] = []
    channel_global_idx = 1

    band_waves = np.array([b["wavelength_um"] for b in bands_output])
    band_fluxes = np.array([b["flux_mjy_sr"] for b in bands_output])
    log_band_w = np.log(band_waves)
    log_band_f = np.log(np.maximum(1e-4, band_fluxes))

    try:
        from scipy.interpolate import PchipInterpolator
        interp_model = PchipInterpolator(log_band_w, log_band_f, extrapolate=True)
        eval_flux = lambda lw: float(np.exp(interp_model(lw)))
    except Exception:
        eval_flux = lambda lw: float(np.exp(np.interp(lw, log_band_w, log_band_f)))

    for cfg in SPHEREX_DETECTOR_CONFIG:
        w_min = cfg["wave_min"]
        w_max = cfg["wave_max"]
        n_chan = cfg["channel_count"]  # 17
        waves = np.linspace(w_min, w_max, n_chan)
        det_obs = cfg["detector"] in measured_by_detector

        for w in waves:
            log_w = np.log(w)
            ch_flux = max(0.005, eval_flux(log_w))

            channels_102.append({
                "channel_index": channel_global_idx,
                "detector": cfg["detector"],
                "color": cfg["color"],
                "wavelength_um": round(float(w), 4),
                "flux_mjy_sr": round(ch_flux, 4),
                "flux_density_mjy": round(ch_flux * 0.9035, 4),
                "is_observed_band": det_obs,
                "is_observed": False,
                "is_interpolated": True,
                "model_label": "Estimated Continuum Model (Interpolated) - Illustrative Continuum, Never Observed Resolution",
            })
            channel_global_idx += 1

    # 5. Smooth continuum curve for SVG rendering
    continuum_eval_waves = np.linspace(0.75, 5.00, 60)
    continuum_curve: List[Dict[str, float]] = []

    for w in continuum_eval_waves:
        cf = max(0.005, eval_flux(np.log(w)))
        continuum_curve.append({
            "wavelength_um": round(float(w), 3),
            "flux_mjy_sr": round(cf, 4),
        })

    # 6. SED Summary and Empirical Physical Characterization
    observed_channels = [b for b in bands_output if b.get("is_observed")]

    # Neutral measured-shape descriptions only; unobserved synthetic peaks are NEVER called measured peaks
    if len(observed_channels) >= 2:
        obs_sorted = sorted(observed_channels, key=lambda b: b["wavelength_um"])
        f_first = obs_sorted[0]["flux_mjy_sr"]
        f_last = obs_sorted[-1]["flux_mjy_sr"]
        peak_band = max(observed_channels, key=lambda b: b["flux_mjy_sr"])
        w_peak = peak_band["wavelength_um"]
        det_peak = peak_band["detector"]

        if peak_band == obs_sorted[-1] and f_last > 1.2 * f_first:
            shape_desc = "flux rises toward longer measured bands"
        elif peak_band == obs_sorted[0] and f_first > 1.2 * f_last:
            shape_desc = "flux falls toward longer measured bands"
        elif peak_band != obs_sorted[0] and peak_band != obs_sorted[-1]:
            shape_desc = f"peak among measured detector bands ({w_peak:.2f} µm in {det_peak})"
        elif f_last > 1.2 * f_first:
            shape_desc = "flux rises toward longer measured bands"
        elif f_first > 1.2 * f_last:
            shape_desc = "flux falls toward longer measured bands"
        else:
            shape_desc = "broadband continuum without monotonic trend across measured bands"

        peak_wave_val: Optional[float] = round(peak_band["wavelength_um"], 4)
        peak_det_val: Optional[str] = peak_band["detector"]
        peak_flux_val: Optional[float] = round(peak_band["flux_mjy_sr"], 4)
        peak_is_measured = True
    elif len(observed_channels) == 1:
        peak_band = observed_channels[0]
        shape_desc = "insufficient observed coverage (single measured detector band; continuum slope unconstrained)"
        peak_wave_val = round(peak_band["wavelength_um"], 4)
        peak_det_val = peak_band["detector"]
        peak_flux_val = round(peak_band["flux_mjy_sr"], 4)
        peak_is_measured = True
    else:
        # Zero observed archive bands: make observed-data summary metrics unavailable!
        shape_desc = "insufficient observed coverage (no observed archive bands)"
        peak_wave_val = None
        peak_det_val = None
        peak_flux_val = None
        peak_is_measured = False

    if len(observed_channels) > 0:
        trapz_fn = getattr(np, "trapezoid", getattr(np, "trapz", None))
        if trapz_fn:
            total_flux_integral = float(trapz_fn(
                [c["flux_mjy_sr"] for c in channels_102],
                [c["wavelength_um"] for c in channels_102]
            ))
        else:
            ch_y = [c["flux_mjy_sr"] for c in channels_102]
            ch_x = [c["wavelength_um"] for c in channels_102]
            total_flux_integral = float(sum(0.5 * (ch_y[i] + ch_y[i+1]) * (ch_x[i+1] - ch_x[i]) for i in range(len(ch_x)-1)))
        total_flux_integral = round(total_flux_integral, 3)
    else:
        total_flux_integral = None

    estimated_temp = int(round(bb_fit["temperature_k"])) if bb_fit.get("temperature_k") is not None else None

    continuum_classification = {
        "continuum_shape": shape_desc,
        "classification_type": "broadband_continuum_shape",
        "method": "Empirical broad-band continuum shape across measured SPHEREx detector bands",
        "observed_bands_count": len(observed_channels),
        "statement": "Broadband continuum shape only; not an astrophysical classification.",
        "inputs": [
            {
                "detector": b.get("detector"),
                "wavelength_um": b.get("wavelength_um"),
                "flux_mjy_sr": b.get("flux_mjy_sr"),
            }
            for b in observed_channels
        ],
        "limitations": "Empirical broad-band continuum shape across measured detector bands; not an astrophysical classification or spectral type. Definitive classification requires resolved spectroscopic absorption features.",
    }

    return {
        "target": {"ra": round(ra, 6), "dec": round(dec, 6)},
        "total_observed_bands": len(measured_by_detector),
        "total_observed_channels": len(observed_channels),
        "observed_channels": observed_channels,
        "observed_detector_bands": observed_channels,
        "bands": bands_output,
        "channels_102": channels_102,
        "estimated_channels_102": channels_102,
        "continuum_curve": continuum_curve,
        "continuum_model_label": "Estimated Continuum Model (Interpolated) - Illustrative Continuum, Never Observed Resolution",
        "temperature_fit": bb_fit,
        "continuum_classification": continuum_classification,
        "summary": {
            "peak_wavelength_um": peak_wave_val,
            "peak_detector": peak_det_val,
            "peak_flux_mjy_sr": peak_flux_val,
            "peak_is_measured": peak_is_measured,
            "estimated_temperature_k": estimated_temp,
            "continuum_shape": shape_desc,
            "temperature_fit": bb_fit,
            "continuum_classification": continuum_classification,
            "integrated_flux_mjy_sr_um": total_flux_integral,
            "total_channels": len(channels_102),
            "estimated_channels_count": len(channels_102),
            "continuum_model_label": "Estimated Continuum Model (Interpolated) - Illustrative Continuum, Never Observed Resolution",
            "observed_channels_count": len(observed_channels),
            "observed_bands_count": len(observed_channels),
        },
    }
