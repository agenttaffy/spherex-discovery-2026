#!/usr/bin/env python3
"""
scripts/audit_demo_manifest.py
SPHEREx Demo-Data Audit Tool

A read-only command-line audit tool that verifies manifest coverage,
schema integrity, cache presence, FITS readability, pixel statistics,
and WCS coordinate consistency for the offline demonstration dataset.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import sys
import urllib.parse
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u

# Ensure backend modules can be imported
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from app.science.fits_processing import (
    calculate_pixel_stats,
    extract_astropy_wcs,
    extract_primary_image,
    load_fits_cutout,
)
from app.services.cache_service import CacheService

Severity = Literal["PASS", "WARN", "FAIL"]


@dataclass
class Finding:
    severity: Severity
    category: str
    message: str
    entry_index: Optional[int] = None
    target_name: Optional[str] = None
    obs_id: Optional[str] = None
    detector: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntryAudit:
    index: int
    target_name: str
    collection: str
    obs_id: str
    detector: str
    utc_date: str
    ra: float
    dec: float
    cutout_url: str
    status: Severity
    cache_path: Optional[str] = None
    dimensions: Optional[List[int]] = None
    actual_dimensions: Optional[List[int]] = None
    finite_pixels: Optional[int] = None
    total_pixels: Optional[int] = None
    finite_pct: Optional[float] = None
    fresh_stats: Optional[Dict[str, float]] = None
    recorded_stats: Optional[Dict[str, float]] = None
    stat_discrepancies: Dict[str, Dict[str, float]] = field(default_factory=dict)
    wcs_valid: bool = False
    wcs_center_offset_arcsec: Optional[float] = None
    target_pixel_coords: Optional[Tuple[float, float]] = None
    target_inside_bounds: Optional[bool] = None
    has_flags: bool = False
    has_wcs_wave: bool = False
    findings: List[Finding] = field(default_factory=list)


@dataclass
class AuditReport:
    manifest_path: str
    cache_dir: str
    total_entries: int
    pass_count: int
    warn_count: int
    fail_count: int
    overall_status: Severity
    coverage: Dict[str, Dict[str, int]]
    findings: List[Finding]
    entries: List[EntryAudit]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "manifest_path": self.manifest_path,
                "cache_dir": self.cache_dir,
                "total_entries": self.total_entries,
                "pass_count": self.pass_count,
                "warn_count": self.warn_count,
                "fail_count": self.fail_count,
                "overall_status": self.overall_status,
                "coverage": self.coverage,
                "coverage_disclaimer": (
                    "Coverage counts reflect offline demonstration assets only; "
                    "target identity and astrophysical motion have not been independently validated."
                ),
            },
            "findings": [asdict(f) for f in self.findings],
            "entries": [asdict(e) for e in self.entries],
        }


class NpEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def compute_cache_key_path(cache_dir: Path, url: str) -> Path:
    """Return the expected cached FITS file path using the application's SHA-256 scheme."""
    hashed = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_dir / f"{hashed}.fits"


