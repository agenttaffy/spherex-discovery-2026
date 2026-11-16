"""Catalog predictions evaluated at the timestamp of the displayed FITS exposure."""

import json
from math import isfinite
from warnings import catch_warnings, filterwarnings

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.wcs import NoConvergence, WcsError
from astropy.wcs.utils import skycoord_to_pixel

from app.config import MANIFESTS_DIR

REFERENCES = json.loads((MANIFESTS_DIR / "target_astrometry.json").read_text(encoding="utf-8"))


def predict(reference: dict, epoch: Time) -> SkyCoord:
    """Linear tangent-plane proper motion, without parallax or perspective acceleration."""
    years = epoch.jyear - reference["epoch_jyear"]
    origin = SkyCoord(reference["ra"], reference["dec"], unit="deg", frame="icrs")
    return origin.spherical_offsets_by(
        reference["pm_ra_cosdec"] * years * u.mas, reference["pm_dec"] * years * u.mas,
    )


def footprint_pixel(wcs, shape: tuple[int, int], position: SkyCoord) -> dict | None:
    if wcs is None or not wcs.has_celestial:
        return None
    # Out-of-projection positions may reach the SIP solver as NaNs. Report
    # those as unavailable without flooding frame requests with solver warnings.
    with catch_warnings():
        filterwarnings("ignore", "All-NaN slice encountered", RuntimeWarning, r"astropy\.wcs\.wcs")
        x, y = map(float, skycoord_to_pixel(position, wcs.celestial))
    height, width = shape
    if not (isfinite(x) and isfinite(y)):
        return None
    return {"x": x, "y": y, "inside": -0.5 <= x < width - 0.5 and -0.5 <= y < height - 0.5}


def frame_predictions(header, wcs, shape: tuple[int, int]) -> dict:
    try:
        mjd = float(header["MJD-AVG"])
        if not isfinite(mjd):
            return {}
        epoch = Time(mjd, format="mjd", scale="utc")
    except (KeyError, ValueError, TypeError):
        return {}

    results = {}
    for target_id, reference in REFERENCES.items():
        position = predict(reference, epoch)
        try:
            pixel = footprint_pixel(wcs, shape, position)
        except (ValueError, NoConvergence, WcsError):
            pixel = None
        results[target_id] = {
            "ra": float(position.ra.deg), "dec": float(position.dec.deg), "mjd": mjd,
            "pixel": pixel, "reference_url": reference["reference_url"],
        }
    return results
