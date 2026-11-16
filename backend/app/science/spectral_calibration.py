"""Validated mapping of a matched spectral calibration onto an image cutout.

IRSA's CWAVE and CBAND products are full-detector maps. The caller must use a
verified association between the science header's plane ID and the calibration
artifact, with a documented expected digest; it must not infer a calibration
version from a filename or observing date.
"""
import hashlib
import io
import re
from typing import Tuple

import numpy as np
from astropy.io import fits

_CALIBRATION_HISTORY = re.compile(
    r"\[CALIB\]\s+spectral_wcs\s+([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})\b",
    re.I,
)


def spectral_calibration_plane_id(science: fits.HDUList) -> str:
    history = science["IMAGE"].header.get("HISTORY", [])
    ids = {match.group(1).lower() for line in history
           if (match := _CALIBRATION_HISTORY.search(str(line)))}
    if len(ids) != 1:
        raise ValueError("Exactly one spectral calibration ID is required in image provenance")
    return ids.pop()


def map_calibration_to_cutout(
    science: fits.HDUList, calibration_bytes: bytes, *, plane_id: str, checksum: str
) -> Tuple[np.ndarray, np.ndarray]:
    """Return CWAVE and CBAND for a cutout, refusing unverified inputs.

    ``plane_id`` must match the science image's calibration provenance. The
    caller supplies an expected MD5 from a documented association: either an
    IRSA TAP checksum or a pinned locally computed cross-mirror digest. Any
    additional pinned SHA-256 is verified by the caller before this function.
    Returned values are in microns. This maps detector pixels only; it does not
    establish inter-epoch compatibility.
    """
    expected = checksum.lower().removeprefix("md5:")
    if not re.fullmatch(r"[0-9a-f]{32}", expected):
        raise ValueError("A valid expected MD5 digest is required")
    if hashlib.md5(calibration_bytes).hexdigest() != expected:
        raise ValueError("Spectral calibration checksum mismatch")

    image = science["IMAGE"]
    if plane_id.lower() != spectral_calibration_plane_id(science):
        raise ValueError("Spectral calibration ID does not match image provenance")
    if image.data is None or image.data.ndim != 2:
        raise ValueError("A two-dimensional image cutout is required")
    hdr = image.header
    keys = ("CRPIX1A", "CRPIX2A", "CRVAL1A", "CRVAL2A", "CTYPE1A", "CTYPE2A",
            "CDELT1A", "CDELT2A", "DETECTOR")
    if any(key not in hdr for key in keys):
        raise ValueError("Cutout-to-detector mapping or detector is unavailable")
    if float(hdr["CDELT1A"]) != 1.0 or float(hdr["CDELT2A"]) != 1.0:
        raise ValueError("Unsupported cutout-to-detector pixel scale")
    if (str(hdr["CTYPE1A"]).strip().upper() != "LINEAR" or
        str(hdr["CTYPE2A"]).strip().upper() != "LINEAR" or
        float(hdr["CRVAL1A"]) != 0.0 or float(hdr["CRVAL2A"]) != 0.0):
        raise ValueError("Unsupported cutout-to-detector coordinate mapping")
    if any(key in hdr for key in ("CD1_1A", "CD1_2A", "CD2_1A", "CD2_2A")):
        raise ValueError("Unsupported cutout-to-detector matrix")
    if any(float(hdr.get(key, default)) != default for key, default in
           (("PC1_1A", 1.0), ("PC1_2A", 0.0), ("PC2_1A", 0.0), ("PC2_2A", 1.0))):
        raise ValueError("Unsupported cutout-to-detector matrix")
    offsets = [1.0 - float(hdr["CRPIX1A"]), 1.0 - float(hdr["CRPIX2A"])]
    if any(not np.isfinite(v) or abs(v - round(v)) > 1e-8 for v in offsets):
        raise ValueError("Cutout-to-detector mapping is not pixel aligned")
    x0, y0 = (int(round(v)) for v in offsets)
    height, width = image.data.shape

    with fits.open(io.BytesIO(calibration_bytes), memmap=False) as hdul:
        wave_hdu, band_hdu = hdul["CWAVE"], hdul["CBAND"]
        if any(str(h.header.get("DETECTOR")) != str(hdr["DETECTOR"]) for h in (wave_hdu, band_hdu)):
            raise ValueError("Spectral calibration detector mismatch")
        if any(str(h.header.get("BUNIT", "")).lower() not in ("um", "micron") for h in (wave_hdu, band_hdu)):
            raise ValueError("Unknown spectral calibration units")
        wave, band = wave_hdu.data, band_hdu.data
        if wave is None or band is None or wave.ndim != 2 or wave.shape != band.shape:
            raise ValueError("Invalid spectral calibration arrays")
        if x0 < 0 or y0 < 0 or x0 + width > wave.shape[1] or y0 + height > wave.shape[0]:
            raise ValueError("Cutout extends beyond the spectral calibration arrays")
        wave_cutout = np.array(wave[y0:y0 + height, x0:x0 + width], dtype=np.float64, copy=True)
        band_cutout = np.array(band[y0:y0 + height, x0:x0 + width], dtype=np.float64, copy=True)
    valid = np.isfinite(wave_cutout) & np.isfinite(band_cutout) & (wave_cutout > 0) & (band_cutout > 0)
    wave_cutout[~valid] = np.nan
    band_cutout[~valid] = np.nan
    return wave_cutout, band_cutout