def validate_manifest_schema_entry(
    idx: int, item: Any
) -> Tuple[bool, List[Finding]]:
    findings: List[Finding] = []
    if not isinstance(item, dict):
        findings.append(
            Finding(
                severity="FAIL",
                category="schema",
                entry_index=idx,
                message=f"Manifest entry #{idx} is not a dictionary/object.",
            )
        )
        return False, findings

    target_name = item.get("target_name")
    obs_id = item.get("obs_id")
    detector = item.get("detector")

    def add_fail(msg: str, details: Optional[Dict[str, Any]] = None):
        findings.append(
            Finding(
                severity="FAIL",
                category="schema",
                entry_index=idx,
                target_name=str(target_name) if target_name else None,
                obs_id=str(obs_id) if obs_id else None,
                detector=str(detector) if detector else None,
                message=msg,
                details=details or {},
            )
        )

    def add_warn(msg: str, details: Optional[Dict[str, Any]] = None):
        findings.append(
            Finding(
                severity="WARN",
                category="schema",
                entry_index=idx,
                target_name=str(target_name) if target_name else None,
                obs_id=str(obs_id) if obs_id else None,
                detector=str(detector) if detector else None,
                message=msg,
                details=details or {},
            )
        )

    # Required fields presence and types
    required_str_fields = ["target_name", "collection", "obs_id", "detector"]
    for field_name in required_str_fields:
        val = item.get(field_name)
        if val is None or not isinstance(val, str) or len(val.strip()) == 0:
            add_fail(f"Missing or invalid required string field '{field_name}'.")

    # Coordinates
    ra = item.get("ra")
    if ra is None or not isinstance(ra, (int, float)) or isinstance(ra, bool) or not math.isfinite(ra):
        add_fail(f"Field 'ra' must be a finite float/int; got {ra!r}.")
    elif not (0.0 <= float(ra) <= 360.0):
        add_fail(f"Field 'ra' out of bounds [0, 360]: {ra}.")

    dec = item.get("dec")
    if dec is None or not isinstance(dec, (int, float)) or isinstance(dec, bool) or not math.isfinite(dec):
        add_fail(f"Field 'dec' must be a finite float/int; got {dec!r}.")
    elif not (-90.0 <= float(dec) <= 90.0):
        add_fail(f"Field 'dec' out of bounds [-90, +90]: {dec}.")

    # UTC Date
    utc_date = item.get("utc_date")
    if not isinstance(utc_date, str) or not utc_date.strip():
        add_fail(f"Missing or invalid required ISO UTC date string 'utc_date'.")
    else:
        try:
            # Normalize ISO string with 'Z' if needed for fromisoformat
            clean_date = utc_date.rstrip("Z")
            datetime.datetime.fromisoformat(clean_date)
        except Exception:
            add_fail(f"Field 'utc_date' is not a valid ISO 8601 timestamp: '{utc_date}'.")

    # Cutout URL
    url = item.get("cutout_url")
    if not isinstance(url, str) or not url.strip():
        add_fail(f"Missing or invalid required URL string 'cutout_url'.")
    else:
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or parsed.scheme not in ("http", "https") or not parsed.netloc:
            add_fail(f"Field 'cutout_url' is not a valid HTTP/HTTPS URL: '{url}'.")

    # Optional dimensions
    if "dimensions" in item:
        dims = item["dimensions"]
        if (
            not isinstance(dims, list)
            or len(dims) != 2
            or not all(isinstance(d, int) and d > 0 and not isinstance(d, bool) for d in dims)
        ):
            add_fail(f"Optional field 'dimensions' must be a list of 2 positive integers [height, width]; got {dims!r}.")

    # Optional pixel_stats
    if "pixel_stats" in item:
        stats = item["pixel_stats"]
        if not isinstance(stats, dict):
            add_fail(f"Optional field 'pixel_stats' must be a dict; got {type(stats).__name__}.")
        else:
            for s_key in ["min_mjy_sr", "max_mjy_sr", "mean_mjy_sr", "std_mjy_sr", "median_mjy_sr"]:
                if s_key in stats:
                    s_val = stats[s_key]
                    if not isinstance(s_val, (int, float)) or isinstance(s_val, bool) or not math.isfinite(s_val):
                        add_fail(f"Statistic '{s_key}' in 'pixel_stats' must be a finite float; got {s_val!r}.")
            if "min_mjy_sr" in stats and "max_mjy_sr" in stats:
                if stats["min_mjy_sr"] > stats["max_mjy_sr"]:
                    add_fail(f"Statistic min ({stats['min_mjy_sr']}) > max ({stats['max_mjy_sr']}).")
            if "std_mjy_sr" in stats and stats["std_mjy_sr"] < 0:
                add_fail(f"Statistic std_mjy_sr cannot be negative; got {stats['std_mjy_sr']}.")

    has_fatal = any(f.severity == "FAIL" for f in findings)
    return not has_fatal, findings


