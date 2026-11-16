import hashlib
import json
from base64 import b64decode
from contextlib import ExitStack
from io import BytesIO

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from fastapi.testclient import TestClient
from PIL import Image

from app.api import demo
from app.config import CACHE_DIR, MANIFESTS_DIR
from app.main import app
from app.services import cache_service, spectral_calibration_service
from app.services.demo_service import DemoService
from app.services.irsa_client import OBSERVATION_REGISTRY


def _independent_d5_oracle(paths, calibration):
    with ExitStack() as files:
        first, second = [files.enter_context(fits.open(path)) for path in paths]
        spectral = files.enter_context(fits.open(calibration))

        def sample(hdus, x, y):
            header = hdus["IMAGE"].header
            raw_flag = int(hdus["FLAGS"].data[y, x])
            flag_header = hdus["FLAGS"].header
            allowed = sum(int(flag_header[f"MSKM{key[4:]}"]) for key, name in flag_header.items()
                          if key.startswith("MSKN") and name in {"SOURCE", "FULLSAMPLE"})
            det_x, det_y = x + 1 - int(header["CRPIX1A"]), y + 1 - int(header["CRPIX2A"])
            value, variance = (float(hdus[plane].data[y, x]) for plane in ("IMAGE", "VARIANCE"))
            center, band = (float(spectral[plane].data[det_y, det_x]) for plane in ("CWAVE", "CBAND"))
            valid = (raw_flag & ~allowed) == 0 and np.isfinite([value, variance, center, band]).all()
            return value, variance, center, band, valid and min(variance, center, band) > 0

        shape = first["IMAGE"].data.shape
        destination_wcs = WCS(second["IMAGE"].header).celestial
        source_wcs = WCS(first["IMAGE"].header).celestial
        difference, summed, variance = (np.full(shape, np.nan) for _ in range(3))
        matched = set()
        overlaps = []
        for y, x in np.ndindex(shape):
            longitude, latitude = source_wcs.all_pix2world(x, y, 0)
            px, py = destination_wcs.all_world2pix(longitude, latitude, 0)
            ix, iy = round(float(px)), round(float(py))
            height, width = second["IMAGE"].data.shape
            if not (0 <= ix < width and 0 <= iy < height and np.hypot(px - ix, py - iy) <= .5):
                continue
            left, lv, lc, lb, left_valid = sample(first, x, y)
            right, rv, rc, rb, right_valid = sample(second, ix, iy)
            overlap = (min(lc + lb / 2, rc + rb / 2) - max(lc - lb / 2, rc - rb / 2)) / max(lb, rb)
            if left_valid and right_valid and overlap >= .9:
                assert (ix, iy) not in matched
                matched.add((ix, iy))
                overlaps.append(overlap)
                difference[y, x], summed[y, x], variance[y, x] = right - left, left + right, lv + rv
        return difference, summed, variance, min(overlaps)


