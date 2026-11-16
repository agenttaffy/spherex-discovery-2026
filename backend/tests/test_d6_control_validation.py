import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from validate_d6_controls import catalog_quality, compare_epochs, crossmatches, recovery_status, response_overlap


def test_match_uses_allwise_motion_epoch_and_mutual_nearest():
    gaia = {"RA_ICRS": "25.0006", "DE_ICRS": "0", "pmRA": "400", "pmDE": "0",
            "Plx": "5", "RUWE": "1.0", "NSS": "0", "Dup": "0", "VarFlag": "NOT_AVAILABLE"}
    wise = {"RAJ2000": "25.00001", "DEJ2000": "0", "RA_pm": "25.00000", "DE_pm": "0",
            "W2mag": "13.8", "e_W2mag": "0.1", "ccf": "0000", "sat2": "0", "ex": "0", "nb": "1", "na": "0"}
    _, _, matched, clean = crossmatches([gaia, dict(gaia, RA_ICRS="25.0007")], [wise])
    assert len(matched) == len(clean) == 1
    assert clean[0][:2] == (0, 0)
    assert clean[0][2] < .02
    assert not crossmatches([gaia], [dict(wise, RA_pm="")])[3]
    for quality in (dict(wise, ccf="0h00"), dict(wise, nb="2"), dict(wise, sat2=".01")):
        assert not catalog_quality(gaia, quality)


def test_nominal_overlap_keeps_worst_core_pixel_and_uses_wider_band():
    assert response_overlap([[4.5, 4.54]], [[4.5, 4.54]]) == pytest.approx(1)
    assert response_overlap([[4.5, 4.54]], [[4.5, 4.54], [4.53, 4.55]]) == pytest.approx(.25)
    assert response_overlap([[4.5, 4.54]], [[4.6, 4.64]]) == 0


def test_recoveries_require_residual_and_full_stability_checks():
    fit = dict(status="experimental fit", formal_snr=6, chi2_tail=.02,
               centroid_trials=4, centroid_change_sigma=.3, gradient_change_sigma=.4)
    assert recovery_status(fit) == "positional recovery only"
    assert recovery_status(dict(fit, formal_snr=4.99)) == "insufficient formal S/N"
    assert recovery_status(dict(fit, chi2_tail=.009)) == "poor nominal fit residuals"
    assert recovery_status(dict(fit, centroid_trials=3)) == "centroid or background sensitivity"
    assert recovery_status(dict(fit, centroid_change_sigma=.61)) == "centroid or background sensitivity"


def test_repeat_requires_both_recoveries_and_matching_passbands():
    star = dict(gaia_source="a", result="positional recovery only", core_passbands_um=[[4.5, 4.54]])
    first = {"stars": [star]}
    assert "eligible" in compare_epochs(first, first)[0]["status"]
    assert "below 90%" in compare_epochs(first, {"stars": [dict(star, core_passbands_um=[[4.6, 4.64]])]})[0]["status"]
    assert "two clean" in compare_epochs(first, {"stars": [dict(star, result="masked core")]})[0]["status"]
