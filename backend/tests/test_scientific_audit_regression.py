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


def test_priority_3_pointing_shift_not_presented_as_target_motion():
    """
    Priority 3: Ensure telescope pointing registration shifts between observation epochs
    are NEVER presented as target proper motion. A stationary celestial source must
    remain classified as stationary with near-zero displacement even when the telescope
    pointing offset is several pixels.
    """
    from astropy.coordinates import SkyCoord
    import astropy.units as u

    # Epoch 1: Pointing centered at (100.0, 10.0), target at (100.0, 10.0) -> pixel (9, 9)
    w1 = WCS(naxis=2)
    w1.wcs.crpix = [10.0, 10.0]
    w1.wcs.cdelt = [-0.001722, 0.001722] # ~6.2 arcsec/pixel
    w1.wcs.crval = [100.0, 10.0]
    w1.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    # Epoch 2: Pointing shifted by ~3 pixels in X and ~3 pixels in Y
    w2 = WCS(naxis=2)
    w2.wcs.crpix = [10.0, 10.0]
    w2.wcs.cdelt = [-0.001722, 0.001722]
    w2.wcs.crval = [100.0 + 3 * 0.001722, 10.0 + 3 * 0.001722]
    w2.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    sc = SkyCoord(100.0 * u.deg, 10.0 * u.deg, frame="icrs")
    px1, py1 = w1.world_to_pixel(sc)
    px2, py2 = w2.world_to_pixel(sc)

    img1 = np.zeros((20, 20), dtype=np.float32)
    img2 = np.zeros((20, 20), dtype=np.float32)
    img1[int(round(float(py1))), int(round(float(px1)))] = 50.0
    img2[int(round(float(py2))), int(round(float(px2)))] = 50.0

    meta1 = {"mjd": 60000.0, "ra": 100.0, "dec": 10.0}
    meta2 = {"mjd": 60365.25, "ra": 100.0, "dec": 10.0}  # 1.0 year later

    motion = measure_astrometric_motion(
        img1=img1,
        img2=img2,
        meta1=meta1,
        meta2=meta2,
        wcs1=w1,
        wcs2=w2,
        target_coord=(100.0, 10.0),
    )

    # Stationary target must NOT inherit telescope pointing shift!
    assert motion["wcs_tracking"] is True
    assert motion["displacement_arcsec"] < 0.5  # true celestial displacement ~ 0
    assert motion["displacement_pixels"] < 0.1  # projected reference pixel displacement ~ 0
    assert motion["proper_motion_arcsec_yr"] < 0.5
    assert motion["motion_class"] == "Stationary / Sub-threshold"
    assert "frame_registration_shift_pixels" in motion

    # Centroid 2 must be projected into Epoch 1's reference frame (matching difference frame)
    assert motion["centroid_1"] == [9.0, 9.0]
    assert motion["centroid_2"][0] == pytest.approx(9.0, abs=0.1)
    assert motion["centroid_2"][1] == pytest.approx(9.0, abs=0.1)


def test_priority_1_lightcurve_source_mask_background_exclusion():
    """
    Priority 1: Ensure build_lightcurve_series respects source_mask on epoch frames,
    excluding neighboring sources from the background annulus to prevent background inflation.
    """
    from app.science.photometry import build_lightcurve_series

    h, w = 25, 25
    img = np.ones((h, w), dtype=np.float32) * 5.0
    # Target at center (12, 12)
    img[12, 12] = 80.0
    # Contaminant source at (12, 17) in background annulus
    img[12, 17] = 200.0

    fatal_mask = np.zeros((h, w), dtype=bool)
    src_mask = np.zeros((h, w), dtype=bool)
    src_mask[12, 12] = True
    src_mask[12, 17] = True

    # Frame without source_mask
    frame_unmasked = {
        "obs_id": "OBS_1",
        "mjd": 60000.0,
        "utc_date": "2026-01-01T00:00:00Z",
        "detector": "SPHEREx-D1",
        "collection": "spherex_dr1",
        "image": img,
        "mask": fatal_mask,
    }

    # Frame with source_mask
    frame_masked = {
        "obs_id": "OBS_2",
        "mjd": 60100.0,
        "utc_date": "2026-04-11T00:00:00Z",
        "detector": "SPHEREx-D1",
        "collection": "spherex_dr1",
        "image": img,
        "mask": fatal_mask,
        "source_mask": src_mask,
    }

    res = build_lightcurve_series([frame_unmasked, frame_masked])
    pts = res["points"]
    assert len(pts) == 2

    # Frame 2 (with source_mask) must have lower background noise and higher SNR
    assert pts[1]["snr"] > pts[0]["snr"]
    assert pts[1]["net_flux_mjy_sr"] > 0.0


