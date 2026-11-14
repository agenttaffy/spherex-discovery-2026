import re
from typing import Tuple, Union
from astropy.coordinates import SkyCoord
import astropy.units as u

def parse_coordinates(
    ra_input: Union[float, int, str],
    dec_input: Union[float, int, str]
) -> Tuple[float, float]:
    """
    Parses and validates Right Ascension and Declination from either:
    1. Decimal degrees (e.g. 133.795129, -7.245147)
    2. Sexagesimal string format (e.g. '08h55m10.831s', '-07d14m42.53s' or '08:55:10.83 -07:14:42.5')
    
    Returns:
        Tuple[float, float]: (ra_degrees, dec_degrees)
        with ra in [0, 360) and dec in [-90, 90]
    """
    # Check if direct numeric inputs
    if isinstance(ra_input, (int, float)) and isinstance(dec_input, (int, float)):
        ra_deg = float(ra_input) % 360.0
        dec_deg = float(dec_input)
        if not (-90.0 <= dec_deg <= 90.0):
            raise ValueError(f"Declination {dec_deg} out of valid range [-90, +90] degrees.")
        return ra_deg, dec_deg

    # String parsing
    ra_str = str(ra_input).strip()
    dec_str = str(dec_input).strip()

    # Try simple float conversion first
    try:
        ra_val = float(ra_str)
        dec_val = float(dec_str)
        ra_deg = ra_val % 360.0
        dec_deg = dec_val
        if not (-90.0 <= dec_deg <= 90.0):
            raise ValueError(f"Declination {dec_deg} out of range [-90, +90]")
        return ra_deg, dec_deg
    except ValueError:
        pass

    # Use Astropy SkyCoord for sexagesimal parsing
    try:
        # Check if units are explicitly included
        if "h" in ra_str or "m" in ra_str:
            coord = SkyCoord(ra_str, dec_str, unit=(u.hourangle, u.deg), frame="icrs")
        elif ":" in ra_str:
            coord = SkyCoord(f"{ra_str} {dec_str}", unit=(u.hourangle, u.deg), frame="icrs")
        else:
            coord = SkyCoord(ra_str, dec_str, unit=(u.deg, u.deg), frame="icrs")

        ra_deg = float(coord.ra.deg) % 360.0
        dec_deg = float(coord.dec.deg)
        if not (-90.0 <= dec_deg <= 90.0):
            raise ValueError(f"Parsed declination {dec_deg} out of range [-90, +90]")
        return ra_deg, dec_deg
    except Exception as e:
        raise ValueError(f"Failed to parse celestial coordinates '{ra_input}', '{dec_input}': {e}")

def format_sexagesimal(ra_deg: float, dec_deg: float) -> str:
    """
    Formats decimal degrees into standard astronomical sexagesimal string.
    Example: 133.795129, -7.245147 -> '08h55m10.83s, -07d14m42.5s'
    """
    coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")
    return coord.to_string("hmsdms", precision=2)
