"""Compare exposure samples using their matched per-pixel CWAVE and CBAND."""

from dataclasses import dataclass

import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS

from app.science.fits_processing import (
    SPHEREX_INFORMATIONAL_FLAG_NAMES,
    extract_variance_data,
    parse_spherex_mask_planes,
)
from app.science.spectral_calibration import map_calibration_to_cutout


@dataclass
class CalibratedExposure:
    image: np.ndarray
    variance: np.ndarray
    bad: np.ndarray
    wavelength: np.ndarray
    bandwidth: np.ndarray
    wcs: WCS

    def usable(self) -> np.ndarray:
        if self.image.ndim != 2 or any(
            plane.shape != self.image.shape
            for plane in (self.variance, self.bad, self.wavelength, self.bandwidth)
        ):
            raise ValueError("Calibration, quality, and variance must match the image grid")
        if not self.wcs.has_celestial:
            raise ValueError("A celestial WCS is required for each exposure")
        return (
            ~self.bad.astype(bool) & np.isfinite(self.image)
            & np.isfinite(self.variance) & (self.variance > 0)
            & np.isfinite(self.wavelength) & (self.wavelength > 0)
            & np.isfinite(self.bandwidth) & (self.bandwidth > 0)
        )


def prepare_calibrated_exposure(
    science: fits.HDUList, calibration: bytes, *, plane_id: str, checksum: str,
) -> CalibratedExposure:
    image = science["IMAGE"]
    flags = science["FLAGS"] if "FLAGS" in science else None
    variance = extract_variance_data(science)
    planes = parse_spherex_mask_planes(flags.header) if flags is not None else {}
    if not planes or flags.data is None or variance is None:
        raise ValueError("Science comparison requires a documented quality mask and a variance plane")
    informational_bits = 0
    for name in SPHEREX_INFORMATIONAL_FLAG_NAMES:
        informational_bits |= planes.get(name, 0)
    bad = (flags.data.astype(np.int64) & ~informational_bits) != 0
    brightness_unit = u.MJy / u.sr
    if (u.Unit(image.header.get("BUNIT", "")) != brightness_unit
            or u.Unit(science["VARIANCE"].header.get("BUNIT", "")) != brightness_unit**2):
        raise ValueError("Expected science brightness and variance in MJy/sr units")
    wave, band = map_calibration_to_cutout(science, calibration, plane_id=plane_id, checksum=checksum)
    return CalibratedExposure(image.data, variance, bad, wave, band, WCS(image.header).celestial)


def compare_calibrated_pair(
    reference: CalibratedExposure,
    comparison: CalibratedExposure,
    *,
    minimum_passband_overlap: float,
) -> dict:
    """Align by nearest pixel and compare nominal passband intervals.

    A retained pair must share the requested fraction of the wider interval.
    The interval is centered at CWAVE and has width CBAND. It represents
    nominal bandwidth only. The inputs must be distinct, independent exposures.
    """
    if not 0 < minimum_passband_overlap <= 1:
        raise ValueError("Minimum passband overlap must be in (0, 1]")
    reference_valid = reference.usable()
    comparison_valid = comparison.usable()
    yy, xx = np.indices(reference.image.shape)
    sky = reference.wcs.celestial.pixel_to_world(xx, yy)
    px, py = comparison.wcs.celestial.world_to_pixel(sky)
    height, width = comparison.image.shape
    in_tile = (
        np.isfinite(px) & np.isfinite(py)
        & (px >= -0.5) & (px < width - 0.5)
        & (py >= -0.5) & (py < height - 0.5)
    )
    if not np.any(in_tile):
        raise ValueError("No overlapping celestial pixel footprints")

    ry, rx = np.nonzero(in_tile & reference_valid)
    x = np.floor(px[ry, rx] + 0.5).astype(int)
    y = np.floor(py[ry, rx] + 0.5).astype(int)
    offset = np.hypot(px[ry, rx] - x, py[ry, rx] - y)
    nearby = (offset <= 0.5) & comparison_valid[y, x]
    center1, width1 = reference.wavelength[ry, rx], reference.bandwidth[ry, rx]
    center2, width2 = comparison.wavelength[y, x], comparison.bandwidth[y, x]
    lower = np.maximum(center1 - width1 / 2, center2 - width2 / 2)
    upper = np.minimum(center1 + width1 / 2, center2 + width2 / 2)
    overlap = np.clip((upper - lower) / np.maximum(width1, width2), 0, 1)
    accepted = nearby & (overlap >= minimum_passband_overlap - 1e-12)

    # Do not reuse one detector sample in multiple output reference pixels.
    # This keeps the variance from implying independent repeated measurements.
    source_ids = (y * width + x)[accepted]
    counts = np.bincount(source_ids, minlength=height * width)
    accepted &= counts[y * width + x] == 1
    if not np.any(accepted):
        if np.any(nearby):
            maximum = float(np.max(overlap[nearby]))
            raise ValueError(
                "No aligned, unmasked pixel pairs meet the passband overlap requirement. "
                f"Best nominal overlap among usable aligned pairs: {maximum:.1%}; "
                f"required: {minimum_passband_overlap:.1%}. Reused detector samples are also excluded."
            )
        raise ValueError("No aligned, unmasked pixel pairs meet the passband overlap requirement; no usable aligned samples were found")

    destination = (ry[accepted], rx[accepted])
    source = (y[accepted], x[accepted])
    left = reference.image[destination].astype(np.float64)
    right = comparison.image[source].astype(np.float64)
    variance = reference.variance[destination].astype(np.float64) + comparison.variance[source]
    difference = np.full(reference.image.shape, np.nan)
    difference[destination] = right - left
    mean = np.full(reference.image.shape, np.nan)
    mean[destination] = (left + right) / 2
    variance_map = np.full(reference.image.shape, np.nan)
    variance_map[destination] = variance
    return {
        "difference": difference,
        "difference_variance": variance_map,
        "mean": mean,
        "mean_variance": variance_map / 4,
        "alignment": "celestial WCS nearest native pixel within 0.5 comparison pixels",
        "compatibility": "overlap of CWAVE-centered CBAND intervals as a fraction of the wider interval",
        "minimum_passband_overlap": minimum_passband_overlap,
        "minimum_retained_overlap": float(np.min(overlap[accepted])),
        "retained_pixels": int(np.count_nonzero(accepted)),
        "reference_pixels": int(reference.image.size),
    }