def test_audit_photometry_target_wcs_failure_returns_unavailable():
    """
    Scientific Truthfulness Audit Pass 1:
    When target_coord is supplied but WCS projection fails/returns non-finite,
    compute_aperture_photometry must return unavailable/invalid measurement with a clear reason,
    NEVER silently substitute the image center or brightest peak.
    """
    # Image with bright source at image center (10, 10)
    img = np.ones((21, 21), dtype=np.float32) * 2.0
    img[10, 10] = 500.0  # Bright center source

    # Case A: target_coord supplied with no WCS
    phot_no_wcs = compute_aperture_photometry(
        image=img,
        target_coord=(120.5, 45.0),
        wcs=None,
    )
    assert phot_no_wcs["status"] == "unavailable"
    assert phot_no_wcs["valid"] is False
    assert phot_no_wcs["net_flux"] is None
    assert "could not be projected" in phot_no_wcs["reason"]

    # Case B: target_coord supplied with non-finite / failing projection
    bad_hdr = fits.Header()
    bad_hdr["CRVAL1"] = 0.0
    bad_hdr["CRVAL2"] = 0.0
    bad_hdr["CRPIX1"] = 10.0
    bad_hdr["CRPIX2"] = 10.0
    # Missing CDELT/CTYPE so world_to_pixel fails
    phot_bad_wcs = compute_aperture_photometry(
        image=img,
        target_coord=(180.0, 90.0),
        wcs=bad_hdr,
    )
    assert phot_bad_wcs["status"] == "unavailable"
    assert phot_bad_wcs["valid"] is False
    assert phot_bad_wcs["net_flux"] is None

    # Case B2: target_coord projects completely outside image bounds
    good_hdr = fits.Header()
    good_hdr["CTYPE1"] = "RA---TAN"
    good_hdr["CTYPE2"] = "DEC--TAN"
    good_hdr["CRVAL1"] = 100.0
    good_hdr["CRVAL2"] = 20.0
    good_hdr["CRPIX1"] = 10.0
    good_hdr["CRPIX2"] = 10.0
    good_hdr["CDELT1"] = -0.01
    good_hdr["CDELT2"] = 0.01
    phot_outside = compute_aperture_photometry(
        image=img,
        target_coord=(105.0, 25.0),  # Far outside 21x21 frame
        wcs=good_hdr,
    )
    assert phot_outside["status"] == "unavailable"
    assert phot_outside["valid"] is False
    assert "outside image boundaries" in phot_outside["reason"]

    # Case C: build_lightcurve_series surfaces unavailable state
    frame_fail = {
        "obs_id": "OBS_FAIL",
        "mjd": 60500.0,
        "detector": "SPHEREx-D1",
        "image": img,
        "wcs": None,
    }
    lc = build_lightcurve_series([frame_fail], target_ra=120.5, target_dec=45.0)
    assert len(lc["points"]) == 1
    pt = lc["points"][0]
    assert pt["status"] == "unavailable"
    assert pt["valid"] is False
    assert pt["net_flux_mjy_sr"] is None
    # Center bright source (500 MJy) must NOT contaminate the lightcurve mean flux
    assert lc["mean_flux_mjy_sr"] == 0.0