def audit_manifest(
    manifest_path: str | Path,
    cache_dir: str | Path,
    strict_warnings: bool = False,
    stat_tolerance: float = 1e-3,
) -> AuditReport:
    """
    Perform a read-only audit of the demonstration manifest and cached FITS files.
    """
    manifest_path = Path(manifest_path).resolve()
    cache_dir = Path(cache_dir).resolve()

    findings: List[Finding] = []
    entry_audits: List[EntryAudit] = []

    # 1. Manifest file existence and structure
    if not manifest_path.is_file():
        findings.append(
            Finding(
                severity="FAIL",
                category="manifest",
                message=f"Manifest file does not exist or is not a regular file: {manifest_path}",
            )
        )
        return AuditReport(
            manifest_path=str(manifest_path),
            cache_dir=str(cache_dir),
            total_entries=0,
            pass_count=0,
            warn_count=0,
            fail_count=1,
            overall_status="FAIL",
            coverage={},
            findings=findings,
            entries=[],
        )

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            raw_manifest = json.load(f)
    except Exception as e:
        findings.append(
            Finding(
                severity="FAIL",
                category="manifest",
                message=f"Failed to parse manifest JSON: {e}",
            )
        )
        return AuditReport(
            manifest_path=str(manifest_path),
            cache_dir=str(cache_dir),
            total_entries=0,
            pass_count=0,
            warn_count=0,
            fail_count=1,
            overall_status="FAIL",
            coverage={},
            findings=findings,
            entries=[],
        )

    if not isinstance(raw_manifest, list):
        findings.append(
            Finding(
                severity="FAIL",
                category="manifest",
                message=f"Manifest root must be a JSON array (list), found {type(raw_manifest).__name__}.",
            )
        )
        return AuditReport(
            manifest_path=str(manifest_path),
            cache_dir=str(cache_dir),
            total_entries=0,
            pass_count=0,
            warn_count=0,
            fail_count=1,
            overall_status="FAIL",
            coverage={},
            findings=findings,
            entries=[],
        )

    if len(raw_manifest) == 0:
        findings.append(
            Finding(
                severity="FAIL",
                category="manifest",
                message="Manifest contains 0 entries (empty dataset).",
            )
        )
        return AuditReport(
            manifest_path=str(manifest_path),
            cache_dir=str(cache_dir),
            total_entries=0,
            pass_count=0,
            warn_count=0,
            fail_count=1,
            overall_status="FAIL",
            coverage={},
            findings=findings,
            entries=[],
        )

    # 2. Duplicate detection and coverage aggregation
    seen_urls: Dict[str, int] = {}
    seen_obs_tuples: Dict[Tuple[str, str, str, str], int] = {}

    targets_cov: Dict[str, int] = {}
    colls_cov: Dict[str, int] = {}
    dets_cov: Dict[str, int] = {}
    dates_cov: Dict[str, int] = {}

    for idx, item in enumerate(raw_manifest, start=1):
        if not isinstance(item, dict):
            continue

        target = str(item.get("target_name", "UNKNOWN"))
        coll = str(item.get("collection", "UNKNOWN"))
        obs = str(item.get("obs_id", "UNKNOWN"))
        det = str(item.get("detector", "UNKNOWN"))
        date_str = str(item.get("utc_date", "UNKNOWN"))[:10]  # group by YYYY-MM-DD
        url = str(item.get("cutout_url", ""))

        targets_cov[target] = targets_cov.get(target, 0) + 1
        colls_cov[coll] = colls_cov.get(coll, 0) + 1
        dets_cov[det] = dets_cov.get(det, 0) + 1
        dates_cov[date_str] = dates_cov.get(date_str, 0) + 1

        # Check duplicates
        if url:
            if url in seen_urls:
                findings.append(
                    Finding(
                        severity="FAIL",
                        category="manifest",
                        entry_index=idx,
                        target_name=target,
                        obs_id=obs,
                        detector=det,
                        message=f"Duplicate cutout_url found: identical to entry #{seen_urls[url]}.",
                        details={"cutout_url": url, "first_entry": seen_urls[url]},
                    )
                )
            else:
                seen_urls[url] = idx

        obs_key = (target, coll, obs, det)
        if obs_key in seen_obs_tuples:
            findings.append(
                Finding(
                    severity="FAIL",
                    category="manifest",
                    entry_index=idx,
                    target_name=target,
                    obs_id=obs,
                    detector=det,
                    message=(
                        f"Duplicate observation frame: target '{target}', collection '{coll}', "
                        f"obs_id '{obs}', detector '{det}' matches entry #{seen_obs_tuples[obs_key]}."
                    ),
                    details={"first_entry": seen_obs_tuples[obs_key]},
                )
            )
        else:
            seen_obs_tuples[obs_key] = idx

    coverage_summary = {
        "by_target": dict(sorted(targets_cov.items())),
        "by_collection": dict(sorted(colls_cov.items())),
        "by_detector": dict(sorted(dets_cov.items())),
        "by_date": dict(sorted(dates_cov.items())),
    }

    # 3. Entry-by-entry schema, cache, FITS, dimension, stats, and WCS validation
    for idx, item in enumerate(raw_manifest, start=1):
        schema_valid, schema_findings = validate_manifest_schema_entry(idx, item)
        findings.extend(schema_findings)

        target_name = item.get("target_name", "UNKNOWN") if isinstance(item, dict) else "INVALID"
        collection = item.get("collection", "UNKNOWN") if isinstance(item, dict) else "INVALID"
        obs_id = item.get("obs_id", "UNKNOWN") if isinstance(item, dict) else "INVALID"
        detector = item.get("detector", "UNKNOWN") if isinstance(item, dict) else "INVALID"
        utc_date = item.get("utc_date", "") if isinstance(item, dict) else ""
        ra = float(item.get("ra", 0.0)) if isinstance(item, dict) and isinstance(item.get("ra"), (int, float)) else 0.0
        dec = float(item.get("dec", 0.0)) if isinstance(item, dict) and isinstance(item.get("dec"), (int, float)) else 0.0
        cutout_url = item.get("cutout_url", "") if isinstance(item, dict) else ""
        dimensions = item.get("dimensions") if isinstance(item, dict) else None
        recorded_stats = item.get("pixel_stats") if isinstance(item, dict) else None

        entry = EntryAudit(
            index=idx,
            target_name=str(target_name),
            collection=str(collection),
            obs_id=str(obs_id),
            detector=str(detector),
            utc_date=str(utc_date),
            ra=ra,
            dec=dec,
            cutout_url=str(cutout_url),
            status="PASS",
            dimensions=dimensions,
            recorded_stats=recorded_stats,
            findings=list(schema_findings),
        )

        if not schema_valid:
            entry.status = "FAIL"
            entry_audits.append(entry)
            continue

        # Cache check
        expected_cache_path = compute_cache_key_path(cache_dir, cutout_url)
        entry.cache_path = str(expected_cache_path)

        if not expected_cache_path.is_file():
            finding = Finding(
                severity="FAIL",
                category="cache",
                entry_index=idx,
                target_name=entry.target_name,
                obs_id=entry.obs_id,
                detector=entry.detector,
                message=f"Cache file missing: expected '{expected_cache_path.name}' in '{cache_dir}'.",
                details={"expected_path": str(expected_cache_path), "cutout_url": cutout_url},
            )
            findings.append(finding)
            entry.findings.append(finding)
            entry.status = "FAIL"
            entry_audits.append(entry)
            continue

        # Read cache strictly read-only
        try:
            cached_bytes = expected_cache_path.read_bytes()
            if len(cached_bytes) == 0:
                raise ValueError("Cached FITS file is 0 bytes (empty).")
        except Exception as e:
            finding = Finding(
                severity="FAIL",
                category="cache",
                entry_index=idx,
                target_name=entry.target_name,
                obs_id=entry.obs_id,
                detector=entry.detector,
                message=f"Failed to read cached FITS file '{expected_cache_path.name}': {e}",
            )
            findings.append(finding)
            entry.findings.append(finding)
            entry.status = "FAIL"
            entry_audits.append(entry)
            continue

        # Open FITS cutout
        try:
            hdul = load_fits_cutout(cached_bytes)
        except Exception as e:
            finding = Finding(
                severity="FAIL",
                category="fits",
                entry_index=idx,
                target_name=entry.target_name,
                obs_id=entry.obs_id,
                detector=entry.detector,
                message=f"FITS file parsing failed with helper load_fits_cutout: {e}",
            )
            findings.append(finding)
            entry.findings.append(finding)
            entry.status = "FAIL"
            entry_audits.append(entry)
            continue

        # Extract primary image (preserve scientific NaN values)
        try:
            data, header = extract_primary_image(hdul, preserve_nan=True)
        except Exception as e:
            finding = Finding(
                severity="FAIL",
                category="fits",
                entry_index=idx,
                target_name=entry.target_name,
                obs_id=entry.obs_id,
                detector=entry.detector,
                message=f"Primary image extraction failed: {e}",
            )
            findings.append(finding)
            entry.findings.append(finding)
            entry.status = "FAIL"
            entry_audits.append(entry)
            continue

        actual_dims = list(data.shape)
        entry.actual_dimensions = actual_dims

        # Check dimension consistency
        if dimensions is not None:
            if actual_dims != dimensions:
                finding = Finding(
                    severity="FAIL",
                    category="dimensions",
                    entry_index=idx,
                    target_name=entry.target_name,
                    obs_id=entry.obs_id,
                    detector=entry.detector,
                    message=(
                        f"Dimension mismatch: manifest records {dimensions} [H, W], "
                        f"but FITS array shape is {actual_dims} [H, W]."
                    ),
                    details={"manifest_dims": dimensions, "actual_dims": actual_dims},
                )
                findings.append(finding)
                entry.findings.append(finding)
                entry.status = "FAIL"

        # Calculate finite-pixel coverage and fresh statistics
        total_pix = data.size
        finite_pix = int(np.count_nonzero(np.isfinite(data)))
        entry.total_pixels = total_pix
        entry.finite_pixels = finite_pix
        entry.finite_pct = round((finite_pix / total_pix) * 100.0, 2) if total_pix > 0 else 0.0

        fresh_stats = calculate_pixel_stats(data)
        entry.fresh_stats = fresh_stats

        # Compare recorded stats if present
        if recorded_stats:
            discrepancies: Dict[str, Dict[str, float]] = {}
            for k in ["min_mjy_sr", "max_mjy_sr", "mean_mjy_sr", "std_mjy_sr", "median_mjy_sr"]:
                if k in recorded_stats and k in fresh_stats:
                    rec_v = recorded_stats[k]
                    fresh_v = fresh_stats[k]
                    if abs(rec_v - fresh_v) > stat_tolerance:
                        discrepancies[k] = {"recorded": rec_v, "fresh": fresh_v, "diff": round(fresh_v - rec_v, 4)}

            if discrepancies:
                entry.stat_discrepancies = discrepancies
                # Check if legacy NaN-sanitizing mode accounts for the discrepancy
                legacy_match = False
                try:
                    data_sanitized, _ = extract_primary_image(hdul, preserve_nan=False)
                    legacy_stats = calculate_pixel_stats(data_sanitized)
                    legacy_diffs = [
                        abs(recorded_stats[k] - legacy_stats.get(k, 0))
                        for k in discrepancies
                        if k in recorded_stats
                    ]
                    if all(d <= stat_tolerance for d in legacy_diffs):
                        legacy_match = True
                except Exception:
                    pass

                explanation = (
                    "Discrepancy matches legacy NaN-sanitizing calculation."
                    if legacy_match
                    else "Recorded statistics differ from fresh calculation on finite pixels."
                )

                finding = Finding(
                    severity="WARN",
                    category="statistics",
                    entry_index=idx,
                    target_name=entry.target_name,
                    obs_id=entry.obs_id,
                    detector=entry.detector,
                    message=(
                        f"Recorded pixel statistics differ from fresh calculation: "
                        + ", ".join(f"{k} (rec={v['recorded']}, fresh={v['fresh']})" for k, v in discrepancies.items())
                        + f". {explanation}"
                    ),
                    details={"discrepancies": discrepancies, "legacy_match": legacy_match},
                )
                findings.append(finding)
                entry.findings.append(finding)
                if entry.status != "FAIL":
                    entry.status = "WARN"

        # Check extensions and optional headers
        ext_names = [h.name for h in hdul]
        entry.has_flags = "FLAGS" in ext_names
        entry.has_wcs_wave = "WCS-WAVE" in ext_names

        if not entry.has_flags:
            finding = Finding(
                severity="WARN",
                category="fits",
                entry_index=idx,
                target_name=entry.target_name,
                obs_id=entry.obs_id,
                detector=entry.detector,
                message="FLAGS extension missing; mask evaluation unavailable for this frame.",
            )
            findings.append(finding)
            entry.findings.append(finding)
            if entry.status != "FAIL":
                entry.status = "WARN"

        if not entry.has_wcs_wave:
            finding = Finding(
                severity="WARN",
                category="fits",
                entry_index=idx,
                target_name=entry.target_name,
                obs_id=entry.obs_id,
                detector=entry.detector,
                message="WCS-WAVE extension missing; wavelength calibration lookup unavailable for this frame.",
            )
            findings.append(finding)
            entry.findings.append(finding)
            if entry.status != "FAIL":
                entry.status = "WARN"

        # WCS evaluation
        w = extract_astropy_wcs(header)
        if w is None or not getattr(w, "is_celestial", False):
            finding = Finding(
                severity="WARN",
                category="wcs",
                entry_index=idx,
                target_name=entry.target_name,
                obs_id=entry.obs_id,
                detector=entry.detector,
                message="Valid celestial WCS could not be extracted from FITS image header.",
            )
            findings.append(finding)
            entry.findings.append(finding)
            if entry.status != "FAIL":
                entry.status = "WARN"
        else:
            entry.wcs_valid = True
            try:
                c_target = SkyCoord(ra=entry.ra * u.deg, dec=entry.dec * u.deg)
                h_img, w_img = data.shape
                # Center pixel coordinates (0-indexed)
                cx = (w_img - 1.0) / 2.0
                cy = (h_img - 1.0) / 2.0
                world_center = w.pixel_to_world(cx, cy)
                sep_arcsec = float(c_target.separation(world_center).arcsec)
                entry.wcs_center_offset_arcsec = round(sep_arcsec, 2)

                px, py = w.world_to_pixel(c_target)
                entry.target_pixel_coords = (round(float(px), 2), round(float(py), 2))
                inside = bool((0.0 <= px < w_img) and (0.0 <= py < h_img))
                entry.target_inside_bounds = inside

                if not inside:
                    # Informational diagnostic when target is outside cutout boundaries (e.g. edge cutout)
                    finding = Finding(
                        severity="WARN",
                        category="wcs",
                        entry_index=idx,
                        target_name=entry.target_name,
                        obs_id=entry.obs_id,
                        detector=entry.detector,
                        message=(
                            f"Target search coordinate (px={px:.2f}, py={py:.2f}) projects outside "
                            f"cutout bounds [0..{w_img-1}, 0..{h_img-1}]; cutout center offset is {sep_arcsec:.2f}\"."
                        ),
                        details={
                            "offset_arcsec": entry.wcs_center_offset_arcsec,
                            "pixel_coords": entry.target_pixel_coords,
                            "cutout_shape": [h_img, w_img],
                        },
                    )
                    findings.append(finding)
                    entry.findings.append(finding)
                    if entry.status != "FAIL":
                        entry.status = "WARN"
            except Exception as e:
                finding = Finding(
                    severity="WARN",
                    category="wcs",
                    entry_index=idx,
                    target_name=entry.target_name,
                    obs_id=entry.obs_id,
                    detector=entry.detector,
                    message=f"WCS celestial projection calculation encountered error: {e}",
                )
                findings.append(finding)
                entry.findings.append(finding)
                if entry.status != "FAIL":
                    entry.status = "WARN"

        entry_audits.append(entry)

    # 4. Overall status calculation
    fail_findings = [f for f in findings if f.severity == "FAIL"]
    warn_findings = [f for f in findings if f.severity == "WARN"]

    pass_entries = sum(1 for e in entry_audits if e.status == "PASS")
    warn_entries = sum(1 for e in entry_audits if e.status == "WARN")
    fail_entries = sum(1 for e in entry_audits if e.status == "FAIL")

    if fail_findings:
        overall_status: Severity = "FAIL"
    elif warn_findings and strict_warnings:
        overall_status = "FAIL"
    elif warn_findings:
        overall_status = "WARN"
    else:
        overall_status = "PASS"

    return AuditReport(
        manifest_path=str(manifest_path),
        cache_dir=str(cache_dir),
        total_entries=len(raw_manifest),
        pass_count=pass_entries,
        warn_count=warn_entries,
        fail_count=fail_entries,
        overall_status=overall_status,
        coverage=coverage_summary,
        findings=findings,
        entries=entry_audits,
    )


