import numpy as np
import pytest
from astropy.wcs import WCS
from fastapi.testclient import TestClient

from app.science.fits_processing import cutout_footprint, load_fits_cutout, extract_primary_image
from app.services.cache_service import cache_service
from app.services.demo_service import demo_service
from app.main import app


def test_footprint_uses_pixel_edges_with_rotated_wcs_across_ra_seam():
    w = WCS(naxis=2)
    w.wcs.crpix = [12.0, 8.0]
    w.wcs.crval = [359.999, 20.0]
    w.wcs.cd = np.array([[-0.001, 0.0004], [0.0003, 0.001]])
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    actual = np.array(cutout_footprint(w.to_header(), (16, 24)))
    ra, dec = w.all_pix2world([-0.5, 23.5, 23.5, -0.5], [-0.5, -0.5, 15.5, 15.5], 0)
    np.testing.assert_allclose(actual[:, 0], np.mod(ra, 360), atol=1e-8)
    np.testing.assert_allclose(actual[:, 1], dec, atol=1e-8)
    assert np.any(actual[:, 0] < 1) and np.any(actual[:, 0] > 359)


@pytest.mark.parametrize("preset", demo_service.get_presets(), ids=lambda p: p.id)
def test_cached_target_footprints_match_full_fits_wcs(preset):
    records = demo_service.find_matching_observations(preset.ra, preset.dec, radius_deg=0.01)
    assert records
    entry = next(row for row in demo_service.raw_manifest if row["obs_id"] == records[0].obs_id and row["detector"] == records[0].detector and row["collection"] == records[0].collection)
    hdul = load_fits_cutout(cache_service.get(entry["cutout_url"]))
    image, header = extract_primary_image(hdul)
    corners = np.array(cutout_footprint(header, image.shape))
    assert corners.shape == (4, 2)
    h, w = image.shape
    expected = WCS(header).celestial.all_pix2world([-0.5, w - 0.5, w - 0.5, -0.5], [-0.5, -0.5, h - 0.5, h - 0.5], 0)
    np.testing.assert_allclose(corners[:, 0], np.mod(expected[0], 360), atol=1e-8)
    np.testing.assert_allclose(corners[:, 1], expected[1], atol=1e-8)


def test_missing_celestial_wcs_has_no_footprint():
    assert cutout_footprint({}, (20, 20)) is None


def test_catalog_projection_uses_actual_cutout_wcs():
    preset = demo_service.get_presets()[0]
    record = demo_service.find_matching_observations(preset.ra, preset.dec, radius_deg=0.01)[0]
    entry = next(row for row in demo_service.raw_manifest if row["obs_id"] == record.obs_id and row["detector"] == record.detector and row["collection"] == record.collection)
    image, header = extract_primary_image(load_fits_cutout(cache_service.get(entry["cutout_url"])))
    wcs = WCS(header).celestial
    sky = wcs.pixel_to_world(4.0, 6.0).icrs
    response = TestClient(app).post('/api/frames/project-catalog', json={
        'frame_id': record.id, 'fov': 0.04,
        'coordinates': [[sky.ra.deg, sky.dec.deg], [(sky.ra.deg + 30) % 360, sky.dec.deg]],
    })
    assert response.status_code == 200
    positions = response.json()['positions']
    assert positions[0]['x'] == pytest.approx(4.0, abs=1e-5)
    assert positions[0]['y'] == pytest.approx(6.0, abs=1e-5)
    assert positions[1] is None