def test_audit_fits_processing_wavelength_and_mask_semantics():
    """
    Scientific Truthfulness Audit Pass 2:
    - extract_calibrated_wavelength returns unavailable (None) when target_coord fails projection,
      and only evaluates center when target_coord is explicitly None.
    - extract_fatal_quality_mask preserves an explicit unknown/missing quality state (None)
      when mask metadata (MSKN cards) are absent, unless allow_legacy_synthetic=True.
    """
    from app.science.fits_processing import extract_calibrated_wavelength, extract_fatal_quality_mask

    # 1. WCS-WAVE tabular HDU
    x_col = fits.Column(name="X", format="9J", dim="(9)", array=np.array([[1, 256, 511, 766, 1021, 1275, 1530, 1785, 2040]]))
    y_col = fits.Column(name="Y", format="9J", dim="(9)", array=np.array([[1, 256, 511, 766, 1021, 1275, 1530, 1785, 2040]]))
    vals = np.zeros((1, 9, 9, 2), dtype=np.float32)
    vals[0, :, :, 0] = 3.12
    vals[0, :, :, 1] = 0.02
    v_col = fits.Column(name="VALUES", format="162E", dim="(2,9,9)", array=vals)
    wave_hdu = fits.BinTableHDU.from_columns([x_col, y_col, v_col], name="WCS-WAVE")

    img_hdr = fits.Header()
    img_hdr["NAXIS1"] = 20
    img_hdr["NAXIS2"] = 20
    img_hdu = fits.ImageHDU(data=np.ones((20, 20), dtype=np.float32), header=img_hdr, name="IMAGE")
    hdul = fits.HDUList([fits.PrimaryHDU(), img_hdu, wave_hdu])

    # Target coord requested without celestial WCS projection capability -> returns None (unavailable)
    wave_target_fail = extract_calibrated_wavelength(hdul, target_coord=(100.0, 20.0))
    assert wave_target_fail is None

    # Target coord explicitly None -> measures center
    wave_center = extract_calibrated_wavelength(hdul, target_coord=None)
    assert wave_center is not None
    assert wave_center["wavelength_um"] == pytest.approx(3.12, rel=1e-3)

    # Target coord with valid celestial 3D WCS (NAXIS=3)
    img_hdr3d = fits.Header()
    img_hdr3d["NAXIS1"] = 20
    img_hdr3d["NAXIS2"] = 20
    img_hdr3d["NAXIS3"] = 1
    img_hdr3d["CTYPE1"] = "RA---TAN"
    img_hdr3d["CTYPE2"] = "DEC--TAN"
    img_hdr3d["CTYPE3"] = "WAVE"
    img_hdr3d["CRVAL1"] = 100.0
    img_hdr3d["CRVAL2"] = 20.0
    img_hdr3d["CRVAL3"] = 3.0
    img_hdr3d["CRPIX1"] = 10.0
    img_hdr3d["CRPIX2"] = 10.0
    img_hdr3d["CRPIX3"] = 1.0
    img_hdr3d["CDELT1"] = -0.01
    img_hdr3d["CDELT2"] = 0.01
    img_hdr3d["CDELT3"] = 0.1
    img_hdu3d = fits.ImageHDU(data=np.ones((20, 20), dtype=np.float32), header=img_hdr3d, name="IMAGE")
    hdul_3d = fits.HDUList([fits.PrimaryHDU(), img_hdu3d, wave_hdu])
    wave_3d = extract_calibrated_wavelength(hdul_3d, target_coord=(100.0, 20.0))
    assert wave_3d is not None
    assert wave_3d["wavelength_um"] == pytest.approx(3.12, rel=1e-3)

    # Target coord projecting outside cutout bounds returns None
    wave_out_bounds = extract_calibrated_wavelength(hdul_3d, target_coord=(120.0, 40.0))
    assert wave_out_bounds is None

    # 2. FLAGS extension with missing mask metadata
    flags_data = np.array([[1, 2], [4, 8]], dtype=np.int32)
    flags_hdr = fits.Header()  # No MSKN cards!
    flags_hdu = fits.ImageHDU(data=flags_data, header=flags_hdr, name="FLAGS")
    hdul_flags = fits.HDUList([fits.PrimaryHDU(), img_hdu, flags_hdu])

    # Default call must preserve explicit unknown/missing quality state (None)
    mask_default = extract_fatal_quality_mask(hdul_flags)
    assert mask_default is None

    # evaluate_quality_flags must also preserve explicit unknown/missing quality state
    eval_default = evaluate_quality_flags(hdul_flags)
    assert eval_default["quality_state"] == "unknown_metadata_missing"
    assert eval_default["flagged_pixels"] == 0

    # Fixture-only explicit call allows legacy synthetic bits
    mask_synthetic = extract_fatal_quality_mask(hdul_flags, allow_legacy_synthetic=True)
    assert mask_synthetic is not None
    assert np.all(mask_synthetic)

    eval_synthetic = evaluate_quality_flags(hdul_flags, allow_legacy_synthetic=True)
    assert eval_synthetic["quality_state"] == "legacy_synthetic"
    assert eval_synthetic["flagged_pixels"] == 4


