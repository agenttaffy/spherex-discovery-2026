import pytest
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u

from app.science.fits_processing import (
    evaluate_quality_flags,
    extract_fatal_quality_mask,
    extract_variance_data,
    parse_spherex_mask_planes,
)
from app.science.photometry import compute_aperture_photometry, build_lightcurve_series
from app.science.spectrum import generate_spectrum_for_target
from app.science.motion import measure_astrometric_motion
from app.science.comparison import check_comparison_eligibility, compute_difference_frame
from app.science.stacking import compute_coadd_stack
from app.science.catalogs import query_reference_catalog, PROVENANCE_DEMO, PROVENANCE_LIVE_GAIA
from app.services.catalog_service import catalog_service


def test_priority_1_flags_metadata_and_source_mask_distinction():
    """
    Priority 1: Ensure nominal SOURCE mask (2097152) is distinguished from fatal defect flags.
    Non-zero pixels are not automatically bad!
    """
    hdr = fits.Header()
    hdr["MSKN0000"] = "TRANSIENT"
    hdr["MSKM0000"] = 1
    hdr["MSKN0001"] = "OVERFLOW"
    hdr["MSKM0001"] = 2
    hdr["MSKN0002"] = "SUR_ERROR"
    hdr["MSKM0002"] = 4
    hdr["MSKN0006"] = "NONFUNC"
    hdr["MSKM0006"] = 64
    hdr["MSKN0010"] = "HOT"
    hdr["MSKM0010"] = 1024
    hdr["MSKN0012"] = "FULLSAMPLE"
    hdr["MSKM0012"] = 4096
    hdr["MSKN0021"] = "SOURCE"
    hdr["MSKM0021"] = 2097152
    hdr["MSKN0027"] = "SNOWBALL"
    hdr["MSKM0027"] = 134217728

    planes = parse_spherex_mask_planes(hdr)
    assert planes["SOURCE"] == 2097152
    assert planes["OVERFLOW"] == 2
    assert planes["NONFUNC"] == 64

    # 4 pixels:
    # 0: Clean
    # 1: Nominal SOURCE only (2097152) -> NOT a bad pixel!
    # 2: FULLSAMPLE only (4096) -> NOT a bad pixel!
    # 3: OVERFLOW (saturation) + SOURCE (2097154) -> FATAL defect!
    flags_arr = np.array([0, 2097152, 4096, 2097154], dtype=np.int32).reshape((2, 2))
    flags_hdu = fits.ImageHDU(data=flags_arr, header=hdr, name="FLAGS")
    hdul = fits.HDUList([fits.PrimaryHDU(), flags_hdu])

    summary = evaluate_quality_flags(hdul)
    assert summary["total_pixels"] == 4
    # Only pixel 3 has a fatal defect; pixels 1 and 2 are valid informational detections
    assert summary["flagged_pixels"] == 1
    assert summary["flag_breakdown"]["saturated"] == 1
    assert summary["flag_breakdown"]["source_detection"] == 2

    fatal_mask = extract_fatal_quality_mask(hdul)
    assert fatal_mask[0, 0] == False
    assert fatal_mask[0, 1] == False  # SOURCE only is not fatal
    assert fatal_mask[1, 0] == False  # FULLSAMPLE only is not fatal
    assert fatal_mask[1, 1] == True   # Saturated is fatal


def test_priority_2_photometry_wcs_target_measurement_and_variance():
    """
    Priority 2: Aperture photometry must measure the requested RA/Dec through image WCS,
    not peak-seek elsewhere, and compute real flux uncertainty from VARIANCE extension.
    """
    w = WCS(naxis=2)
    w.wcs.crpix = [10.0, 10.0]
    w.wcs.cdelt = [-0.01, 0.01]
    w.wcs.crval = [180.0, 45.0]
    w.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    # Image with background 2.0
    img = np.ones((20, 20), dtype=np.float32) * 2.0
    # True target at RA=180.0, Dec=45.0 -> pixel (9.0, 9.0) (0-indexed)
    img[9, 9] = 25.0
    # Put a brighter distracter star in the corner at pixel (2, 2)
    img[2, 2] = 100.0

    # Variance array with 0.25 (MJy/sr)^2
    var = np.full((20, 20), 0.25, dtype=np.float32)

    # Photometry at true target coordinates (180.0, 45.0)
    phot = compute_aperture_photometry(
        image=img,
        target_coord=(180.0, 45.0),
        wcs=w,
        variance=var,
        aperture_radius=2.5,
    )

    # Net flux should measure around pixel (9, 9) (~23 MJy/sr above background)
    assert phot["net_flux"] > 15.0
    assert phot["net_flux"] < 50.0  # NOT 100+ from the distracter star!
    # Real flux error should be propagated from variance
    assert phot["flux_err"] > 0.0
    assert phot["snr"] > 8.0


def test_priority_2_spectrum_interpolation_labeled_correctly():
    """
    Priority 2: In spectrum generation, ensure 102 channels are explicitly labeled
    as 'Estimated Continuum Model (Interpolated)' and separated from observed detector channels.
    """
    from app.services.demo_service import demo_service
    ra, dec = 269.45208, 4.69339  # Barnard's Star
    recs = demo_service.find_matching_observations(ra, dec, radius_deg=0.1)
    spec = generate_spectrum_for_target(ra, dec, recs, None)

    assert "continuum_model_label" in spec
    assert "Estimated Continuum Model (Interpolated)" in spec["continuum_model_label"]
    assert "observed_channels" in spec
    # Verify each channel in channels_102 carries interpolated metadata
    for ch in spec["channels_102"]:
        assert ch["is_interpolated"] is True
        assert ch["is_observed"] is False
        assert "Estimated Continuum Model (Interpolated)" in ch["model_label"]


