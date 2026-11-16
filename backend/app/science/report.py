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
        "- **Search provenance:** See each observation below. A cached demonstration result is not a live search result; image bytes may also come from cache.",
    ]

    if observations:
        md_lines.append("")
        md_lines.append("### Evaluated Observation Epochs")
        md_lines.append("| Obs ID | UTC Date | Collection | Detector | MJD | Search provenance |")
        md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for obs in observations[:8]:
            md_lines.append(f"| `{obs.get('obs_id', 'N/A')}` | {obs.get('utc_date', 'N/A')} | {obs.get('collection', 'N/A')} | {obs.get('detector', 'N/A')} | {obs.get('mjd', 'N/A')} | {obs.get('search_provenance', 'unknown')} |")

    # Client-supplied shifts are not proof that the same source was tracked.
    if motion_data:
        md_lines.extend(["", "## 3. Astrometric Motion", "- Automatic motion measurement is unavailable until source association, wavelength compatibility, image quality and astrometric uncertainties are independently validated."])

    # Photometric Variability Analysis
    if photometry_data and photometry_data.get("valid_points_count") == 0:
        md_lines.extend(["", "## 4. Photometric Light Curve Analysis", "- No valid photometry available; summary values and variability assessment are unavailable."])
    elif photometry_data:
        md_lines.extend([
            "",
            "## 4. Photometric Light Curve Analysis",
            f"- **Variability Heuristic:** **{'Variation flagged' if photometry_data.get('is_variable') else 'No variation flagged'}**. This threshold does not establish variability or stability; review wavelength compatibility and uncertainties.",
            f"- **Total Epoch Points:** {photometry_data.get('total_points', 0)}",
            f"- **Variability Index (std/mean):** {photometry_data.get('variability_index', 0.0):.3f}",
            f"- **Mean field aperture sum:** {photometry_data.get('mean_flux_mjy_sr', 0.0):.4f} (MJy/sr)·pixels",
            f"- **Peak field aperture sum:** {photometry_data.get('max_flux_mjy_sr', 0.0):.4f} (MJy/sr)·pixels",
            f"- **Aperture-sum range:** {photometry_data.get('amplitude_delta_mjy_sr', 0.0):.4f} (MJy/sr)·pixels",
        ])

    # Field samples are not calibrated source spectrophotometry.
    if spectrum_data:
        obs_bands = spectrum_data.get("observed_channels") or spectrum_data.get("observed_detector_bands") or []
        md_lines.extend([
            "", "## 5. Detector Field Samples",
            f"- **Available detector samples:** {len(obs_bands)} of 6.",
            "- Samples are background-subtracted sums of surface-brightness pixels, not calibrated source flux densities. They may come from different dates and do not confirm source identity.",
            "- A resolved source spectrum, continuum shape, integrated source flux and temperature are unavailable from these samples.",
        ])
        if obs_bands:
            md_lines.extend(["", "| Detector | Approx. wavelength (µm) | Aperture sum ((MJy/sr)·pixels) | Uncertainty | Calibration |", "| :--- | :--- | :--- | :--- | :--- |"])
            for band in obs_bands:
                md_lines.append(
                    f"| {band.get('detector', 'N/A')} | {band.get('wavelength_um', 0.0):.3f} | {band.get('flux_mjy_sr', 0.0):.4f} | {band.get('flux_err_mjy_sr', 0.0):.4f} | {band.get('calibration_source', 'unknown')} |"
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