def test_audit_spectrum_truthfulness_and_documented_bb_fit():
    """
    Scientific Truthfulness Audit Pass:
    Remove unsupported physical claims (e.g. hardcoded 260K, 3150K temperatures or preset identity heuristics).
    Return documented single-temperature blackbody continuum fit with inputs, uncertainty, and limitations
    only when >= 3 distinct bands exist with valid propagated errors (positive residual dof >= 1).
    102 channels must be labeled as illustrative estimated continuum, never observed channels/resolution.
    """
    from app.science.spectrum import fit_blackbody_continuum, generate_spectrum_for_target

    # 1. Fit with insufficient bands (< 3)
    fit_single = fit_blackbody_continuum([
        {"detector": "SPHEREx-D1", "wavelength_um": 0.935, "flux_mjy_sr": 10.0, "flux_err_mjy_sr": 0.5}
    ])
    assert fit_single["status"] == "unavailable"
    assert fit_single["temperature_k"] is None
    assert "minimum 3 distinct bands" in fit_single["reason"]

    # 2. Fit with 2 observed bands returns unavailable (two-parameter fit requires >= 3 bands for dof >= 1)
    fit_two = fit_blackbody_continuum([
        {"detector": "SPHEREx-D1", "wavelength_um": 0.935, "flux_mjy_sr": 5.0, "flux_err_mjy_sr": 0.2},
        {"detector": "SPHEREx-D3", "wavelength_um": 2.050, "flux_mjy_sr": 15.0, "flux_err_mjy_sr": 0.5},
    ])
    assert fit_two["status"] == "unavailable"
    assert fit_two["temperature_k"] is None
    assert fit_two["degrees_of_freedom"] == 0
    assert fit_two["reduced_chi2"] is None
    assert "minimum 3 distinct bands" in fit_two["reason"]

    # 3. Fit with 3 observed distinct bands: dof = 3 - 2 = 1, reduced_chi2 is a float
    fit_three = fit_blackbody_continuum([
        {"detector": "SPHEREx-D1", "wavelength_um": 0.935, "flux_mjy_sr": 5.0, "flux_err_mjy_sr": 0.2},
        {"detector": "SPHEREx-D3", "wavelength_um": 2.050, "flux_mjy_sr": 15.0, "flux_err_mjy_sr": 0.5},
        {"detector": "SPHEREx-D6", "wavelength_um": 4.710, "flux_mjy_sr": 12.0, "flux_err_mjy_sr": 0.4},
    ])
    assert fit_three["status"] == "converged"
    assert fit_three["temperature_k"] is not None
    assert fit_three["degrees_of_freedom"] == 1
    assert fit_three["reduced_chi2"] is not None
    assert "Single-temperature Planck blackbody continuum fit" in fit_three["model"]

    # 4. Missing/None flux error returns unavailable (missing-error no-fit; 10% substitution disallowed)
    fit_none_err = fit_blackbody_continuum([
        {"detector": "SPHEREx-D1", "wavelength_um": 0.935, "flux_mjy_sr": 5.0, "flux_err_mjy_sr": None},
        {"detector": "SPHEREx-D3", "wavelength_um": 2.050, "flux_mjy_sr": 15.0, "flux_err_mjy_sr": 0.5},
        {"detector": "SPHEREx-D6", "wavelength_um": 4.710, "flux_mjy_sr": 12.0, "flux_err_mjy_sr": 0.4},
    ])
    assert fit_none_err["status"] == "unavailable"
    assert fit_none_err["temperature_k"] is None
    assert "Missing valid propagated photometric uncertainty" in fit_none_err["limitations"]

    # 5. Repeated identical wavelengths (zero baseline) return unavailable
    fit_same_wave = fit_blackbody_continuum([
        {"detector": "SPHEREx-D1", "wavelength_um": 0.935, "flux_mjy_sr": 5.0, "flux_err_mjy_sr": 0.2},
        {"detector": "SPHEREx-D1", "wavelength_um": 0.935, "flux_mjy_sr": 5.2, "flux_err_mjy_sr": 0.2},
        {"detector": "SPHEREx-D1", "wavelength_um": 0.935, "flux_mjy_sr": 5.1, "flux_err_mjy_sr": 0.2},
    ])
    assert fit_same_wave["status"] == "unavailable"
    assert fit_same_wave["temperature_k"] is None

    # 6. generate_spectrum_for_target with no observations
    spec = generate_spectrum_for_target(ra=150.0, dec=20.0, observations=[], cutout_fetcher=None)
    # When no observations, all summary metrics must be unavailable (no synthetic measured peaks!)
    assert spec["summary"]["peak_wavelength_um"] is None
    assert spec["summary"]["peak_detector"] is None
    assert spec["summary"]["peak_flux_mjy_sr"] is None
    assert spec["summary"]["peak_is_measured"] is False
    assert spec["summary"]["estimated_temperature_k"] is None
    assert spec["summary"]["integrated_flux_mjy_sr_um"] is None
    assert spec["summary"]["continuum_shape"] == "insufficient observed coverage (no observed archive bands)"
    assert "spectral_class" not in spec["summary"]
    # Channels 102 must be labeled as illustrative estimated continuum
    for ch in spec["channels_102"]:
        assert ch["is_interpolated"] is True
        assert ch["is_observed"] is False
        assert "Estimated Continuum Model (Interpolated)" in ch["model_label"]
        assert "Never Observed Resolution" in ch["model_label"]