def test_priority_3_astrometric_motion_wcs_target_tracking():
    """
    Priority 3: Track the requested target across epochs with WCS, not brightest pixel,
    and compute proper motion using true epoch baseline in years.
    """
    w1 = WCS(naxis=2)
    w1.wcs.crpix = [15.0, 15.0]
    w1.wcs.cdelt = [-0.001722, 0.001722]  # ~6.2 arcsec/pix
    w1.wcs.crval = [269.45208, 4.69339]
    w1.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    w2 = WCS(naxis=2)
    w2.wcs.crpix = [15.0, 15.0]
    w2.wcs.cdelt = [-0.001722, 0.001722]
    w2.wcs.crval = [269.45208, 4.69339]
    w2.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    img1 = np.zeros((30, 30), dtype=np.float32)
    img2 = np.zeros((30, 30), dtype=np.float32)

    # Target star near center
    img1[14, 14] = 40.0
    img2[16, 14] = 40.0  # shifted by ~2 pixels in epoch 2

    # Put a much brighter stationary star at the corner in both images
    img1[3, 3] = 200.0
    img2[3, 3] = 200.0

    meta1 = {"mjd": 60800.0, "ra": 269.45208, "dec": 4.69339}
    meta2 = {"mjd": 61165.25, "ra": 269.45208, "dec": 4.69339}  # Exactly 1.0 year later

    motion = measure_astrometric_motion(
        img1=img1,
        img2=img2,
        meta1=meta1,
        meta2=meta2,
        wcs1=w1,
        wcs2=w2,
        target_coord=(269.45208, 4.69339),
    )

    # Should detect the target's motion (~2 pixels * 6.2" = ~12.4"), NOT 0 from the corner star!
    assert motion["displacement_pixels"] > 1.0
    assert motion["displacement_arcsec"] > 6.0
    assert motion["proper_motion_arcsec_yr"] > 6.0
    assert motion["delta_time_years"] == pytest.approx(1.0, rel=1e-3)
    assert motion["wcs_tracking"] is True


def test_priority_4_differencing_lvf_compatibility_and_reprojection_error():
    """
    Priority 4: Check LVF wavelength compatibility and raise clear errors on reprojection/no overlap.
    """
    # Incompatible LVF wavelength coverage
    meta_d1 = {"id": "m1", "detector": "SPHEREx-D1", "em_min": 0.75, "em_max": 1.12, "ra": 100.0, "dec": 20.0, "mjd": 60000.0}
    meta_d6 = {"id": "m2", "detector": "SPHEREx-D6", "em_min": 4.42, "em_max": 5.00, "ra": 100.0, "dec": 20.0, "mjd": 60100.0}
    eligible, reason = check_comparison_eligibility(meta_d1, meta_d6)
    assert eligible is False
    assert "Incompatible" in reason

    # Completely non-overlapping sky pointings with WCS
    w1 = WCS(naxis=2)
    w1.wcs.crpix = [10.0, 10.0]
    w1.wcs.cdelt = [-0.01, 0.01]
    w1.wcs.crval = [100.0, 20.0]
    w1.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    w2 = WCS(naxis=2)
    w2.wcs.crpix = [10.0, 10.0]
    w2.wcs.cdelt = [-0.01, 0.01]
    w2.wcs.crval = [250.0, -40.0]  # Far away
    w2.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    i1 = np.ones((20, 20), dtype=np.float32) * 5.0
    i2 = np.ones((20, 20), dtype=np.float32) * 5.0

    with pytest.raises(ValueError, match="no overlapping celestial sky coverage"):
        compute_difference_frame(i1, i2, wcs1=w1, wcs2=w2)


def test_priority_5_stacking_detector_compatibility_and_variance():
    """
    Priority 5: Reject stacking incompatible detectors and propagate variance.
    """
    i1 = np.ones((20, 20), dtype=np.float32) * 5.0
    i2 = np.ones((20, 20), dtype=np.float32) * 5.0

    # Incompatible detector arrays
    with pytest.raises(ValueError, match="Incompatible detector bands"):
        compute_coadd_stack([i1, i2], detectors=["SPHEREx-D1", "SPHEREx-D5"])

    # Variance propagation
    v1 = np.full((20, 20), 0.5, dtype=np.float32)
    v2 = np.full((20, 20), 0.5, dtype=np.float32)
    stacked, stats = compute_coadd_stack(
        [i1, i2],
        variances=[v1, v2],
        method="mean"
    )
    assert stacked.shape == (20, 20)
    assert "propagated_noise_sigma" in stats
    # For mean of 2 frames with variance 0.5 each: Var_stack = (0.5+0.5)/4 = 0.25, sigma = 0.5
    assert stats["propagated_noise_sigma"] == pytest.approx(0.5, rel=0.1)


def test_priority_6_gaia_provenance_explicit_labeling():
    """
    Priority 6: Explicitly label catalog sources with provenance ('Curated Reference Catalog (Demo)').
    """
    import asyncio
    sources = asyncio.run(query_reference_catalog(ra=269.45208, dec=4.69339, radius_deg=0.08))
    assert len(sources) > 0
    for s in sources:
        assert "provenance" in s
        assert s["provenance"] in (PROVENANCE_DEMO, PROVENANCE_LIVE_GAIA)
        assert "catalog_source" in s