def format_text_report(report: AuditReport) -> str:
    lines: List[str] = []
    w = 72
    lines.append("=" * w)
    lines.append("SPHEREx DEMONSTRATION DATASET AUDIT REPORT".center(w))
    lines.append("=" * w)
    lines.append(f"Manifest Path : {report.manifest_path}")
    lines.append(f"Cache Directory: {report.cache_dir}")
    lines.append(f"Total Entries  : {report.total_entries}")
    lines.append(f"Overall Status : [{report.overall_status}]")
    lines.append("-" * w)

    # Coverage summary
    lines.append("DATASET COVERAGE SUMMARY")
    lines.append("-" * w)
    cov = report.coverage
    by_target = cov.get("by_target", {})
    lines.append(f"Targets ({len(by_target)}):")
    for t_name, count in sorted(by_target.items()):
        lines.append(f"  • {t_name:<28} : {count:2d} cutout(s)")

    by_coll = cov.get("by_collection", {})
    lines.append(f"\nCollections ({len(by_coll)}):")
    for c_name, count in sorted(by_coll.items()):
        lines.append(f"  • {c_name:<28} : {count:2d} cutout(s)")

    by_det = cov.get("by_detector", {})
    lines.append(f"\nDetectors ({len(by_det)}):")
    for d_name, count in sorted(by_det.items()):
        lines.append(f"  • {d_name:<28} : {count:2d} cutout(s)")

    by_date = cov.get("by_date", {})
    lines.append(f"\nObservation Dates ({len(by_date)} distinct dates):")
    for d_str, count in sorted(by_date.items()):
        lines.append(f"  • {d_str:<28} : {count:2d} cutout(s)")

    lines.append(
        "\nCoverage note: Coverage counts reflect offline demonstration assets only; "
        "target identity and astrophysical motion have not been independently validated."
    )
    lines.append("-" * w)

    # Entry summaries
    lines.append("ENTRY INSPECTION DETAILS")
    lines.append("-" * w)
    for e in report.entries:
        dims_str = f"{e.actual_dimensions[0]}x{e.actual_dimensions[1]}" if e.actual_dimensions else "N/A"
        finite_str = f"{e.finite_pixels}/{e.total_pixels} ({e.finite_pct}%)" if e.total_pixels else "N/A"
        wcs_str = (
            f"offset={e.wcs_center_offset_arcsec:.2f}\""
            if e.wcs_center_offset_arcsec is not None
            else "no celestial WCS"
        )
        lines.append(
            f"[{e.status:4s}] Entry #{e.index:02d} | {e.target_name} ({e.collection} | {e.detector} | {e.obs_id})"
        )
        lines.append(f"       Dims: {dims_str} | Finite Pixels: {finite_str} | WCS: {wcs_str}")
        if e.fresh_stats:
            s = e.fresh_stats
            lines.append(
                f"       Flux (MJy/sr): mean={s['mean_mjy_sr']}, min={s['min_mjy_sr']}, max={s['max_mjy_sr']}, std={s['std_mjy_sr']}"
            )
        if e.stat_discrepancies:
            disc_items = [f"{k}: rec={v['recorded']} vs fresh={v['fresh']}" for k, v in e.stat_discrepancies.items()]
            lines.append(f"       * Stat discrepancy: {', '.join(disc_items)}")

    # Actionable Findings
    lines.append("-" * w)
    lines.append("ACTIONABLE FINDINGS & RECOMMENDATIONS")
    lines.append("-" * w)
    actionable = [f for f in report.findings if f.severity in ("FAIL", "WARN")]
    if not actionable:
        lines.append("✓ No defects or warnings found. Dataset is fully consistent.")
    else:
        for idx, f in enumerate(actionable, start=1):
            loc_str = ""
            if f.entry_index is not None:
                loc_str = f" [Entry #{f.entry_index}"
                if f.target_name:
                    loc_str += f" | {f.target_name}"
                if f.obs_id:
                    loc_str += f" | {f.obs_id}"
                if f.detector:
                    loc_str += f" | {f.detector}"
                loc_str += "]"
            lines.append(f"{idx:02d}. [{f.severity}] [{f.category}]{loc_str}: {f.message}")

    lines.append("=" * w)
    lines.append(
        f"AUDIT SUMMARY: {report.overall_status} "
        f"(Total: {report.total_entries} | Pass: {report.pass_count} | "
        f"Warn: {report.warn_count} | Fail: {report.fail_count})"
    )
    lines.append("=" * w)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit SPHEREx demonstration dataset manifest and offline cache consistency.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=_REPO_ROOT / "data" / "manifests" / "demo_dataset.json",
        help="Path to demo dataset JSON manifest",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=_REPO_ROOT / "data" / "cache",
        help="Path to FITS cutouts cache directory",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Report output format (text or json)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Shorthand for --format json",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Path to write the report to (defaults to stdout)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures (returns exit code 1 if any warnings exist)",
    )
    parser.add_argument(
        "--stat-tolerance",
        type=float,
        default=1e-3,
        help="Numerical tolerance for comparing recorded vs fresh pixel statistics",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    output_format = "json" if args.json else args.format

    report = audit_manifest(
        manifest_path=args.manifest,
        cache_dir=args.cache_dir,
        strict_warnings=args.strict,
        stat_tolerance=args.stat_tolerance,
    )

    if output_format == "json":
        rendered = json.dumps(report.to_dict(), indent=2, cls=NpEncoder)
    else:
        rendered = format_text_report(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        # Print concise confirmation to stdout
        print(f"Audit completed: [{report.overall_status}]. Report written to {args.output}")
    else:
        print(rendered)

    # Return exit code 0 on success/pass/warn, 1 on fail
    return 1 if report.overall_status == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
