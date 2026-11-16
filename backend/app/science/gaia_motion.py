"""Approximate Gaia DR3 barycentric directions at an exposure epoch."""
import warnings

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.time import Time
from erfa import ErfaWarning


def propagate_gaia_positions(coordinates, proper_motions, exposure_mjd):
    """Apply catalog angular proper motion; do not model parallax or radial velocity.

    Gaia DR3 positions and proper motions refer to J2016.0 (TCB). Missing or
    invalid proper motions remain at that reference epoch. Returned flags state
    which positions were shifted; a shifted position is not a source match.
    """
    coords = np.array(coordinates, dtype=float, copy=True).reshape((-1, 2))
    applied = np.zeros(len(coords), dtype=bool)
    if exposure_mjd is None or not np.isfinite(exposure_mjd) or not 30000 <= exposure_mjd <= 100000 or proper_motions is None:
        return coords, applied
    valid_indices = [i for i, pm in enumerate(proper_motions)
                     if pm is not None and len(pm) == 2
                     and all(v is not None and np.isfinite(v) and abs(v) <= 1_000_000 for v in pm)]
    if not valid_indices:
        return coords, applied
    motions = np.array([proper_motions[i] for i in valid_indices], dtype=float)
    original = coords[valid_indices]
    with warnings.catch_warnings():
        # With no distances or radial velocities, ERFA adopts a notional
        # distance. We use only the propagated direction and disclose limits.
        warnings.simplefilter("ignore", ErfaWarning)
        sky = SkyCoord(ra=original[:, 0] * u.deg, dec=original[:, 1] * u.deg,
                       pm_ra_cosdec=motions[:, 0] * u.mas / u.yr,
                       pm_dec=motions[:, 1] * u.mas / u.yr,
                       obstime=Time(2016.0, format="jyear", scale="tcb"), frame="icrs")
        shifted = sky.apply_space_motion(new_obstime=Time(exposure_mjd, format="mjd", scale="utc"))
    propagated = np.column_stack((shifted.ra.deg, shifted.dec.deg))
    finite = np.all(np.isfinite(propagated), axis=1)
    for idx, point, usable in zip(valid_indices, propagated, finite):
        if usable:
            coords[idx] = point
            applied[idx] = True
    return coords, applied
