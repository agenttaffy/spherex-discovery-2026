from typing import Dict, Any, Optional
from datetime import datetime
from app.science.coordinates import format_sexagesimal

def generate_discovery_report(
    target_name: str,
    ra_deg: float,
    dec_deg: float,
    target_type: Optional[str] = None,
    motion_data: Optional[Dict[str, Any]] = None,
    photometry_data: Optional[Dict[str, Any]] = None,
    observations: Optional[list] = None,
    notes: Optional[str] = None,
    spectrum_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Builds a structured scientific discovery report with J2000 sexagesimal formatting,
    astrometric vectors, photometric variability indices, and IRSA archive DOIs.
    """
    sex_coord = format_sexagesimal(ra_deg, dec_deg)
    now_iso = datetime.utcnow().isoformat() + "Z"

    # Compile Markdown Document
    md_lines = [
        f"# SPHEREx Discovery Report: {target_name}",
        f"**Generated:** {now_iso} | **Platform:** SPHEREx Discovery Engine (NASA Space Apps Challenge 2026)",
        "",
        "## 1. Astronomical Target Information",
        f"- **Designation / Target Name:** {target_name}",
        f"- **Coordinates (J2000):** RA {ra_deg:.6f}°, Dec {dec_deg:.6f}° (`{sex_coord}`)",
        f"- **Candidate Classification:** {target_type or 'Astronomical Source'}",
        "",
        "## 2. Multi-Epoch Observation Provenance",
        f"- **Data Archive:** NASA/IPAC Infrared Science Archive (IRSA)",
        f"- **Level 2 Science Archive DOI:** [10.26131/IRSA678](https://doi.org/10.26131/IRSA678)",
        f"- **Instrument:** SPHEREx (Spectro-Photometer for the History of the Universe, Epoch of Reionization and Ices)",
        f"- **Spectrophotometric Range:** 0.75 μm – 5.0 μm (Detectors D1–D6 Linear Variable Filters)",
    ]

    if observations:
        md_lines.append("")
        md_lines.append("### Evaluated Observation Epochs")
        md_lines.append("| Obs ID | UTC Date | Collection | Detector | MJD |")
        md_lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for obs in observations[:8]:
            md_lines.append(f"| `{obs.get('obs_id', 'N/A')}` | {obs.get('utc_date', 'N/A')} | {obs.get('collection', 'N/A')} | {obs.get('detector', 'N/A')} | {obs.get('mjd', 'N/A')} |")

    # Astrometric Motion Analysis
    if motion_data:
        md_lines.extend([
            "",
            "## 3. Astrometric Motion & Centroid Analysis",
            f"- **Motion Classification:** **{motion_data.get('motion_class', 'N/A')}**",
            f"- **Angular Displacement:** {motion_data.get('displacement_arcsec', 0.0):.3f} arcsec ({motion_data.get('displacement_pixels', 0.0):.3f} pixels)",
            f"- **Shift Vectors:** Δx = {motion_data.get('dx_pixels', 0.0):.3f} px, Δy = {motion_data.get('dy_pixels', 0.0):.3f} px",
            f"- **Position Angle (North through East):** {motion_data.get('position_angle_deg', 0.0):.1f}°",
            f"- **Time Baseline:** {motion_data.get('delta_time_days', 0.0):.1f} days ({motion_data.get('delta_time_years', 0.0):.3f} years)",
            f"- **Calculated Proper Motion:** **{motion_data.get('proper_motion_arcsec_yr', 0.0):.3f} arcsec/year** ({motion_data.get('proper_motion_mas_yr', 0.0):.1f} mas/yr)",
            f"- **Centroid Detection Confidence:** {float(motion_data.get('confidence_score', 0.0))*100:.0f}%",
        ])
        if "pm_ra_cosdec_mas_yr" in motion_data and "pm_dec_mas_yr" in motion_data:
            md_lines.append(
                f"- **Equatorial Vector Components:** μα* = {motion_data['pm_ra_cosdec_mas_yr']:.1f} mas/yr, μδ = {motion_data['pm_dec_mas_yr']:.1f} mas/yr"
            )
        if motion_data.get("wcs_tracking"):
            md_lines.append("- **Astrometric Calibration:** WCS-anchored centroiding with pointing-shift isolation")

    # Photometric Variability Analysis
    if photometry_data:
        md_lines.extend([
            "",
            "## 4. Photometric Light Curve Analysis",
            f"- **Variability Assessment:** **{'CONFIRMED VARIABLE' if photometry_data.get('is_variable') else 'STABLE / NON-VARIABLE'}**",
            f"- **Total Epoch Points:** {photometry_data.get('total_points', 0)}",
            f"- **Variability Index (std/mean):** {photometry_data.get('variability_index', 0.0):.3f}",
            f"- **Mean Net Flux:** {photometry_data.get('mean_flux_mjy_sr', 0.0):.4f} MJy/sr",
            f"- **Peak Flux Observed:** {photometry_data.get('max_flux_mjy_sr', 0.0):.4f} MJy/sr",
            f"- **Flux Range (ΔF):** {photometry_data.get('amplitude_delta_mjy_sr', 0.0):.4f} MJy/sr",
        ])

    # Spectral Energy Distribution Analysis
    if spectrum_data:
        obs_bands = spectrum_data.get("observed_channels") or spectrum_data.get("observed_detector_bands") or []
        total_obs = spectrum_data.get("total_observed_bands", len(obs_bands))
        summary = spectrum_data.get("summary", {})
        shape_desc = summary.get("continuum_shape") or "insufficient observed coverage"
        bb_fit = spectrum_data.get("temperature_fit") or summary.get("temperature_fit") or {}

        md_lines.extend([
            "",
            "## 5. Spectral Energy Distribution (SED)",
            f"- **Observed Detector Bands:** {total_obs} of 6 bands (calibrated WCS-WAVE where available)",
            "- **Spectrophotometric Continuum:** Estimated Continuum Model (Interpolated across 6 detector bandpasses)",
            "- **Spectral Line Caveat:** The 102 individual channel values represent an interpolated continuum curve across the 6 SPHEREx detector arrays, not 102 independently resolved spectral line measurements.",
            f"- **Broadband Continuum Shape:** {shape_desc} (Note: broadband continuum shape across measured detector bands, not an astrophysical classification)",
        ])

        if bb_fit.get("status") == "converged" and bb_fit.get("temperature_k") is not None:
            unc_str = f"± {bb_fit.get('uncertainty_k')} K" if bb_fit.get("uncertainty_k") is not None else "uncertainty unconstrained"
            stats_parts = []
            if bb_fit.get("reduced_chi2") is not None:
                stats_parts.append(f"reduced χ² = {bb_fit['reduced_chi2']}")
            if bb_fit.get("degrees_of_freedom") is not None:
                stats_parts.append(f"dof = {bb_fit['degrees_of_freedom']}")
            stats_str = f" ({', '.join(stats_parts)})" if stats_parts else ""
            md_lines.append(
                f"- **Single-Temperature Blackbody Continuum Fit:** T = {bb_fit['temperature_k']} {unc_str}{stats_str}. Note: Single-temperature broadband continuum fit; not an object's known physical temperature."
            )
        else:
            limit_reason = bb_fit.get("reason") or bb_fit.get("limitations") or "Insufficient observed detector bands (minimum 3 distinct bands with propagated errors required for dof >= 1)"
            md_lines.append(
                f"- **Single-Temperature Blackbody Continuum Fit:** Unavailable ({limit_reason})"
            )

        if total_obs == 0:
            md_lines.append(
                "- **Archive Coverage Status:** No observed archive bands available. Summary metrics (peak wavelength, peak flux, temperature fit) are unavailable."
            )
        elif obs_bands:
            md_lines.append("")
            md_lines.append("### Observed Detector Photometry")
            md_lines.append("| Detector | λ_eff (μm) | Net Flux (MJy/sr) | ± Uncertainty | Calibration |")
            md_lines.append("| :--- | :--- | :--- | :--- | :--- |")
            for b in obs_bands:
                md_lines.append(
                    f"| {b.get('detector', 'N/A')} | {b.get('wavelength_um', 0.0):.3f} | {b.get('flux_mjy_sr', 0.0):.4f} | ±{b.get('flux_err_mjy_sr', 0.0):.4f} | {b.get('calibration_source', 'WCS-WAVE')} |"
                )

    if notes:
        section_num = "6" if spectrum_data else "5"
        md_lines.extend([
            "",
            f"## {section_num}. Analyst Notes & Scientific Interpretation",
            notes,
        ])

    md_lines.extend([
        "",
        "---",
        "**Citation:** NASA/IPAC Infrared Science Archive (IRSA), SPHEREx Data Release 1 & Quick Release 3 (DOI: 10.26131/IRSA678). Produced with SPHEREx Discovery.",
    ])

    markdown_content = "\n".join(md_lines)

    return {
        "report_id": f"SPX-REP-{int(datetime.utcnow().timestamp())}",
        "timestamp": now_iso,
        "target": {
            "name": target_name,
            "ra_deg": ra_deg,
            "dec_deg": dec_deg,
            "sexagesimal": sex_coord,
            "target_type": target_type,
        },
        "motion_analysis": motion_data,
        "photometry_analysis": photometry_data,
        "spectrum_analysis": spectrum_data,
        "observations_summary": observations[:10] if observations else [],
        "markdown_report": markdown_content,
        "irsa_doi": "10.26131/IRSA678",
    }
