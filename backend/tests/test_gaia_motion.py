import numpy as np
import pytest
from astropy.time import Time

from app.science.gaia_motion import propagate_gaia_positions


def test_gaia_motion_uses_cosdec_and_reference_epoch():
    positions, applied = propagate_gaia_positions(
        [[10.0, 0.0], [20.0, 60.0], [30.0, 20.0]],
        [[1000.0, 0.0], [1000.0, 0.0], [None, None]],
        Time(2026.0, format="jyear", scale="tcb").utc.mjd,
    )
    assert list(applied) == [True, True, False]
    assert positions[0, 0] == pytest.approx(10.0 + 10.0 / 3600, abs=1e-7)
    assert positions[1, 0] == pytest.approx(20.0 + 20.0 / 3600, abs=1e-6)
    np.testing.assert_array_equal(positions[2], [30.0, 20.0])


def test_missing_epoch_or_bad_motion_keeps_gaia_reference_position():
    for mjd, pm in [(None, [[1.0, 2.0]]), (60000.0, [[float("nan"), 2.0]])]:
        result, applied = propagate_gaia_positions([[10.0, 20.0]], pm, mjd)
        np.testing.assert_array_equal(result, [[10.0, 20.0]])
        assert not applied[0]
