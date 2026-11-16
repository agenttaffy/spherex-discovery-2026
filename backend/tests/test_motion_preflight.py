import sys
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.time import Time
from astropy.wcs import WCS

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_motion_preflight import apparent_position, assess_pair, candidate_rows
from app.science.calibrated_comparison import CalibratedExposure
from app.science.target_astrometry import REFERENCES, predict


def test_nearby_object_prediction_includes_earth_parallax():
    epoch = Time("2026-05-04", scale="utc")
    apparent = apparent_position("wise_0855", epoch, {})
    barycentric = predict(REFERENCES["wise_0855"], epoch)
    assert .05 < apparent.separation(barycentric).arcsec < .45
    gaia = {"kapteyn": {"row": dict(RA_ICRS="77.95993735", DE_ICRS="-45.0438127", pmRA="6491.223",
                                  pmDE="-5708.614", Plx="254.1986", RV="245.05")}}
    first = apparent_position("kapteyn", epoch, gaia)
    second = apparent_position("kapteyn", epoch + 365.25 * u.day, gaia)
    assert 8.5 < first.separation(second).arcsec < 8.8


def test_query_sampling_deduplicates_and_spreads_distinct_d6_exposures():
    records = []
    for mjd in range(61032, 61050):
        row = dict(obs_id=str(mjd), release="spherex_dr1", energy_bandpassname="SPHEREx-D6",
                   t_min=mjd, t_max=mjd + .001, access_url="https://example.invalid/archive.fits")
        records.extend([row, dict(row, energy_bandpassname="SPHEREx-D3"), dict(row, release="spherex_qr3")])
    all_rows, selected = candidate_rows(records, count=4)
    assert len(all_rows) == 18
    assert len(selected) == 8
    assert [selected[i]["observation"] for i in [0, 3, 4, 7]] == ["61032", "61040", "61041", "61049"]


def test_valid_image_overlap_cannot_override_source_mask_or_passband():
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [10, 30]
    wcs.wcs.crpix = [3, 3]
    wcs.wcs.cdelt = [-.002, .002]
    shape = (5, 5)
    exp = CalibratedExposure(np.ones(shape), np.ones(shape), np.zeros(shape, bool),
                             np.full(shape, 4.52), np.full(shape, .04), wcs)
    first = dict(target="a", observation="epoch1", mjd=60800, predicted_deg=[10, 30],
                 core=[19, 19], core_contained=True, passbands=[[4.50, 4.54]])
    second = dict(first, observation="epoch2", mjd=61160)
    passed = assess_pair((first, exp), (second, exp))
    assert passed["aligned_field_pixels"] == 25
    assert not passed["rejection_reasons"] and not passed["validated_motion"]
    bad = assess_pair((first, exp), (dict(second, core=[18, 19], passbands=[[4.52, 4.56]]), exp))
    assert bad["aligned_field_pixels"] == 25
    assert len(bad["rejection_reasons"]) == 2
    same = assess_pair((first, exp), (dict(second, observation="epoch1"), exp))
    assert any("independent" in reason for reason in same["rejection_reasons"])