def test_audit_spectrum_truthfulness_tightened_temperature_and_neutral_shapes():
    """
    Focused verification of the 4 truthfulness requirements:
    1. Neutral measured-shape descriptions only (no Brown Dwarf, Cool Star, or Dust Disk candidate classifications).
    2. Temperature fit unavailable with < 3 distinct bands (two-band no-fit) or missing propagated errors (missing-error no-fit).
    3. Three-band documented fit succeeds with positive residual dof (dof >= 1).
    4. Zero observations makes summary metrics unavailable without outputting synthetic peaks as measured.
    """
    from app.science.spectrum import fit_blackbody_continuum, generate_spectrum_for_target

    # Req 1: Neutral profile output for candidate-like colors
    # Rising slope (formerly "Cold Sub-stellar / Brown Dwarf")
    class MockObs:
        def __init__(self, obs_id, detector):
            self.id = obs_id
            self.detector = detector
            self.access_url = "mock://obs"

    class MockFetcher:
        def __init__(self, fluxes):
            self.fluxes = fluxes
        def get(self, url):
            return b"MOCK_FITS_BYTES"

    # Test direct fit: Two-band no-fit
    fit_2band = fit_blackbody_continuum([
        {"detector": "SPHEREx-D1", "wavelength_um": 0.935, "flux_mjy_sr": 1.0, "flux_err_mjy_sr": 0.1},
        {"detector": "SPHEREx-D6", "wavelength_um": 4.710, "flux_mjy_sr": 10.0, "flux_err_mjy_sr": 0.5},
    ])
    assert fit_2band["status"] == "unavailable"
    assert fit_2band["temperature_k"] is None
    assert fit_2band["degrees_of_freedom"] == 0

    # Test direct fit: Missing-error no-fit
    fit_no_err = fit_blackbody_continuum([
        {"detector": "SPHEREx-D1", "wavelength_um": 0.935, "flux_mjy_sr": 1.0, "flux_err_mjy_sr": 0.1},
        {"detector": "SPHEREx-D3", "wavelength_um": 2.050, "flux_mjy_sr": 3.0, "flux_err_mjy_sr": None},
        {"detector": "SPHEREx-D6", "wavelength_um": 4.710, "flux_mjy_sr": 10.0, "flux_err_mjy_sr": 0.5},
    ])
    assert fit_no_err["status"] == "unavailable"
    assert fit_no_err["temperature_k"] is None
    assert "Missing valid propagated photometric uncertainty" in fit_no_err["limitations"]

    # Test direct fit: Three-band documented fit behavior
    fit_3band = fit_blackbody_continuum([
        {"detector": "SPHEREx-D1", "wavelength_um": 0.935, "flux_mjy_sr": 10.0, "flux_err_mjy_sr": 0.3},
        {"detector": "SPHEREx-D3", "wavelength_um": 2.050, "flux_mjy_sr": 12.0, "flux_err_mjy_sr": 0.4},
        {"detector": "SPHEREx-D6", "wavelength_um": 4.710, "flux_mjy_sr": 4.0, "flux_err_mjy_sr": 0.2},
    ])
    assert fit_3band["status"] == "converged"
    assert fit_3band["temperature_k"] is not None
    assert fit_3band["uncertainty_k"] is not None
    assert fit_3band["degrees_of_freedom"] == 1
    assert fit_3band["reduced_chi2"] is not None
    assert len(fit_3band["inputs"]) == 3
    assert "not an object's known physical temperature" in fit_3band["limitations"]

    # Req 4: Report generation SED section contains neutral shape and fit limitations
    from app.science.report import generate_discovery_report
    mock_spec_converged = {
        "total_observed_bands": 3,
        "observed_channels": [
            {"detector": "SPHEREx-D1", "wavelength_um": 0.935, "flux_mjy_sr": 10.0, "flux_err_mjy_sr": 0.3, "calibration_source": "WCS-WAVE"},
            {"detector": "SPHEREx-D3", "wavelength_um": 2.050, "flux_mjy_sr": 12.0, "flux_err_mjy_sr": 0.4, "calibration_source": "WCS-WAVE"},
            {"detector": "SPHEREx-D6", "wavelength_um": 4.710, "flux_mjy_sr": 4.0, "flux_err_mjy_sr": 0.2, "calibration_source": "WCS-WAVE"},
        ],
        "temperature_fit": fit_3band,
        "summary": {
            "continuum_shape": "peak among measured detector bands (2.05 µm in SPHEREx-D3)",
            "temperature_fit": fit_3band,
        },
    }
    rep = generate_discovery_report(
        target_name="Test Source",
        ra_deg=269.452,
        dec_deg=4.693,
        spectrum_data=mock_spec_converged,
    )
    assert "Broadband Continuum Shape:" in rep["markdown_report"]
    assert "Single-Temperature Blackbody Continuum Fit:" in rep["markdown_report"]
    assert "not an object's known physical temperature" in rep["markdown_report"]
    assert "Candidate Profile" not in rep["markdown_report"]
    assert "Brown Dwarf" not in rep["markdown_report"]


