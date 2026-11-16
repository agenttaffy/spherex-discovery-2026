"""
backend/tests/test_demo_manifest_audit.py

Comprehensive unit and integration tests for the SPHEREx demo manifest audit tool.
Verifies schema validation, duplicate detection, cache lookup, FITS loading,
finite-pixel calculation, dimension/stat checking, WCS evaluation, CLI behavior,
and strictly read-only execution using isolated temporary fixtures.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pytest
from astropy.io import fits

import sys

# Ensure backend and scripts are in sys.path
_TEST_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TEST_DIR.parent.parent
sys.path.insert(0, str(_TEST_DIR.parent))
sys.path.insert(0, str(_REPO_ROOT))

from scripts.audit_demo_manifest import (
    AuditReport,
    audit_manifest,
    compute_cache_key_path,
    format_text_report,
    main as audit_cli_main,
)


def make_synthetic_fits_bytes(
    shape: tuple[int, int] = (10, 10),
    data_override: Optional[np.ndarray] = None,
    crval1: float = 127.6944,
    crval2: float = -39.1776,
    include_flags: bool = True,
    include_wcs_wave: bool = True,
    has_celestial_wcs: bool = True,
) -> bytes:
    """Create in-memory SPHEREx-like FITS cutout bytes with customizable extensions and metadata."""
    pri = fits.PrimaryHDU()
    pri.header["TELESCOP"] = "SPHEREx"
    pri.header["INSTRUME"] = "SPHEREx"

    if data_override is not None:
        img_data = data_override.astype(np.float32)
    else:
        # Predictable pattern: linear values
        h, w = shape
        img_data = np.arange(h * w, dtype=np.float32).reshape(h, w) + 1.0

    img_hdu = fits.ImageHDU(data=img_data, name="IMAGE")
    img_hdu.header["BUNIT"] = "MJy/sr"
    if has_celestial_wcs:
        img_hdu.header["CTYPE1"] = "RA---TAN"
        img_hdu.header["CTYPE2"] = "DEC--TAN"
        img_hdu.header["CRVAL1"] = crval1
        img_hdu.header["CRVAL2"] = crval2
        img_hdu.header["CRPIX1"] = float(shape[1] + 1) / 2.0
        img_hdu.header["CRPIX2"] = float(shape[0] + 1) / 2.0
        img_hdu.header["CDELT1"] = -0.0017
        img_hdu.header["CDELT2"] = 0.0017

    hdus: List[fits.HDUList] = [pri, img_hdu]

    if include_flags:
        flags_data = np.zeros(shape, dtype=np.int32)
        flags_hdu = fits.ImageHDU(data=flags_data, name="FLAGS")
        flags_hdu.header["MSKN0001"] = "HOT"
        flags_hdu.header["MSKM0001"] = 1
        hdus.append(flags_hdu)

    if include_wcs_wave:
        # Mock binary table for WCS-WAVE
        col_x = fits.Column(name="X", format="10D", array=np.zeros((1, 10)))
        col_y = fits.Column(name="Y", format="10D", array=np.zeros((1, 10)))
        col_vals = fits.Column(name="VALUES", format="10D", array=np.ones((1, 10)))
        wave_hdu = fits.BinTableHDU.from_columns([col_x, col_y, col_vals], name="WCS-WAVE")
        hdus.append(wave_hdu)

    hdul = fits.HDUList(hdus)
    buf = io.BytesIO()
    hdul.writeto(buf)
    return buf.getvalue()


@pytest.fixture
def mock_dataset_env(tmp_path: Path):
    """
    Creates an isolated mock environment with a manifest file and corresponding cached FITS cutouts.
    """
    manifest_dir = tmp_path / "data" / "manifests"
    cache_dir = tmp_path / "data" / "cache"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    url_1 = "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/cutout1.fits"
    url_2 = "https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/cutout2.fits"

    # Shape 4x4 for simple stats
    data_1 = np.array([
        [1.0, 2.0, 3.0, 4.0],
        [5.0, 6.0, 7.0, 8.0],
        [9.0, 10.0, 11.0, 12.0],
        [13.0, 14.0, 15.0, 16.0],
    ], dtype=np.float32)

    fits_bytes_1 = make_synthetic_fits_bytes(shape=(4, 4), data_override=data_1, crval1=100.0, crval2=20.0)
    cache_file_1 = compute_cache_key_path(cache_dir, url_1)
    cache_file_1.write_bytes(fits_bytes_1)

    data_2 = np.ones((4, 4), dtype=np.float32) * 5.0
    fits_bytes_2 = make_synthetic_fits_bytes(shape=(4, 4), data_override=data_2, crval1=150.0, crval2=-10.0)
    cache_file_2 = compute_cache_key_path(cache_dir, url_2)
    cache_file_2.write_bytes(fits_bytes_2)

    manifest_entries = [
        {
            "target_name": "Target Alpha",
            "ra": 100.0,
            "dec": 20.0,
            "collection": "spherex_dr1",
            "obs_id": "OBS_001",
            "detector": "SPHEREx-D1",
            "utc_date": "2025-05-01T12:00:00",
            "cutout_url": url_1,
            "dimensions": [4, 4],
            "pixel_stats": {
                "min_mjy_sr": 1.0,
                "max_mjy_sr": 16.0,
                "mean_mjy_sr": 8.5,
                "std_mjy_sr": 4.6098,
                "median_mjy_sr": 8.5,
            },
        },
        {
            "target_name": "Target Beta",
            "ra": 150.0,
            "dec": -10.0,
            "collection": "spherex_qr3",
            "obs_id": "OBS_002",
            "detector": "SPHEREx-D4",
            "utc_date": "2026-06-01T14:30:00",
            "cutout_url": url_2,
            "dimensions": [4, 4],
            "pixel_stats": {
                "min_mjy_sr": 5.0,
                "max_mjy_sr": 5.0,
                "mean_mjy_sr": 5.0,
                "std_mjy_sr": 0.0,
                "median_mjy_sr": 5.0,
            },
        },
    ]

    manifest_path = manifest_dir / "demo_dataset.json"
    manifest_path.write_text(json.dumps(manifest_entries, indent=2), encoding="utf-8")

    return {
        "manifest_path": manifest_path,
        "cache_dir": cache_dir,
        "entries": manifest_entries,
        "cache_file_1": cache_file_1,
        "cache_file_2": cache_file_2,
    }


def test_audit_valid_dataset(mock_dataset_env):
    """Verify that a fully conforming mock manifest and cache produces PASS status."""
    report = audit_manifest(
        manifest_path=mock_dataset_env["manifest_path"],
        cache_dir=mock_dataset_env["cache_dir"],
    )

    assert report.overall_status == "PASS"
    assert report.total_entries == 2
    assert report.pass_count == 2
    assert report.warn_count == 0
    assert report.fail_count == 0
    assert len(report.findings) == 0

    # Coverage verification
    assert report.coverage["by_target"] == {"Target Alpha": 1, "Target Beta": 1}
    assert report.coverage["by_collection"] == {"spherex_dr1": 1, "spherex_qr3": 1}
    assert report.coverage["by_detector"] == {"SPHEREx-D1": 1, "SPHEREx-D4": 1}

    # Verify per-entry diagnostics
    e0 = report.entries[0]
    assert e0.status == "PASS"
    assert e0.actual_dimensions == [4, 4]
    assert e0.finite_pixels == 16
    assert e0.total_pixels == 16
    assert e0.wcs_valid is True
    assert e0.wcs_center_offset_arcsec is not None
    assert e0.target_inside_bounds is True


def test_audit_manifest_missing(tmp_path: Path):
    """Verify handling when the manifest file does not exist."""
    missing_manifest = tmp_path / "nonexistent.json"
    report = audit_manifest(missing_manifest, tmp_path)
    assert report.overall_status == "FAIL"
    assert report.fail_count == 1
    assert any(f.category == "manifest" and "does not exist" in f.message for f in report.findings)


def test_audit_manifest_malformed_json(tmp_path: Path):
    """Verify handling when manifest is corrupted/invalid JSON."""
    bad_json = tmp_path / "bad_manifest.json"
    bad_json.write_text("{ unclosed JSON ...", encoding="utf-8")
    report = audit_manifest(bad_json, tmp_path)
    assert report.overall_status == "FAIL"
    assert report.fail_count == 1
    assert any(f.category == "manifest" and "Failed to parse" in f.message for f in report.findings)


def test_audit_manifest_empty_or_non_list(tmp_path: Path):
    """Verify handling when manifest is empty list or not a list."""
    empty_json = tmp_path / "empty.json"
    empty_json.write_text("[]", encoding="utf-8")
    report = audit_manifest(empty_json, tmp_path)
    assert report.overall_status == "FAIL"
    assert any("0 entries" in f.message for f in report.findings)

    dict_json = tmp_path / "dict.json"
    dict_json.write_text('{"key": "value"}', encoding="utf-8")
    report_dict = audit_manifest(dict_json, tmp_path)
    assert report_dict.overall_status == "FAIL"
    assert any("must be a JSON array" in f.message for f in report_dict.findings)


def test_audit_schema_invalid_fields(tmp_path: Path):
    """Verify validation of required field types, bounds, and date/url formats."""
    bad_entries = [
        {
            # Missing target_name, out-of-bounds RA, bad Dec, invalid UTC date, invalid URL
            "ra": 450.0,
            "dec": -120.0,
            "collection": "",
            "obs_id": 12345,  # non-string
            "detector": "SPHEREx-D1",
            "utc_date": "not-a-date",
            "cutout_url": "ftp://invalid-url",
            "dimensions": [20],  # only 1 int
            "pixel_stats": {
                "min_mjy_sr": 10.0,
                "max_mjy_sr": 2.0,  # min > max
                "std_mjy_sr": -1.0,  # negative std
            },
        }
    ]
    manifest = tmp_path / "invalid_fields.json"
    manifest.write_text(json.dumps(bad_entries), encoding="utf-8")
    report = audit_manifest(manifest, tmp_path)

    assert report.overall_status == "FAIL"
    messages = [f.message for f in report.findings]
    assert any("target_name" in m for m in messages)
    assert any("ra" in m and "out of bounds" in m for m in messages)
    assert any("dec" in m and "out of bounds" in m for m in messages)
    assert any("utc_date" in m for m in messages)
    assert any("cutout_url" in m for m in messages)
    assert any("dimensions" in m for m in messages)
    assert any("min (10.0) > max (2.0)" in m for m in messages)
    assert any("cannot be negative" in m for m in messages)


def test_audit_duplicate_entries(mock_dataset_env):
    """Verify detection of duplicate cutout URLs and duplicate observation frames."""
    entries = mock_dataset_env["entries"]
    # Duplicate entry 0 with identical URL and obs_id
    dup_manifest = entries + [entries[0]]
    manifest_path = mock_dataset_env["manifest_path"]
    manifest_path.write_text(json.dumps(dup_manifest), encoding="utf-8")

    report = audit_manifest(manifest_path, mock_dataset_env["cache_dir"])
    assert report.overall_status == "FAIL"
    assert any("Duplicate cutout_url" in f.message for f in report.findings)
    assert any("Duplicate observation frame" in f.message for f in report.findings)


def test_audit_missing_cache_file(mock_dataset_env):
    """Verify FAIL status when cache file is missing on disk."""
    # Delete cache file 1
    mock_dataset_env["cache_file_1"].unlink()

    report = audit_manifest(mock_dataset_env["manifest_path"], mock_dataset_env["cache_dir"])
    assert report.overall_status == "FAIL"
    cache_findings = [f for f in report.findings if f.category == "cache"]
    assert len(cache_findings) == 1
    assert "Cache file missing" in cache_findings[0].message
    assert cache_findings[0].entry_index == 1


def test_audit_bad_fits_bytes(mock_dataset_env):
    """Verify FAIL status when cached FITS file contains corrupted data."""
    mock_dataset_env["cache_file_1"].write_bytes(b"NOT A VALID FITS FILE DATA")

    report = audit_manifest(mock_dataset_env["manifest_path"], mock_dataset_env["cache_dir"])
    assert report.overall_status == "FAIL"
    fits_findings = [f for f in report.findings if f.category == "fits"]
    assert len(fits_findings) >= 1
    assert "FITS file parsing failed" in fits_findings[0].message


def test_audit_dimension_mismatch(mock_dataset_env):
    """Verify FAIL status when FITS image dimensions disagree with manifest metadata."""
    # Write a 6x6 image to cache_file_1 while manifest states [4, 4]
    fits_bytes_6x6 = make_synthetic_fits_bytes(shape=(6, 6))
    mock_dataset_env["cache_file_1"].write_bytes(fits_bytes_6x6)

    report = audit_manifest(mock_dataset_env["manifest_path"], mock_dataset_env["cache_dir"])
    assert report.overall_status == "FAIL"
    dim_findings = [f for f in report.findings if f.category == "dimensions"]
    assert len(dim_findings) == 1
    assert "Dimension mismatch" in dim_findings[0].message
    assert "manifest records [4, 4]" in dim_findings[0].message
    assert "[6, 6]" in dim_findings[0].message


def test_audit_stat_mismatch_and_strict_mode(mock_dataset_env):
    """Verify that statistics discrepancies produce WARN normally and FAIL under strict mode."""
    # Modify manifest entry 0 to have wildly inaccurate mean and std
    entries = mock_dataset_env["entries"]
    entries[0]["pixel_stats"]["mean_mjy_sr"] = 999.0
    entries[0]["pixel_stats"]["std_mjy_sr"] = 50.0
    mock_dataset_env["manifest_path"].write_text(json.dumps(entries), encoding="utf-8")

    # Default run: WARN severity, overall status is WARN, non-zero return in strict only
    report_default = audit_manifest(mock_dataset_env["manifest_path"], mock_dataset_env["cache_dir"])
    assert report_default.overall_status == "WARN"
    stat_findings = [f for f in report_default.findings if f.category == "statistics"]
    assert len(stat_findings) == 1
    assert "Recorded pixel statistics differ" in stat_findings[0].message

    # Strict run: WARN causes overall status to become FAIL
    report_strict = audit_manifest(
        mock_dataset_env["manifest_path"],
        mock_dataset_env["cache_dir"],
        strict_warnings=True,
    )
    assert report_strict.overall_status == "FAIL"


def test_audit_wcs_and_finite_pixels(tmp_path: Path):
    """Verify finite-pixel counting with NaNs and conservative WCS diagnostics."""
    manifest_dir = tmp_path / "data" / "manifests"
    cache_dir = tmp_path / "data" / "cache"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    url = "https://irsa.ipac.caltech.edu/cutout_nan.fits"
    # 4x4 array with 2 NaNs
    data = np.ones((4, 4), dtype=np.float32)
    data[0, 0] = np.nan
    data[1, 1] = np.nan

    fits_bytes = make_synthetic_fits_bytes(
        shape=(4, 4),
        data_override=data,
        crval1=180.0,
        crval2=45.0,
        include_flags=False,
        include_wcs_wave=False,
    )
    cache_file = compute_cache_key_path(cache_dir, url)
    cache_file.write_bytes(fits_bytes)

    # Put search coordinate slightly outside the 4x4 image
    entries = [
        {
            "target_name": "Target Edge",
            "ra": 185.0,  # far from 180.0 center
            "dec": 45.0,
            "collection": "spherex_dr1",
            "obs_id": "OBS_EDGE",
            "detector": "SPHEREx-D1",
            "utc_date": "2025-07-01T00:00:00",
            "cutout_url": url,
            "dimensions": [4, 4],
        }
    ]
    manifest = manifest_dir / "edge_manifest.json"
    manifest.write_text(json.dumps(entries), encoding="utf-8")

    report = audit_manifest(manifest, cache_dir)
    assert report.overall_status == "WARN"

    entry = report.entries[0]
    assert entry.total_pixels == 16
    assert entry.finite_pixels == 14
    assert entry.finite_pct == 87.5
    assert entry.target_inside_bounds is False

    # Check that missing optional extensions are warnings, not guessed failures
    wcs_warns = [f for f in report.findings if f.category == "wcs"]
    assert any("projects outside cutout bounds" in f.message for f in wcs_warns)

    fits_warns = [f for f in report.findings if f.category == "fits"]
    assert any("FLAGS extension missing" in f.message for f in fits_warns)
    assert any("WCS-WAVE extension missing" in f.message for f in fits_warns)


def test_audit_strictly_read_only(mock_dataset_env):
    """Verify that running the audit produces zero disk writes or mutations to manifest or cache."""
    manifest_path = mock_dataset_env["manifest_path"]
    cache_file_1 = mock_dataset_env["cache_file_1"]
    cache_file_2 = mock_dataset_env["cache_file_2"]

    def snapshot() -> Dict[str, str]:
        return {
            "manifest": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "cache_1": hashlib.sha256(cache_file_1.read_bytes()).hexdigest(),
            "cache_2": hashlib.sha256(cache_file_2.read_bytes()).hexdigest(),
        }

    before = snapshot()
    report = audit_manifest(manifest_path, mock_dataset_env["cache_dir"])
    assert report.overall_status == "PASS"
    after = snapshot()

    assert before == after, "Audit modified manifest or cached FITS data!"


def test_cli_json_and_file_output(mock_dataset_env, tmp_path: Path):
    """Verify CLI interface: exit codes, JSON mode, text formatting, and file redirection."""
    out_json = tmp_path / "out_report.json"
    exit_code = audit_cli_main([
        "--manifest", str(mock_dataset_env["manifest_path"]),
        "--cache-dir", str(mock_dataset_env["cache_dir"]),
        "--json",
        "-o", str(out_json),
    ])

    assert exit_code == 0
    assert out_json.is_file()

    parsed = json.loads(out_json.read_text(encoding="utf-8"))
    assert "summary" in parsed
    assert parsed["summary"]["overall_status"] == "PASS"
    assert parsed["summary"]["total_entries"] == 2
    assert "coverage" in parsed["summary"]
    assert len(parsed["entries"]) == 2

    # Test text report formatting function directly
    report = audit_manifest(mock_dataset_env["manifest_path"], mock_dataset_env["cache_dir"])
    text_rep = format_text_report(report)
    assert "SPHEREx DEMONSTRATION DATASET AUDIT REPORT" in text_rep
    assert "Overall Status : [PASS]" in text_rep
    assert "Targets (2):" in text_rep
