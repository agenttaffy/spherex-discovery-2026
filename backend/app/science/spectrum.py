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
        # B_nu = (2*h*nu^3 / c^2) / (exp(h*nu/kT) - 1)
        val = (nu**3) / exp_val
        return float(val)
    except Exception:
        return 0.0

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
        
        # If we already have a measurement with higher SNR for this detector, continue
        # Otherwise fetch cutout
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
                img, hdr = extract_primary_image(hd)
                from app.science.fits_processing import (
                    extract_variance_data,
                    extract_fatal_quality_mask,
                    extract_calibrated_wavelength,
                )
                var = extract_variance_data(hd)
                mask = extract_fatal_quality_mask(hd)
                wave_cal = extract_calibrated_wavelength(hd, target_coord=(ra, dec))

                phot = compute_aperture_photometry(
                    image=img,
                    target_coord=(ra, dec),
                    wcs=hdr,
                    variance=var,
                    mask=mask,
                )
                snr = phot.get("snr", 0.0)

                if det_key not in measured_by_detector or snr > measured_by_detector[det_key]["snr"]:
                    meas_entry = {
                        "flux_mjy_sr": phot["net_flux"],
                        "peak_flux_mjy_sr": phot["peak_flux"],
                        "flux_err_mjy_sr": phot.get("flux_err", phot["background_std"]),
                        "snr": snr,
                        "obs_id": obs_id,
                        "observed": True,
                    }
                    if wave_cal is not None:
                        meas_entry["calibrated_wave_um"] = wave_cal["wavelength_um"]
                        meas_entry["bandwidth_um"] = wave_cal["bandwidth_um"]
                        meas_entry["calibration_source"] = wave_cal["calibration_method"]

                    measured_by_detector[det_key] = meas_entry
            except Exception:
                pass

    # 2. Check for preset physical priors if coordinates match known demo targets
    preset_type = None
    # Barnard's Star (RA ~ 269.452, Dec ~ 4.693)
    if abs(ra - 269.45208) < 0.05 and abs(dec - 4.69339) < 0.05:
        preset_type = "barnards_star"
    # WISE 0855 (RA ~ 133.795, Dec ~ -7.245)
    elif abs(ra - 133.79513) < 0.05 and abs(dec - (-7.24515)) < 0.05:
        preset_type = "wise_0855"
    # RW Aurigae (RA ~ 76.954, Dec ~ 30.401)
    elif abs(ra - 76.95420) < 0.05 and abs(dec - 30.40140) < 0.05:
        preset_type = "rw_aurigae"
    # R Draconis (RA ~ 248.338, Dec ~ 66.704)
    elif abs(ra - 248.33750) < 0.05 and abs(dec - 66.70420) < 0.05:
        preset_type = "r_draconis"
    # Epsilon Indi B (RA ~ 330.840, Dec ~ -56.786)
    elif abs(ra - 330.84000) < 0.05 and abs(dec - (-56.78600)) < 0.05:
        preset_type = "epsilon_indi_b"

    # 3. Model continuum SED across all 6 detector bands
    # If we have some measurements, determine scaling
    observed_detectors = list(measured_by_detector.keys())
    
    # Estimate representative temperature or spectral model
    temp_k = 3000.0  # default typical cool star
    if preset_type == "wise_0855":
        temp_k = 260.0  # Cold Y-dwarf
    elif preset_type == "barnards_star":
        temp_k = 3150.0  # M4V
    elif preset_type == "rw_aurigae":
        temp_k = 4200.0  # T Tauri + warm dust
    elif preset_type == "r_draconis":
        temp_k = 2800.0  # Mira giant
    elif preset_type == "epsilon_indi_b":
        temp_k = 1300.0  # T-dwarf
    elif len(observed_detectors) >= 2:
        # Robust color ratio across shortest and longest observed wavelengths
        obs_cfgs = [c for c in SPHEREX_DETECTOR_CONFIG if c["detector"] in measured_by_detector]
        obs_cfgs.sort(key=lambda c: c["wave_eff"])
        c_short = obs_cfgs[0]
        c_long = obs_cfgs[-1]
        f_short = measured_by_detector[c_short["detector"]].get("flux_mjy_sr")
        f_long = measured_by_detector[c_long["detector"]].get("flux_mjy_sr")
        if f_short and f_long and f_short > 0 and f_long > 0:
            ratio = f_long / f_short
            if ratio > 1.8:
                temp_k = 450.0  # cold IR source / brown dwarf
            elif ratio < 0.6:
                temp_k = 4800.0  # warm stellar continuum
            else:
                temp_k = 2800.0

    # Calculate scale factor to match measured flux
    scale_factor = 1.0
    if measured_by_detector:
        # Fit scale factor based on observed detector fluxes
        scales = []
        for det_name, m in measured_by_detector.items():
            cfg = next((c for c in SPHEREX_DETECTOR_CONFIG if c["detector"] == det_name), None)
            if cfg and m["flux_mjy_sr"] > 0:
                # Special astrophysical shapes for presets
                if preset_type == "wise_0855":
                    # Y dwarf: strong suppression < 3.5 um, huge peak in D5/D6 (4.5 um)
                    eff_lambda = cfg["wave_eff"]
                    if eff_lambda < 2.5:
                        model_shape = 0.05
                    elif eff_lambda < 3.8:
                        model_shape = 0.8
                    else:
                        model_shape = 12.0
                elif preset_type == "rw_aurigae":
                    # T Tauri with IR excess: optical star + mid-IR dust plateau
                    eff_lambda = cfg["wave_eff"]
                    model_shape = (eff_lambda / 1.0) ** (-0.5) + 0.8 * (eff_lambda / 3.0) ** 1.5
                else:
                    b_val = planck_b_nu(cfg["wave_eff"], temp_k)
                    model_shape = b_val if b_val > 0 else 1.0
                
                if model_shape > 0:
                    scales.append(m["flux_mjy_sr"] / model_shape)
        if scales:
            scale_factor = float(np.median(scales))

    # 4. Build output for all 6 detector bands
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
        else:
            # Model synthetic flux based on physical profile
            if preset_type == "wise_0855":
                if wave_eff < 2.5:
                    model_shape = 0.05
                elif wave_eff < 3.8:
                    model_shape = 0.8
                else:
                    model_shape = 12.0
                flux = scale_factor * model_shape
            elif preset_type == "rw_aurigae":
                model_shape = (wave_eff / 1.0) ** (-0.5) + 0.8 * (wave_eff / 3.0) ** 1.5
                flux = scale_factor * model_shape
            else:
                b_val = planck_b_nu(wave_eff, temp_k)
                ref_b = planck_b_nu(2.0, temp_k) or 1.0
                model_shape = (b_val / ref_b)
                flux = scale_factor * model_shape

            flux = max(0.01, float(flux))
            peak = flux * 1.4
            err = max(0.05, flux * 0.08)
            snr = round(flux / err, 1)
            is_obs = False
            obs_id_val = None

        # Point source conversion: 1 MJy/sr ~ 0.9035 mJy for SPHEREx pixel solid angle
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
        })

    # 5. Synthesize 102 individual spectral channels across the 6 arrays
    channels_102: List[Dict[str, Any]] = []
    channel_global_idx = 1
    
    # We will interpolate across the 6 band center flux values
    band_waves = np.array([b["wavelength_um"] for b in bands_output])
    band_fluxes = np.array([b["flux_mjy_sr"] for b in bands_output])
    log_band_w = np.log(band_waves)
    log_band_f = np.log(np.maximum(1e-4, band_fluxes))

    # Interpolation model in log-log space
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
                "model_label": "Estimated Continuum Model (Interpolated)",
            })
            channel_global_idx += 1

    # 6. Smooth continuum curve for SVG rendering (e.g. 60 evaluation points)
    continuum_eval_waves = np.linspace(0.75, 5.00, 60)
    continuum_curve: List[Dict[str, float]] = []
    
    for w in continuum_eval_waves:
        cf = max(0.005, eval_flux(np.log(w)))
        continuum_curve.append({
            "wavelength_um": round(float(w), 3),
            "flux_mjy_sr": round(cf, 4),
        })

    # 7. SED Summary and Physical Characterization
    peak_band = max(bands_output, key=lambda b: b["flux_mjy_sr"])
    min_band = min(bands_output, key=lambda b: b["flux_mjy_sr"])
    trapz_fn = getattr(np, "trapezoid", getattr(np, "trapz", None))
    if trapz_fn:
        total_flux_integral = float(trapz_fn(
            [c["flux_mjy_sr"] for c in channels_102],
            [c["wavelength_um"] for c in channels_102]
        ))
    else:
        # Manual trapezoidal integration fallback
        ch_y = [c["flux_mjy_sr"] for c in channels_102]
        ch_x = [c["wavelength_um"] for c in channels_102]
        total_flux_integral = float(sum(0.5 * (ch_y[i] + ch_y[i+1]) * (ch_x[i+1] - ch_x[i]) for i in range(len(ch_x)-1)))

    # Classify spectral energy distribution
    if peak_band["wavelength_um"] >= 4.0 and min_band["wavelength_um"] <= 1.5 and (peak_band["flux_mjy_sr"] > 3.0 * min_band["flux_mjy_sr"]):
        spec_class = "Cold Sub-stellar / Brown Dwarf (Strong Mid-IR Peak)"
    elif peak_band["wavelength_um"] <= 1.5 and peak_band["flux_mjy_sr"] > 2.0 * bands_output[-1]["flux_mjy_sr"]:
        spec_class = "Cool Stellar Atmosphere (M-Dwarf / Optical Continuum)"
    elif bands_output[-1]["flux_mjy_sr"] > bands_output[0]["flux_mjy_sr"] * 1.5:
        spec_class = "Infrared Excess (Circumstellar Dust / Protoplanetary Disk)"
    else:
        spec_class = "Broadband Infrared Continuum Source"

    observed_channels = [b for b in bands_output if b.get("is_observed")]

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
        "continuum_model_label": "Estimated Continuum Model (Interpolated)",
        "summary": {
            "peak_wavelength_um": peak_band["wavelength_um"],
            "peak_detector": peak_band["detector"],
            "peak_flux_mjy_sr": peak_band["flux_mjy_sr"],
            "estimated_temperature_k": int(temp_k),
            "spectral_class": spec_class,
            "integrated_flux_mjy_sr_um": round(total_flux_integral, 3),
            "total_channels": len(channels_102),
            "estimated_channels_count": len(channels_102),
            "continuum_model_label": "Estimated Continuum Model (Interpolated)",
            "observed_channels_count": len(observed_channels),
            "observed_bands_count": len(observed_channels),
        },
    }
