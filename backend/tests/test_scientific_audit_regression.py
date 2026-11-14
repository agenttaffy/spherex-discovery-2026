import pytest
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u

from app.science.fits_processing import (
    evaluate_quality_flags,
    extract_fatal_quality_mask,
    extract_source_mask,
    extract_variance_data,
    extract_calibrated_wavelength,
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


def test_priority_1_extract_source_mask():
    """
    Priority 1: Ensure extract_source_mask correctly identifies nominal source detections
    without classifying them as fatal defects.
    """
    hdr = fits.Header()
    hdr["MSKN0000"] = "SOURCE"
    hdr["MSKM0000"] = 2097152
    hdr["MSKN0001"] = "FULLSAMPLE"
    hdr["MSKM0001"] = 4096
    hdr["MSKN0002"] = "OVERFLOW"
    hdr["MSKM0002"] = 2

    flags = np.array([[0, 2097152], [4096, 2]], dtype=np.int32)
    hdul = fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(data=flags, header=hdr, name="FLAGS")])

    src_mask = extract_source_mask(hdul)
    assert src_mask is not None
    assert src_mask[0, 0] is np.False_ or src_mask[0, 0] == False
    assert src_mask[0, 1] == True  # SOURCE
    assert src_mask[1, 0] == True  # FULLSAMPLE
    assert src_mask[1, 1] == False  # OVERFLOW is not a source mask


def test_priority_2_aperture_photometry_boundary_and_wcs_wave():
    """
    Priority 2: Ensure aperture photometry applies boundary clipping area correction when target
    is near the edge, and extract_calibrated_wavelength reads WCS-WAVE extension.
    """
    # 1. Boundary clipping test
    img = np.ones((20, 20), dtype=np.float32) * 2.0
    img[0, 0] = 50.0  # star right at the corner (0, 0)

    phot_corner = compute_aperture_photometry(
        image=img,
        center_x=0.0,
        center_y=0.0,
        aperture_radius=3.0,
        annulus_inner=4.0,
        annulus_outer=6.0,
    )
    assert phot_corner["coverage_fraction"] < 1.0
    assert phot_corner["coverage_fraction"] > 0.1
    assert phot_corner["net_flux"] > 0.0

    # 2. WCS-WAVE wavelength calibration extraction test
    wcs_wave_hdr = fits.Header()
    # Dummy WCS-WAVE bintable
    x_col = fits.Column(name="X", format="9J", dim="(9)", array=np.array([[1, 256, 511, 766, 1021, 1275, 1530, 1785, 2040]]))
    y_col = fits.Column(name="Y", format="9J", dim="(9)", array=np.array([[1, 256, 511, 766, 1021, 1275, 1530, 1785, 2040]]))
    # 9x9 grid of [4.7, 0.035]
    vals = np.zeros((1, 9, 9, 2), dtype=np.float32)
    vals[0, :, :, 0] = 4.75
    vals[0, :, :, 1] = 0.035
    v_col = fits.Column(name="VALUES", format="162E", dim="(2,9,9)", array=vals)
    wcs_wave_hdu = fits.BinTableHDU.from_columns([x_col, y_col, v_col], name="WCS-WAVE")

    img_hdr = fits.Header()
    img_hdr["CRPIX1W"] = 0.0
    img_hdr["CRPIX2W"] = 0.0
    img_hdr["CRVAL1W"] = 1000.0
    img_hdr["CRVAL2W"] = 1000.0
    img_hdu = fits.ImageHDU(data=np.ones((12, 12), dtype=np.float32), header=img_hdr, name="IMAGE")

    hdul_test = fits.HDUList([fits.PrimaryHDU(), img_hdu, wcs_wave_hdu])
    wave_info = extract_calibrated_wavelength(hdul_test)
    assert wave_info is not None
    assert wave_info["calibration_method"] == "WCS-WAVE"
    assert wave_info["wavelength_um"] == pytest.approx(4.75, rel=1e-3)
    assert wave_info["bandwidth_um"] == pytest.approx(0.035, rel=1e-3)


def test_priority_3_astrometric_vector_components_and_no_wandering():
    """
    Priority 3: Ensure measure_astrometric_motion computes celestial vector components
    (d_ra_cosdec_arcsec, d_dec_arcsec, pm_ra_cosdec_mas_yr, pm_dec_mas_yr) and does NOT
    wander off to a brighter distracter star when target_coord is given.
    """
    w1 = WCS(naxis=2)
    w1.wcs.crpix = [10.0, 10.0]
    w1.wcs.cdelt = [-0.001722, 0.001722]
    w1.wcs.crval = [100.0, 10.0]
    w1.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    w2 = WCS(naxis=2)
    w2.wcs.crpix = [10.0, 10.0]
    w2.wcs.cdelt = [-0.001722, 0.001722]
    w2.wcs.crval = [100.0, 10.0]
    w2.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    # Faint target at center (9, 9), giant stationary distracter star at (2, 2)
    img1 = np.zeros((20, 20), dtype=np.float32)
    img2 = np.zeros((20, 20), dtype=np.float32)
    img1[9, 9] = 10.0
    img2[11, 9] = 10.0  # shifted by 2 pixels along y (Dec)
    img1[2, 2] = 500.0  # bright star
    img2[2, 2] = 500.0  # bright star

    meta1 = {"mjd": 60000.0}
    meta2 = {"mjd": 60365.25}  # 1 year

    motion = measure_astrometric_motion(
        img1=img1,
        img2=img2,
        meta1=meta1,
        meta2=meta2,
        wcs1=w1,
        wcs2=w2,
        target_coord=(100.0, 10.0),
    )

    assert motion["wcs_tracking"] is True
    assert motion["displacement_pixels"] > 1.5
    assert "d_ra_cosdec_arcsec" in motion
    assert "d_dec_arcsec" in motion
    assert "pm_ra_cosdec_mas_yr" in motion
    assert "pm_dec_mas_yr" in motion
    # Motion is along Dec (+y in TAN projection with cdelt2 > 0)
    assert abs(motion["pm_dec_mas_yr"]) > 5000.0


