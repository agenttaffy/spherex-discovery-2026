"""Real D6 field co-add checked against an independent native-pixel oracle."""
import io
from contextlib import ExitStack

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from app.science.calibrated_comparison import coadd_calibrated_exposures, prepare_calibrated_exposure
from app.services.cache_service import cache_service
from app.services.cutout_service import cutout_cache_key
from app.services.irsa_client import OBSERVATION_REGISTRY
from app.services.saved_observation_search import saved_observations
from app.services.spectral_calibration_service import _VERIFIED_D6, verified_cached_bytes


def test_three_real_d6_cutouts_match_independent_mean_and_variance(monkeypatch):
    ra, dec, fov = 248.16722768733652, 66.75502445923215, .04
    names = ["2026W01_1A_0257_4", "2026W17_1B_0434_4", "2026W20_1A_0101_1"]
    records = saved_observations(ra, dec, fov, "spherex_dr1", "SPHEREx-D6", 200)
    rows = {row.obs_id: row for row in records}
    for row in records:
        OBSERVATION_REGISTRY.pop(row.id, None)
    calibration = verified_cached_bytes(_VERIFIED_D6)
    if calibration is None or any(name not in rows for name in names):
        pytest.skip("Real R Draconis historical records and D6 calibration are not staged")
    cached = [cache_service.get(cutout_cache_key(rows[name].access_url, ra, dec, fov)) for name in names]
    if not all(cached):
        pytest.skip("Real R Draconis D6 cutouts are not cached")
    with ExitStack() as stack:
        science = [stack.enter_context(fits.open(io.BytesIO(data))) for data in cached]
        spectral = stack.enter_context(fits.open(io.BytesIO(calibration)))
        intervals = []
        for name, hdul in zip(names, science):
            header = hdul["IMAGE"].header
            assert header["OBSID"] == name and str(header["DETECTOR"]).strip() == "6"
            intervals.append((float(header["MJD-BEG"]), float(header["MJD-END"])))
        assert all(a[1] <= b[0] for a, b in zip(sorted(intervals), sorted(intervals)[1:]))
        exposures = [prepare_calibrated_exposure(h, calibration, plane_id=_VERIFIED_D6.plane_id,
                                                  checksum=_VERIFIED_D6.checksum) for h in science]
        actual = coadd_calibrated_exposures(exposures, minimum_passband_overlap=.9)

        def sample(hdul, x, y):
            flags = hdul["FLAGS"]
            allowed = sum(int(flags.header[f"MSKM{k[4:]}"]) for k, value in flags.header.items()
                          if k.startswith("MSKN") and value in {"SOURCE", "FULLSAMPLE"})
            header = hdul["IMAGE"].header
            dx, dy = x + 1 - int(header["CRPIX1A"]), y + 1 - int(header["CRPIX2A"])
            value = float(hdul["IMAGE"].data[y, x])
            variance = float(hdul["VARIANCE"].data[y, x])
            wave, band = (float(spectral[key].data[dy, dx]) for key in ("CWAVE", "CBAND"))
            valid = (int(flags.data[y, x]) & ~allowed) == 0 and np.isfinite([value, variance, wave, band]).all()
            return value, variance, wave, band, valid and min(variance, wave, band) > 0

        shape = science[0]["IMAGE"].data.shape
        grids = [WCS(h["IMAGE"].header).celestial for h in science]
        expected_mean, expected_var = np.full(shape, np.nan), np.full(shape, np.nan)
        candidates = {(y, x): [sample(science[0], x, y)] for y, x in np.ndindex(shape)}
        candidates = {key: values for key, values in candidates.items() if values[0][4]}
        for h, grid in zip(science[1:], grids[1:]):
            proposed = {}
            for (y, x), samples in candidates.items():
                lon, lat = grids[0].all_pix2world(x, y, 0)
                px, py = grid.all_world2pix(lon, lat, 0)
                if not np.isfinite([px, py]).all():
                    continue
                ix, iy = int(np.floor(px + .5)), int(np.floor(py + .5))
                height, width = h["IMAGE"].data.shape
                if not (0 <= ix < width and 0 <= iy < height and np.hypot(px - ix, py - iy) <= .5):
                    continue
                value = sample(h, ix, iy)
                if value[4]:
                    proposed[(y, x)] = (samples + [value], (ix, iy))
            counts = {}
            for _, pixel in proposed.values():
                counts[pixel] = counts.get(pixel, 0) + 1
            candidates = {key: samples for key, (samples, pixel) in proposed.items() if counts[pixel] == 1}
        for (y, x), samples in candidates.items():
            if len(samples) != 3:
                continue
            lo = max(row[2] - row[3] / 2 for row in samples)
            hi = min(row[2] + row[3] / 2 for row in samples)
            if (hi - lo) / max(row[3] for row in samples) < .9 - 1e-12:
                continue
            expected_mean[y, x] = sum(row[0] for row in samples) / 3
            expected_var[y, x] = sum(row[1] for row in samples) / 9
        assert np.isfinite(expected_mean).sum() == 123
        assert actual["retained_pixels"] == 123 and actual["reference_pixels"] == 529
        np.testing.assert_allclose(actual["mean"], expected_mean, equal_nan=True, rtol=1e-12)
        np.testing.assert_allclose(actual["mean_variance"], expected_var, equal_nan=True, rtol=1e-12)

        # Exercise the real application stack path as well as the pure math.
        import asyncio
        from app.api import frames
        from app.services import spectral_calibration_service
        monkeypatch.setattr(spectral_calibration_service, "DEMO_CACHE_ONLY", True)
        for name in names:
            monkeypatch.setitem(OBSERVATION_REGISTRY, rows[name].id, rows[name].model_dump())
        ids = [rows[name].id for name in names]
        for method, scale in [("mean", 1), ("sum", 3)]:
            response = asyncio.run(frames.stack_frames(frames.StackRequest(frame_ids=ids, fov=fov, method=method)))
            assert response["calibration"]["retained_pixels"] == 123
            np.testing.assert_allclose(np.array(response["surface_brightness_mjy_sr"], dtype=float),
                                       expected_mean * scale, equal_nan=True, rtol=1e-12)
            np.testing.assert_allclose(np.array(response["variance_mjy_sr_squared"], dtype=float),
                                       expected_var * scale**2, equal_nan=True, rtol=1e-12)
