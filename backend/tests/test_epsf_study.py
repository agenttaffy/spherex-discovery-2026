from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_epsf_photometry import Exposure, fit, geometry, render_native


@pytest.fixture
def exposure():
    y, x = np.indices((33, 33), dtype=float) - 16
    radius = np.hypot(x, y)
    stamp = np.exp(-radius**2 / 36) - 0.01 * np.exp(-(radius - 13)**2 / 4)
    stamp /= stamp.sum()
    zones = np.array([(50., 50., 100., 100., 0, 0, stamp)], dtype=[
        ("XCENTER", float), ("YCENTER", float), ("XWIDTH", float), ("YWIDTH", float),
        ("BINX", int), ("BINY", int), ("EPSF", float, (33, 33)),
    ])
    shape = (20, 20)
    area_factor = np.linspace(880, 910, np.prod(shape)).reshape(shape)
    return Exposure(np.zeros(shape), np.ones(shape) * .01, area_factor, np.ones(shape, bool),
                    np.zeros(shape, bool), zones, (5, 5), (0, 0))


def test_signed_native_psf_moves_with_subpixel_phase(exposure):
    y, x = np.indices(exposure.image.shape)
    template = exposure.zone_table["EPSF"][0]
    centered = render_native(template, 9, 9, (5, 5), (x, y))
    shifted = render_native(template, 9.4, 9, (5, 5), (x, y))
    assert centered.sum() == pytest.approx(1)
    assert shifted.sum() == pytest.approx(1)
    assert centered.min() < 0
    assert (shifted * x).sum() > (centered * x).sum()
    assert shifted[1, 1] == 0


def test_weighted_fit_recovers_known_signal_and_noise_scaling(exposure):
    _, reason, model = geometry(exposure, (9.4, 9.6))
    assert reason is None
    intensity = 700 * model[0] + 1.8 + .03 * model[3] - .015 * model[4]
    result = fit(exposure, intensity, model, plane=True)
    assert result.amplitude == pytest.approx(700)
    assert result.reduced_chi2 < 1e-20
    assert fit(exposure, np.full_like(intensity, 1.8), model).amplitude == pytest.approx(0, abs=1e-9)
    exposure.variance *= 4
    assert fit(exposure, intensity, model, plane=True).sigma == pytest.approx(2 * result.sigma)


def test_geometry_refuses_edge_core_mask_and_contaminated_background(exposure):
    assert "edge" in geometry(exposure, (2, 8))[1]
    exposure.valid[9, 9] = False
    assert "core" in geometry(exposure, (9, 9))[1]
    exposure.valid[9, 9] = True
    y, x = np.indices(exposure.image.shape)
    exposure.source = np.hypot(x - 9, y - 9) >= 3.3
    assert "background" in geometry(exposure, (9, 9))[1]