def test_audit_stacking_snr_improvement_uncensored():
    """
    Scientific Truthfulness Audit Pass 4:
    Empirical snr_improvement_factor must NOT be clamped to an arbitrary interval around sqrt(N).
    The actual uncensored estimator or unavailable must be reported, with theoretical sqrt(N) separate.
    """
    # Case A: Two identical frames co-added with mean.
    # Noise does not reduce when identical frames are averaged; measured gain is 1.0!
    np.random.seed(99)
    noise = np.random.normal(0, 1.0, (30, 30)).astype(np.float32)
    stacked_ident, stats_ident = compute_coadd_stack([noise, noise.copy()], method="mean")
    assert stats_ident["snr_improvement_factor"] == pytest.approx(1.0, rel=0.05)
    assert stats_ident["snr_gain_status"] == "measured"
    assert stats_ident["theoretical_snr_gain"] == pytest.approx(1.414, rel=1e-2)
    assert stats_ident["theoretical_gain_model"] == "sqrt(N) ideal Gaussian noise reduction"

    # Case B: Two independent noise frames with an aligned source co-added with mean.
    noise1 = np.random.normal(0, 1.0, (50, 50)).astype(np.float32)
    noise2 = np.random.normal(0, 1.0, (50, 50)).astype(np.float32)
    noise1[25, 25] += 50.0
    noise2[25, 25] += 50.0
    stacked_indep, stats_indep = compute_coadd_stack([noise1, noise2], method="mean")
    assert stats_indep["snr_improvement_factor"] == pytest.approx(1.414, rel=0.10)
    assert stats_indep["theoretical_snr_gain"] == pytest.approx(1.414, rel=1e-2)


