import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.science.motion import measure_astrometric_motion
from app.science.photometry import compute_aperture_photometry, build_lightcurve_series
from app.science.report import generate_discovery_report
from app.services.demo_service import demo_service

client = TestClient(app)


def test_uncertainty_provenance_prevents_estimated_error_temperature_fit():
    from app.science.spectrum import temperature_fit_inputs, fit_blackbody_continuum

    image = np.ones((21, 21)) + 0.1 * (np.indices((21, 21)).sum(axis=0) % 2)
    image[10, 10] = 20
    variance = np.ones_like(image)
    measured = compute_aperture_photometry(image, center_x=10, center_y=10, variance=variance)
    assert measured["uncertainty_source"] == "variance_propagated"
    variance[10, 10] = np.nan
    estimated = compute_aperture_photometry(image, center_x=10, center_y=10, variance=variance)
    assert estimated["uncertainty_source"] == "background_estimate"
    inputs = [{"detector": f"D{i}", "wavelength_um": float(i), "flux_mjy_sr": 10.,
               "flux_err_mjy_sr": 1., "uncertainty_source": source}
              for i, source in enumerate(["variance_propagated", "variance_propagated", "background_estimate"], 1)]
    result = fit_blackbody_continuum(temperature_fit_inputs(inputs))
    assert result["status"] == "unavailable"
    assert result["temperature_k"] is None


def test_report_variability_is_not_presented_as_diagnosis():
    for flagged in (True, False):
        report = generate_discovery_report("Example", 1, 1, photometry_data={"is_variable": flagged})
        text = report["markdown_report"]
        assert ("Variation flagged" if flagged else "No variation flagged") in text
        assert "does not establish variability or stability" in text


def test_flag_summary_preserves_unknown_quality_state():
    from app.models.schemas import FlagSummary
    summary = FlagSummary(quality_state="unknown_metadata_missing", flagged_pixels=0,
                          total_pixels=400, flag_breakdown={})
    assert summary.model_dump()["quality_state"] == "unknown_metadata_missing"


def test_cutout_cache_does_not_reuse_a_different_demo_cutout(monkeypatch):
    import asyncio
    import io
    import numpy as np
    from astropy.io import fits
    from app.services.cutout_service import CutoutService, cutout_cache_key
    from app.services.cache_service import cache_service
    import app.services.cutout_service as cutout_module

    requested = "https://example.invalid/image.fits"
    old_key = f"{requested}?center=1.000000,2.000000&size=0.0400"
    entries = {old_key: b"untrusted-old-cache"}
    buffer = io.BytesIO()
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(np.ones((2, 2)), name="IMAGE"),
                  fits.ImageHDU(np.zeros((2, 2), dtype=np.int32), name="FLAGS"),
                  fits.ImageHDU(np.ones((2, 2)), name="VARIANCE")]).writeto(buffer)
    fresh = buffer.getvalue()
    monkeypatch.setattr(cache_service, "get", entries.get)
    monkeypatch.setattr(cache_service, "set", lambda key, value: entries.update({key: value}))

    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, **kwargs):
            assert url == old_key
            return type("Response", (), {"status_code": 200, "content": fresh})()

    monkeypatch.setattr(cutout_module.httpx, "AsyncClient", Client)
    result = asyncio.run(CutoutService().fetch_cutout_fits(requested, 1, 2, 0.04))
    assert result == fresh
    assert entries[cutout_cache_key(requested, 1, 2, 0.04)] == fresh
    assert cutout_cache_key(requested, 1, 2, 0.04) != cutout_cache_key(requested, 1, 2, 0.08)


def test_science_endpoints_do_not_silently_change_release(monkeypatch):
    from unittest.mock import AsyncMock
    from app.services.irsa_client import irsa_client

    query = AsyncMock(return_value=[])
    monkeypatch.setattr(irsa_client, "query_observations", query)
    for endpoint in ("photometry", "spectrum"):
        query.reset_mock()
        response = client.get(f"/api/science/{endpoint}?ra=1&dec=2&collection=spherex_dr1")
        assert response.status_code == 200
        assert query.await_count == 1
        assert query.await_args.kwargs["collection"] == "spherex_dr1"


