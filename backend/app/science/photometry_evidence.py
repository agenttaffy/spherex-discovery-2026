"""Summarize aperture eligibility without attributing field signals to a source."""

import astropy.units as u
import numpy as np
from astropy.io import fits

from app.models.schemas import PhotometryEvidence
from app.science.fits_processing import SPHEREX_INFORMATIONAL_FLAG_NAMES, parse_spherex_mask_planes
from app.science.photometry import compute_aperture_photometry

_BRIGHTNESS = u.MJy / u.sr
_ANNULUS_INNER, _ANNULUS_OUTER = 4.5, 7.0


def inspect_photometry(hdul: fits.HDUList, prediction: dict) -> PhotometryEvidence:
    """Describe input and mask limitations at the propagated subpixel position."""
    diagnostics = PhotometryEvidence(
        reason="A native FITS footprint is needed to assess this position.",
        epsf_present="EPSF" in hdul,
    )
    pixel = prediction["pixel"]
    if pixel is None:
        return diagnostics
    if not pixel["inside"]:
        diagnostics.reason = "The predicted position is outside the FITS field."
        return diagnostics

    if any(name not in hdul or hdul[name].data is None for name in ("IMAGE", "VARIANCE", "FLAGS")):
        diagnostics.reason = "A real image, variance plane, and quality flags are required."
        return diagnostics

    image = hdul["IMAGE"].data
    variance = hdul["VARIANCE"].data
    flags = hdul["FLAGS"].data
    planes = parse_spherex_mask_planes(hdul["FLAGS"].header)
    try:
        units_match = (u.Unit(hdul["IMAGE"].header["BUNIT"]) == _BRIGHTNESS
                       and u.Unit(hdul["VARIANCE"].header["BUNIT"]) == _BRIGHTNESS**2)
    except (KeyError, ValueError):
        units_match = False
    if (image.ndim != 2 or variance.shape != image.shape or flags.shape != image.shape
            or not units_match or not np.issubdtype(flags.dtype, np.integer) or not planes.get("SOURCE")):
        diagnostics.reason = "Image or variance units, data shapes, or quality flag definitions are incomplete."
        return diagnostics

    info_bits = 0
    for name in SPHEREX_INFORMATIONAL_FLAG_NAMES:
        info_bits |= planes.get(name, 0)
    flags = flags.astype(np.int64)
    source_mask = (flags & planes["SOURCE"]) != 0
    bad = ((flags & ~info_bits) != 0) | ~np.isfinite(variance) | (variance <= 0)
    x, y = pixel["x"], pixel["y"]
    yy, xx = np.ogrid[:image.shape[0], :image.shape[1]]
    radius = np.hypot(xx - x, yy - y)
    valid = np.isfinite(image) & ~bad
    core = radius <= 2.5
    annulus = (radius >= _ANNULUS_INNER) & (radius <= _ANNULUS_OUTER)
    diagnostics.core_pixels = int(core.sum())
    diagnostics.usable_core_pixels = int((core & valid).sum())
    diagnostics.background_pixels = int((annulus & valid & ~source_mask).sum())
    diagnostics.aperture_status = "unavailable"
    if not diagnostics.usable_core_pixels:
        diagnostics.reason = "No unmasked core pixels have usable brightness and positive variance."
        return diagnostics

    result = compute_aperture_photometry(
        image, center_x=x, center_y=y, mask=bad, variance=variance, source_mask=source_mask,
        annulus_inner=_ANNULUS_INNER, annulus_outer=_ANNULUS_OUTER,
    )
    if not result["valid"]:
        diagnostics.reason = result["reason"]
    elif min(x + 0.5, y + 0.5, image.shape[1] - 0.5 - x, image.shape[0] - 0.5 - y) < _ANNULUS_OUTER:
        diagnostics.reason = "The background annulus crosses the edge of this cutout."
    else:
        diagnostics.aperture_status = "field_sample_only"
        diagnostics.reason = "Field sample only. The pixels pass aperture and background checks. This provides no source detection or target flux."
    return diagnostics