def test_d5_demo_with_real_fits(monkeypatch):
    entries = json.loads((MANIFESTS_DIR / "d5_comparison.json").read_text(encoding="utf-8"))
    paths = [CACHE_DIR / "demo-comparison" / (hashlib.sha256(row["cutout_url"].encode()).hexdigest() + ".fits")
             for row in entries]
    md5 = "d59bd98b5d1d14ae8d74499b1c1ccb3f"
    calibration = CACHE_DIR / "spectral-calibration" / f"spectral-{md5}.fits"
    if not all(path.exists() for path in (*paths, calibration)):
        pytest.skip("Archived D5 comparison FITS and calibration are staged locally")
    monkeypatch.setattr(demo, "DEMO_CACHE_ONLY", True)
    monkeypatch.setattr(cache_service, "DEMO_CACHE_ONLY", True)
    monkeypatch.setattr(spectral_calibration_service, "DEMO_CACHE_ONLY", True)
    difference, summed, variance, minimum = _independent_d5_oracle(paths, calibration)
    assert np.isfinite(difference).sum() == 207
    assert minimum == pytest.approx(.9862206923573, abs=1e-12)

    with TestClient(app) as client:
        try:
            discovery = client.get("/api/demo/comparison")
            assert discovery.status_code == 200, discovery.text
            records = discovery.json()
            ids = [row["id"] for row in records]
            assert [row["obs_id"] for row in records] == ["2025W17_4B_0027_3", "2026W17_2A_0308_3"]
            assert {row["detector"] for row in records} == {"SPHEREx-D5"}
            assert {row["collection"] for row in records} == {"spherex_dr1"}
            responses = [
                (client.post("/api/frames/diff", json={"frame_id_1": ids[0], "frame_id_2": ids[1]}), difference, variance),
                (client.post("/api/frames/stack", json={"frame_ids": ids, "method": "mean"}), summed / 2, variance / 4),
                (client.post("/api/frames/stack", json={"frame_ids": ids, "method": "sum"}), summed, variance),
            ]
            valid = np.isfinite(difference)
            for response, values, expected_variance in responses:
                assert response.status_code == 200, response.text
                body = response.json()
                assert body["dimensions"] == [15, 15]
                provenance = body["calibration"]
                assert provenance["retained_pixels"] == 207 and provenance["reference_pixels"] == 225
                assert provenance["minimum_retained_overlap"] == pytest.approx(minimum, abs=1e-12)
                assert {row["plane_id"] for row in provenance["calibrations"]} == {demo.D5_PLANE}
                assert {row["md5"] for row in provenance["calibrations"]} == {md5}
                for actual, expected in [
                    (body["surface_brightness_mjy_sr"], values),
                    (body["variance_mjy_sr_squared"], expected_variance),
                ]:
                    np.testing.assert_array_equal(np.equal(actual, None), ~valid)
                    np.testing.assert_allclose(np.array(actual, dtype=float), expected, rtol=0, atol=0)
                with Image.open(BytesIO(b64decode(body["image_base64"].split(",", 1)[1]))) as png:
                    np.testing.assert_array_equal(np.asarray(png.convert("RGBA"))[..., 3] == 255, valid[::-1])
        finally:
            for row in entries:
                OBSERVATION_REGISTRY.pop(f"demo_comparison_{row['obs_id']}_D5", None)


def test_d5_demo_reports_unavailable_instead_of_registering_unverified_data(monkeypatch):
    cache_ids = ("demo_comparison_2025W17_4B_0027_3_D5", "demo_comparison_2026W17_2A_0308_3_D5")
    monkeypatch.setattr(demo, "DEMO_CACHE_ONLY", True)
    monkeypatch.setattr(demo, "verified_cached_bytes", lambda _: None)
    with TestClient(app) as client:
        response = client.get("/api/demo/comparison")
    assert response.status_code == 503
    assert "verified calibration" in response.json()["detail"]
    assert all(key not in OBSERVATION_REGISTRY for key in cache_ids)


def test_preview_wise_pair_remains_incompatible(monkeypatch):
    manifest = CACHE_DIR / "demo_multiepoch" / "demo_dataset.json"
    md5 = "e665c189ad63ca0cd032c0797e8aabf2"
    calibration_name = f"spectral-{md5}.fits"
    calibration_paths = (CACHE_DIR / calibration_name, CACHE_DIR / "spectral-calibration" / calibration_name)
    if not manifest.is_file() or not any(path.is_file() for path in calibration_paths):
        pytest.skip("Optional ten-frame preview and D6 calibration are staged locally")
    monkeypatch.setattr(cache_service, "DEMO_DATASET_FILE", manifest)
    monkeypatch.setattr(spectral_calibration_service, "DEMO_CACHE_ONLY", True)
    previous = OBSERVATION_REGISTRY.copy()
    try:
        preview = DemoService(manifest)
        epochs = {"2025W19_1B_0116_2", "2026W19_2A_0952_1"}
        ids = [record.id for record in preview.demo_records if record.obs_id in epochs]
        assert len(ids) == 2
        with TestClient(app) as client:
            responses = (
                client.post("/api/frames/diff", json={"frame_id_1": ids[0], "frame_id_2": ids[1]}),
                client.post("/api/frames/stack", json={"frame_ids": ids}),
            )
        for response in responses:
            assert response.status_code == 422
            assert "No aligned, unmasked pixel pairs meet the passband overlap requirement" in response.json()["detail"]
    finally:
        OBSERVATION_REGISTRY.clear()
        OBSERVATION_REGISTRY.update(previous)