def test_all_release_search_queries_only_the_two_requested_collections(monkeypatch):
    import asyncio
    from app.services.irsa_client import IRSAClient
    import app.services.irsa_client as irsa_module

    seen = []

    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, params):
            collection = params["COLLECTION"]
            seen.append(collection)
            mjd = "60002" if collection == "spherex_dr1" else "60001"
            body = ("obs_id,energy_bandpassname,access_url,t_min\n"
                    f"{collection}-1,SPHEREx-D1,https://example.invalid/{collection}-1,{mjd}\n"
                    f"{collection}-2,SPHEREx-D1,https://example.invalid/{collection}-2,{mjd}\n")
            return type("Response", (), {"status_code": 200, "text": body})()

    monkeypatch.setattr(irsa_module.httpx, "AsyncClient", Client)
    records = asyncio.run(IRSAClient().query_observations(10, 20, collection="ALL", limit=2))
    assert sorted(seen) == ["spherex_dr1", "spherex_qr3"]
    assert [record.collection for record in records] == ["spherex_qr3", "spherex_dr1"]
    seen.clear()
    monkeypatch.setattr(irsa_module, "SEARCH_COLLECTIONS", ("spherex_dr1", "spherex_qr3", "spherex_future"))
    records = asyncio.run(IRSAClient().query_observations(10, 20, collection=None, limit=3))
    assert set(seen) == {"spherex_dr1", "spherex_qr3", "spherex_future"}
    assert {record.collection for record in records} == set(seen)

def test_aperture_photometry_gaussian_source():
    # Create 21x21 image with a Gaussian peak in center
    h, w = 21, 21
    y, x = np.indices((h, w))
    cy, cx = 10.0, 10.0
    r_sq = (y - cy)**2 + (x - cx)**2
    img = 100.0 * np.exp(-r_sq / (2.0 * 1.0**2)) + 5.0 # peak ~105, bg ~5.0
    
    phot = compute_aperture_photometry(img, center_y=10.0, center_x=10.0, aperture_radius=3.0)
    assert phot["peak_flux"] >= 100.0
    assert abs(phot["background_median"] - 5.0) < 0.2
    assert phot["net_flux"] > 0.0
    assert phot["snr"] > 10.0

def test_lightcurve_variability_classification():
    # Construct 3 frames with dramatic variable flux (e.g. RW Aurigae)
    frames = []
    flux_levels = [15.0, 85.0, 22.0]
    for i, flux in enumerate(flux_levels):
        img = np.ones((15, 15), dtype=np.float32) * 2.0 + 0.1 * (np.indices((15, 15)).sum(axis=0) % 2)
        img[7, 7] = flux
        frames.append({
            "frame_id": f"frame_{i}",
            "obs_id": f"obs_{i}",
            "mjd": 60800.0 + i * 30.0,
            "utc_date": f"2025-05-{10+i:02d}T00:00:00",
            "detector": "SPHEREx-D1",
            "collection": "spherex_dr1",
            "image": img,
        })

    lc = build_lightcurve_series(frames)
    assert lc["total_points"] == 3
    assert lc["is_variable"] is True
    assert lc["amplitude_delta_mjy_sr"] > 40.0
    assert lc["max_flux_mjy_sr"] > lc["min_flux_mjy_sr"]

def test_astrometric_motion_measurement():
    # Simulate Barnard's Star motion: 1.6 pixel shift over 1.0 year baseline
    img1 = np.zeros((30, 30), dtype=np.float32)
    img2 = np.zeros((30, 30), dtype=np.float32)
    
    # Epoch 1 centroid at (15.0, 15.0)
    img1[15, 15] = 50.0
    img1[14:17, 14:17] += 20.0
    
    # Epoch 2 centroid shifted by dy = +1.6 px, dx = -0.3 px
    img2[17, 15] = 50.0
    img2[16:19, 14:17] += 20.0

    meta1 = {"mjd": 60890.0, "ra": 269.45208, "dec": 4.69339}
    meta2 = {"mjd": 61255.0, "ra": 269.45208, "dec": 4.69339} # 1.0 year later

    motion = measure_astrometric_motion(img1, img2, meta1, meta2, pixel_scale_arcsec=6.2)
    assert motion["displacement_pixels"] > 1.0
    assert motion["displacement_arcsec"] > 5.0
    assert motion["proper_motion_arcsec_yr"] > 5.0
    assert motion["motion_class"] == "High Proper Motion Candidate"
    assert "position_angle_deg" in motion

def test_catalog_endpoint_barnard(monkeypatch):
    from unittest.mock import AsyncMock
    from app.services.catalog_service import catalog_service
    expected = {"source_id": "Gaia DR3 123", "designation": "Gaia DR3 123", "ra": 269.45, "dec": 4.69,
                "provenance": "VizieR Gaia DR3 (J2016.0)", "pm_dec": None}
    monkeypatch.setattr(catalog_service, "query_catalog", AsyncMock(return_value=[expected]))
    resp = client.get("/api/science/catalogs?ra=269.45208&dec=4.69339&radius=0.08")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sources"] >= 1
    assert data["sources"] == [expected]

