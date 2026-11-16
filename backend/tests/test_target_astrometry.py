import astropy.units as u
import pytest
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.wcs import WCS

from app.science.target_astrometry import REFERENCES, footprint_pixel, frame_predictions, predict


def test_propagated_catalog_position_uses_cosine_weighted_ra_motion():
    ref = REFERENCES["barnards_star"]
    initial = predict(ref, Time(2000.0, format="jyear"))
    later = predict(ref, Time(2025.0, format="jyear"))
    dra, dec = initial.spherical_offsets_to(later)
    assert dra.to_value(u.mas) == pytest.approx(25 * ref["pm_ra_cosdec"], abs=0.01)
    assert dec.to_value(u.mas) == pytest.approx(25 * ref["pm_dec"], abs=0.01)


def test_prediction_distinguishes_footprint_from_source_identity():
    epoch = Time(60902.865380738, format="mjd", scale="utc")
    position = predict(REFERENCES["barnards_star"], epoch)
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [position.ra.deg, position.dec.deg]
    wcs.wcs.crpix = [10.5, 10.5]
    wcs.wcs.cdelt = [-6.15 / 3600, 6.15 / 3600]
    result = frame_predictions({"MJD-AVG": epoch.mjd}, wcs, (20, 20))["barnards_star"]
    assert result["pixel"]["inside"] is True
    assert set(result) == {"ra", "dec", "mjd", "pixel", "reference_url"}
    assert result["pixel"]["x"] == pytest.approx(9.5)
    outside = wcs.pixel_to_world(19.6, 9.5)
    assert footprint_pixel(wcs, (20, 20), outside)["inside"] is False
    assert footprint_pixel(None, (20, 20), SkyCoord(0, 0, unit="deg")) is None


@pytest.mark.parametrize("header", [{}, {"MJD-AVG": float("nan")}, {"MJD-AVG": "missing"}])
def test_missing_exposure_epoch_returns_no_prediction(header):
    assert frame_predictions(header, None, (20, 20)) == {}
