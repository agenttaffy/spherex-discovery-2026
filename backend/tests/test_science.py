import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.science.motion import measure_astrometric_motion
from app.science.photometry import compute_aperture_photometry, build_lightcurve_series
from app.science.report import generate_discovery_report
from app.services.demo_service import demo_service

client = TestClient(app)

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
        img = np.ones((15, 15), dtype=np.float32) * 2.0
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

def test_catalog_endpoint_barnard():
    resp = client.get("/api/science/catalogs?ra=269.45208&dec=4.69339&radius=0.08")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sources"] >= 1
    names = [s["designation"] for s in data["sources"]]
    assert any("Barnard" in n for n in names)
    b_star = [s for s in data["sources"] if "Barnard" in s["designation"]][0]
    assert b_star["pm_dec"] > 9000.0  # ~10,328 mas/yr

def test_photometry_endpoint_demo():
    # Barnard's Star or RW Aurigae in demo dataset
    resp = client.get("/api/science/photometry?ra=269.45208&dec=4.69339&collection=spherex_dr1")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_points" in data
    assert "points" in data

def test_motion_endpoint_on_demo_epochs():
    barnard_recs = demo_service.find_matching_observations(269.45208, 4.69339, radius_deg=0.1)
    d3_recs = [r for r in barnard_recs if "D3" in r.detector]
    if len(d3_recs) >= 2:
        resp = client.post("/api/science/motion", json={
            "frame_id_1": d3_recs[0].id,
            "frame_id_2": d3_recs[1].id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["eligible"] is True
        assert "motion" in data
        assert "proper_motion_arcsec_yr" in data["motion"]

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