def test_photometry_endpoint_demo():
    # Barnard's Star or RW Aurigae in demo dataset
    resp = client.get("/api/science/photometry?ra=269.45208&dec=4.69339&collection=spherex_dr1")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_points" in data
    assert "points" in data

def test_motion_endpoint_on_demo_epochs(monkeypatch):
    from app.services.irsa_client import OBSERVATION_REGISTRY
    # Motion is intentionally guarded for any registered pair; it must not
    # depend on a particular preset manifest or on local/network image files.
    monkeypatch.setitem(OBSERVATION_REGISTRY, "motion-fixture-1", {})
    monkeypatch.setitem(OBSERVATION_REGISTRY, "motion-fixture-2", {})
    resp = client.post("/api/science/motion", json={
        "frame_id_1": "motion-fixture-1",
        "frame_id_2": "motion-fixture-2",
    })
    assert resp.status_code == 422
    assert "source association" in resp.json()["detail"]


def test_discovery_report_endpoint():
    req = {
        "target_name": "Barnard's Star",
        "ra": 269.45208,
        "dec": 4.69339,
        "target_type": "High Proper Motion Star",
        "motion_data": {
            "displacement_arcsec": 10.3,
            "displacement_pixels": 1.66,
            "proper_motion_arcsec_yr": 10.33,
            "proper_motion_mas_yr": 10328.0,
            "motion_class": "High Proper Motion Candidate",
            "delta_time_days": 365.2,
            "delta_time_years": 1.0,
            "position_angle_deg": 355.6,
        },
        "notes": "Verified displacement across DR1 (2025) and QR3 (2026) data releases."
    }
    resp = client.post("/api/science/report", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_id"].startswith("SPX-REP-")
    assert "10.26131/IRSA678" in data["irsa_doi"]
    assert "## 1. Astronomical Target Information" in data["markdown_report"]
    assert "Barnard's Star" in data["markdown_report"]

def test_photometry_preset_differentiation(monkeypatch):
    from app.services.cache_service import cache_service
    from app.services.irsa_client import OBSERVATION_REGISTRY

    # This integration test uses actual staged FITS, which are intentionally
    # absent from a clean checkout. Do not silently fetch from the archive.
    for ra, dec, detector in [(76.95420, 30.40140, None), (269.45208, 4.69339, "SPHEREx-D3")]:
        records = demo_service.find_matching_observations(ra, dec, radius_deg=.05, detector=detector)
        keys = [OBSERVATION_REGISTRY[r.id].get("cached_cutout_url") for r in records]
        cached = [cache_service.get(key) for key in keys if key]
        if sum(bool(data) for data in cached) < 2:
            pytest.skip("At least two real FITS cutouts per target must be staged for this integration test")
    monkeypatch.setattr("app.services.irsa_client.DEMO_CACHE_ONLY", True)
    # Exercise cached targets without assuming the data establish variability.
    resp_rw = client.get("/api/science/photometry?ra=76.95420&dec=30.40140")
    assert resp_rw.status_code == 200
    data_rw = resp_rw.json()
    assert data_rw["total_points"] >= 2
    assert data_rw["valid_points_count"] == sum(p["valid"] for p in data_rw["points"])
    assert all(p["net_flux_mjy_sr"] is None for p in data_rw["points"] if not p["valid"])

    # A non-triggered heuristic does not establish stability.
    resp_b = client.get("/api/science/photometry?ra=269.45208&dec=4.69339&detector=SPHEREx-D3")
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["total_points"] >= 2
    assert data_b["valid_points_count"] == sum(p["valid"] for p in data_b["points"])


def test_photometry_rejects_clipped_and_masked_apertures_without_biasing_subpixel_centers():
    image = np.ones((21, 21))
    image[10, 10] = 20
    full = compute_aperture_photometry(image, center_x=10.4, center_y=10.3, variance=np.ones_like(image))
    assert full["valid"] is True
    assert full["coverage_fraction"] == 1.0
    mask = np.zeros_like(image, dtype=bool)
    mask[10, 10] = True
    masked = compute_aperture_photometry(image, center_x=10.4, center_y=10.3, mask=mask)
    assert masked["valid"] is False and masked["net_flux"] is None
    clipped = compute_aperture_photometry(image, center_x=0.4, center_y=0.3)
    assert clipped["valid"] is False and clipped["flux_err"] is None
    no_background = compute_aperture_photometry(image, center_x=10, center_y=10, source_mask=np.ones_like(mask))
    assert no_background["valid"] is False and no_background["net_flux"] is None