def coadd_calibrated_exposures(exposures: list[CalibratedExposure], *, minimum_passband_overlap: float) -> dict:
    """Mean of independent exposures at native matched pixels and common passbands.

    Each output pixel requires a distinct valid sample from every exposure. The
    intersection of all nominal passband intervals must cover the requested
    fraction of the widest interval; pairwise overlap alone is insufficient.
    """
    if len(exposures) < 2 or not 0 < minimum_passband_overlap <= 1:
        raise ValueError("At least two exposures and a valid overlap threshold are required")
    ref = exposures[0]
    valid = ref.usable().copy()
    yy, xx = np.indices(ref.image.shape)
    sky = ref.wcs.celestial.pixel_to_world(xx, yy)
    total = ref.image.astype(float).copy()
    variance_sum = ref.variance.astype(float).copy()
    lower = ref.wavelength - ref.bandwidth / 2
    upper = ref.wavelength + ref.bandwidth / 2
    widest = ref.bandwidth.copy()
    for exp in exposures[1:]:
        usable = exp.usable()
        px, py = exp.wcs.celestial.world_to_pixel(sky)
        height, width = exp.image.shape
        inside = (np.isfinite(px) & np.isfinite(py) & (px >= -0.5) & (px < width - 0.5)
                  & (py >= -0.5) & (py < height - 0.5))
        ry, rx = np.nonzero(inside & valid)
        x = np.floor(px[ry, rx] + 0.5).astype(int)
        y = np.floor(py[ry, rx] + 0.5).astype(int)
        near = (np.hypot(px[ry, rx] - x, py[ry, rx] - y) <= 0.5) & usable[y, x]
        ids = (y * width + x)[near]
        counts = np.bincount(ids, minlength=height * width)
        near &= counts[y * width + x] == 1
        keep = np.zeros(ref.image.shape, dtype=bool)
        ry, rx, y, x = ry[near], rx[near], y[near], x[near]
        keep[ry, rx] = True
        valid &= keep
        total[ry, rx] += exp.image[y, x]
        variance_sum[ry, rx] += exp.variance[y, x]
        lower[ry, rx] = np.maximum(lower[ry, rx], exp.wavelength[y, x] - exp.bandwidth[y, x] / 2)
        upper[ry, rx] = np.minimum(upper[ry, rx], exp.wavelength[y, x] + exp.bandwidth[y, x] / 2)
        widest[ry, rx] = np.maximum(widest[ry, rx], exp.bandwidth[y, x])
    overlap = np.zeros(ref.image.shape, dtype=float)
    np.divide(upper - lower, widest, out=overlap, where=np.isfinite(widest) & (widest > 0))
    overlap = np.clip(overlap, 0, 1)
    eligible = valid.copy()
    valid &= overlap >= minimum_passband_overlap - 1e-12
    if not np.any(valid):
        if np.any(eligible):
            raise ValueError(
                "No aligned, unmasked pixels meet the common passband overlap requirement. "
                f"Best common nominal overlap: {float(np.max(overlap[eligible])):.1%}; "
                f"required: {minimum_passband_overlap:.1%}."
            )
        raise ValueError("No aligned, unmasked pixels meet the common passband overlap requirement; no usable aligned samples were found")
    count = len(exposures)
    return {
        "mean": np.where(valid, total / count, np.nan),
        "mean_variance": np.where(valid, variance_sum / count**2, np.nan),
        "alignment": "celestial WCS nearest native pixel within 0.5 comparison pixels",
        "compatibility": "common intersection of CWAVE-centered CBAND intervals as a fraction of the widest interval",
        "minimum_passband_overlap": minimum_passband_overlap,
        "minimum_retained_overlap": float(np.min(overlap[valid])),
        "retained_pixels": int(np.count_nonzero(valid)),
        "reference_pixels": int(ref.image.size),
    }