def test_priority_5_stacking_variance_with_masked_pixels():
    """
    Priority 5: Ensure coaddition variance propagation excludes masked pixels from the
    variance sum rather than inflating the variance of unmasked pixels.
    """
    i1 = np.ones((10, 10), dtype=np.float32) * 5.0
    i2 = np.ones((10, 10), dtype=np.float32) * 5.0
    v1 = np.full((10, 10), 0.5, dtype=np.float32)
    v2 = np.full((10, 10), 0.5, dtype=np.float32)

    # Pixel (0, 0) is masked (fatal defect) in frame 2 only
    m1 = np.zeros((10, 10), dtype=bool)
    m2 = np.zeros((10, 10), dtype=bool)
    m2[0, 0] = True

    stacked, stats = compute_coadd_stack(
        images=[i1, i2],
        variances=[v1, v2],
        masks=[m1, m2],
        method="mean",
    )

    # Frame count is 2
    assert stats["frame_count"] == 2
    # Flagged pixels should be tracked
    assert stats["flagged_pixels_count"] >= 1
    # For pixel (0, 0), only 1 frame contributed, so stacked variance should be 0.5, not (0.5+0.5)/1 = 1.0!
    # And overall propagated sigma should be well below 1.0
    assert stats["propagated_noise_sigma"] < 0.6


def test_priority_1_source_mask_background_exclusion_without_aperture_rejection():
    """
    Priority 1 & 3: Ensure source masks (SOURCE plane) are distinguished from fatal pixel rejection:
    source masks in the background annulus are excluded to prevent background noise contamination,
    while nominal source pixels in the target aperture are NOT rejected.
    """
    img = np.ones((25, 25), dtype=np.float32) * 2.0
    # Center target star (at 12, 12)
    img[12, 12] = 20.0

    # A bright contaminant field star in the background annulus
    img[10:15, 15:20] = 50.0

    # Fatal mask (bad pixel) elsewhere
    fatal_mask = np.zeros((25, 25), dtype=bool)
    fatal_mask[0, 0] = True

    # Source mask marking the contaminant star
    src_mask = np.zeros((25, 25), dtype=bool)
    src_mask[10:15, 15:20] = True
    # Also mark the target star itself as a detected source
    src_mask[12, 12] = True

    # Run without source_mask -> contaminant inflates background noise and ruins SNR
    phot_unmasked = compute_aperture_photometry(
        image=img,
        center_y=12.0,
        center_x=12.0,
        mask=fatal_mask,
        aperture_radius=2.5,
        annulus_inner=4.0,
        annulus_outer=7.0,
    )

    # Run with source_mask -> contaminant is excluded from annulus, target is NOT rejected in aperture
    phot_clean = compute_aperture_photometry(
        image=img,
        center_y=12.0,
        center_x=12.0,
        mask=fatal_mask,
        source_mask=src_mask,
        aperture_radius=2.5,
        annulus_inner=4.0,
        annulus_outer=7.0,
    )

    # Contaminant source was excluded from annulus -> background noise is dramatically lower
    assert phot_clean["background_std"] < phot_unmasked["background_std"]
    assert phot_clean["snr"] > phot_unmasked["snr"]
    # Target aperture flux is preserved (not rejected by source mask!)
    assert phot_clean["net_flux"] > 0.0
    assert phot_clean["coverage_fraction"] == 1.0


def test_priority_2_discovery_report_sed_truthfulness():
    """
    Priority 2: Ensure generated discovery reports truthfully present spectrophotometry:
    label interpolation as estimated continuum, distinguish observed bands from 102 channels,
    and include WCS-WAVE calibration provenance without unsupported classification claims.
    """
    from app.science.report import generate_discovery_report

    mock_spec = {
        "total_observed_bands": 2,
        "observed_channels": [
            {"detector": "SPHEREx-D1", "wavelength_um": 0.935, "flux_mjy_sr": 1.25, "flux_err_mjy_sr": 0.05, "calibration_source": "WCS-WAVE"},
            {"detector": "SPHEREx-D3", "wavelength_um": 2.050, "flux_mjy_sr": 2.40, "flux_err_mjy_sr": 0.08, "calibration_source": "WCS-WAVE"},
        ],
        "bands": [],
    }

    rep = generate_discovery_report(
        target_name="WISE 0855 Test",
        ra_deg=133.79513,
        dec_deg=-7.24515,
        spectrum_data=mock_spec,
    )

    md = rep["markdown_report"]
    assert "## 5. Spectral Energy Distribution (SED)" in md
    assert "Estimated Continuum Model (Interpolated across 6 detector bandpasses)" in md
    assert "102 individual channel values represent an interpolated continuum curve" in md
    assert "WCS-WAVE" in md
    assert "SPHEREx-D1" in md
    assert "SPHEREx-D3" in md