def test_audit_nan_inf_preserved_as_masks_not_fabricated():
    """
    Scientific Truthfulness Audit Pass 5:
    Preserve invalid pixels (NaN/Inf) as masks; do NOT let fabricated fill values enter
    photometry, comparisons, stacks, spectra, or motion.
    """
    from app.science.fits_processing import extract_primary_image
    from app.science.motion import _find_brightest_centroid, _find_local_centroid

    # 1. extract_primary_image preserves NaNs in preserve_nan mode
    pri = fits.PrimaryHDU()
    img_data = np.array([[1.0, np.nan], [np.inf, 4.0]], dtype=np.float32)
    img_hdu = fits.ImageHDU(data=img_data, name="IMAGE")
    hdul = fits.HDUList([pri, img_hdu])

    data_sci, _ = extract_primary_image(hdul, preserve_nan=True)
    assert np.isnan(data_sci[0, 1])
    assert np.isnan(data_sci[1, 0])  # inf converted to nan mask, not fabricated min_finite!

    # 2. Stacking preserves NaNs as masks and does not overwrite with background median
    f1 = np.ones((10, 10), dtype=np.float32) * 2.0
    f1[2, 2] = np.nan
    f2 = np.ones((10, 10), dtype=np.float32) * 2.0
    f2[2, 2] = np.nan

    stacked, stats = compute_coadd_stack([f1, f2], method="mean")
    # Pixel (2, 2) was invalid in all frames -> must remain NaN, not replaced with bg_fill!
    assert np.isnan(stacked[2, 2])

    # 3. Motion centroiding: NaNs/Infs are never selected as brightest peak
    arr_with_nan = np.ones((20, 20), dtype=np.float32) * 1.0
    arr_with_nan[10, 10] = 50.0  # Real peak
    arr_with_nan[0, 0] = np.nan
    arr_with_nan[0, 1] = np.inf

    cen = _find_brightest_centroid(arr_with_nan)
    assert cen is not None
    y_c, x_c, _ = cen
    assert abs(y_c - 10.0) < 0.5
    assert abs(x_c - 10.0) < 0.5

    # 4. Photometry: input image is not mutated
    clean_copy = f1.copy()
    phot = compute_aperture_photometry(f1, center_y=5.0, center_x=5.0)
    assert phot["valid"] is True
    # Verify original array unchanged
    assert np.isnan(f1[2, 2])


def test_audit_motion_requested_target_never_substitutes_brightest_peak():
    """
    When target_coord is requested in measure_astrometric_motion, but WCS projection
    fails or centroids cannot be tracked, motion analysis must NEVER substitute the blind
    brightest peak in the field as the target.
    """
    img1 = np.ones((30, 30), dtype=np.float32) * 1.0
    img2 = np.ones((30, 30), dtype=np.float32) * 1.0
    # Add an unrelated bright field star at (5, 5)
    img1[5, 5] = 100.0
    img2[5, 5] = 100.0

    meta1 = {"mjd": 60000.0}
    meta2 = {"mjd": 60365.0}

    # Request motion for a target without WCS
    res = measure_astrometric_motion(
        img1=img1,
        img2=img2,
        meta1=meta1,
        meta2=meta2,
        wcs1=None,
        wcs2=None,
        target_coord=(120.0, 45.0),
    )
    # Must NOT track the unrelated bright star at (5, 5)
    assert res["centroid_detected"] is False
    assert res["centroid_1"] is None
    assert res["centroid_2"] is None
    assert res["displacement_pixels"] == 0.0
    assert res["proper_motion_arcsec_yr"] == 0.0



