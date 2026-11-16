"""Reproduce a visualization-only RW Aur D1 overlap check from cached images.

This deliberately uses the low-resolution WCS-WAVE table, NOT the full
CWAVE/CBAND science calibration. Results do not establish source detection,
motion, or a quantitatively verified comparison. No network calls are made.
"""
import io
import json
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from scipy.interpolate import RegularGridInterpolator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.science.calibrated_comparison import CalibratedExposure, compare_calibrated_pair
from app.science.fits_processing import SPHEREX_INFORMATIONAL_FLAG_NAMES, parse_spherex_mask_planes
from app.science.spectral_calibration import spectral_calibration_plane_id
from app.services.cache_service import cache_service
from app.services.cutout_service import cutout_cache_key
from app.services.saved_observation_search import saved_observations

RA, DEC, FOV = 76.95658820303035, 30.401287398865755, .04
PAIRS = [
    ("2025W36_1A_0095_1", "2025W36_1A_0155_1"),
    ("2025W36_1A_0606_2", "2026W10_1A_0445_2"),
]


def image_exposure(row):
    key = cutout_cache_key(row.access_url, RA, DEC, FOV)
    data = cache_service.get(key) or cache_service.get(f"cloud-{key}")
    if not data:
        raise ValueError(f"Required cached cutout is missing: {row.obs_id}")
    with fits.open(io.BytesIO(data)) as hdul:
        image_hdu = hdul["IMAGE"]
        header = image_hdu.header
        if header.get("OBSID") != row.obs_id or str(header.get("DETECTOR")) != "1":
            raise ValueError("Cached observation identity or detector mismatch")
        image = image_hdu.data.copy()
        variance = hdul["VARIANCE"].data.copy()
        flags = hdul["FLAGS"]
        planes = parse_spherex_mask_planes(flags.header)
        if not planes:
            raise ValueError("Documented image quality flags are unavailable")
        allowed = 0
        for name in SPHEREX_INFORMATIONAL_FLAG_NAMES:
            allowed |= planes.get(name, 0)
        bad = (flags.data.astype(np.int64) & ~allowed) != 0
        table = hdul["WCS-WAVE"].data[0]
        yy, xx = np.indices(image.shape)
        x = xx - float(header["CRPIX1W"]) + float(header["CRVAL1W"])
        y = yy - float(header["CRPIX2W"]) + float(header["CRVAL2W"])
        points = np.column_stack((y.ravel(), x.ravel()))
        grid = (table["Y"], table["X"])
        wave = RegularGridInterpolator(grid, table["VALUES"][:, :, 0], bounds_error=False, fill_value=np.nan)(points).reshape(image.shape)
        band = RegularGridInterpolator(grid, table["VALUES"][:, :, 1], bounds_error=False, fill_value=np.nan)(points).reshape(image.shape)
        center = (image.shape[0] // 2, image.shape[1] // 2)
        return CalibratedExposure(image, variance, bad, wave, band, WCS(header).celestial), {
            "obs_id": row.obs_id, "spectral_plane_id": spectral_calibration_plane_id(hdul),
            "approximate_center_wavelength_um": float(wave[center]),
            "approximate_center_bandwidth_um": float(band[center]),
        }


def main():
    rows = {row.obs_id: row for row in saved_observations(RA, DEC, FOV, "spherex_dr1", "SPHEREx-D1", 200)}
    results = []
    for pair in PAIRS:
        if any(name not in rows for name in pair):
            raise ValueError(f"Required historical observation metadata missing: {pair}")
        samples = [image_exposure(rows[name]) for name in pair]
        try:
            result = compare_calibrated_pair(samples[0][0], samples[1][0], minimum_passband_overlap=.9)
            outcome = {"approximately_retained_pixels": result["retained_pixels"],
                       "reference_pixels": result["reference_pixels"]}
        except ValueError as exc:
            outcome = {"approximate_rejection": str(exc)}
        results.append({"images": [item[1] for item in samples], **outcome})
    print(json.dumps({"warning": "Approximate WCS-WAVE visual diagnostic only; not science-grade calibration.",
                      "requested_position": {"ra": RA, "dec": DEC, "fov_deg": FOV},
                      "pairs": results}, indent=2))


if __name__ == "__main__":
    main()
