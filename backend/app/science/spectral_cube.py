"""Native-pixel sampling of the IRSA SPHEREx DR1 all-sky FITS cube."""

from math import floor

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS

# IRSA Explanatory Supplement §2.5. SOURCE is informational. Reject
# OVERFLOW, OUTLIER, and any unrecognized propagated flags conservatively.
SOURCE_FLAG = 1 << 21


class CubeCoverageError(ValueError):
    """The requested coordinate falls outside the supplied tile."""


def sample_cube(cube: fits.HDUList, position: SkyCoord) -> dict:
    """Sample the nearest native HPX pixel with no smoothing or photometry."""
    image = cube["IMAGE"]
    hits = cube["NHITS"]
    flags = cube["FLAGS"]
    plane_count, height, width = image.shape
    if plane_count != 102 or hits.shape != image.shape or flags.shape != image.shape:
        raise ValueError("Unexpected IRSA cube dimensions")
    if u.Unit(image.header["BUNIT"]) != u.MJy / u.sr:
        raise ValueError("Unexpected IRSA cube surface brightness unit")

    celestial = WCS(image.header, fobj=cube, naxis=[1, 2])
    px, py = celestial.world_to_pixel(position)
    if not np.all(np.isfinite([px, py])):
        raise CubeCoverageError("Position could not be projected into this HPX tile")
    x, y = floor(float(px) + 0.5), floor(float(py) + 0.5)
    if not (0 <= x < width and 0 <= y < height):
        raise CubeCoverageError("Position falls outside this HPX tile")
    pixel_center = celestial.pixel_to_world(x, y).icrs

    table_hdu = cube["SPECTRAL_CHANNELS"]
    table = table_hdu.data
    if len(table) != plane_count:
        raise ValueError("Spectral metadata does not match the cube planes")
    wavelength_fields = ("WAVELENGTH", "WL_MIN", "WL_MAX", "BANDWIDTH")
    conversion = {
        field: u.Unit(table_hdu.columns[field].unit).to(u.um)
        for field in wavelength_fields
    }
    blank = {
        item.strip()
        for item in cube[0].header.get("BLANKCH", "").split(",")
    } | {"D3:17", "D4:01"}

    brightness = image.section[:, y, x]
    hit_count = hits.section[:, y, x]
    flag_bits = flags.section[:, y, x]
    channels = []
    for index, row in enumerate(table):
        detector, subchannel = divmod(index, 17)
        detector += 1
        subchannel += 1
        if (int(row["DETECTOR"]), int(row["SUBCHAN"])) != (detector, subchannel):
            raise ValueError("Unexpected spectral channel order in the IRSA cube")
        wavelengths = {
            field.lower(): float(row[field]) * conversion[field]
            if np.isfinite(row[field]) else None
            for field in wavelength_fields
        }
        value = float(brightness[index])
        count = int(hit_count[index])
        bits = int(flag_bits[index]) & 0xFFFFFFFF
        if f"D{detector}:{subchannel:02d}" in blank:
            status = "blank_channel"
        elif not np.isfinite(value) or count <= 0:
            status = "no_coverage"
        elif bits & ~SOURCE_FLAG:
            status = "flagged"
        elif wavelengths["wavelength"] is None:
            status = "missing_wavelength"
        else:
            status = "measured"
        channels.append({
            "channel": index + 1,
            "detector": detector,
            "subchannel": subchannel,
            "wavelength_um": wavelengths["wavelength"],
            "wavelength_min_um": wavelengths["wl_min"],
            "wavelength_max_um": wavelengths["wl_max"],
            "bandwidth_um": wavelengths["bandwidth"],
            "hits": count,
            "flags": bits,
            "status": status,
            "archive_brightness_mjy_sr": value if np.isfinite(value) else None,
            "surface_brightness_mjy_sr": value if status == "measured" else None,
        })
    return {
        "pixel": {
            "x": x, "y": y,
            "ra": float(pixel_center.ra.deg),
            "dec": float(pixel_center.dec.deg),
        },
        "channels": channels,
    }


def sample_channel_map(cube: fits.HDUList, x: int, y: int, channel: int) -> dict:
    """Return a bounded native tile subset around the sampled position."""
    _, height, width = cube["IMAGE"].shape
    x0, x1 = max(0, x - 12), min(width, x + 13)
    y0, y1 = max(0, y - 12), min(height, y + 13)
    region = (channel - 1, slice(y0, y1), slice(x0, x1))
    brightness = cube["IMAGE"].section[region]
    hits = cube["NHITS"].section[region]
    flags = cube["FLAGS"].section[region]
    valid = np.isfinite(brightness) & (hits > 0) & ((flags.astype(np.int64) & ~SOURCE_FLAG) == 0)
    detector, subchannel = divmod(channel - 1, 17)
    blank = {item.strip() for item in cube[0].header.get("BLANKCH", "").split(",")}
    if channel in (51, 52) or f"D{detector + 1}:{subchannel + 1:02d}" in blank:
        valid[:] = False
    return {
        "channel": channel,
        "center_x": x - x0,
        "center_y": y - y0,
        "pixels": np.where(valid, brightness.astype(object), None).tolist(),
    }
