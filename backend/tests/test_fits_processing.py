import pytest
import io
import numpy as np
from astropy.io import fits
from app.science.fits_processing import (
    load_fits_cutout,
    extract_primary_image,
    extract_wcs_info,
    evaluate_quality_flags,
    calculate_pixel_stats,
    apply_asinh_stretch,
    apply_zscale_stretch,
    render_image_to_base64,
    render_image_to_base64_png,
    extract_astropy_wcs,
)

@pytest.fixture
def sample_fits_bytes():
    # Construct a synthetic multi-extension FITS matching SPHEREx structure
    pri = fits.PrimaryHDU()
    pri.header["TELESCOP"] = "SPHEREx"
    pri.header["INSTRUME"] = "SPHEREx"

    # Image HDU
    img_data = np.array([
        [1.0, 2.5, 3.0],
        [4.2, np.nan, 8.1],
        [10.5, 12.0, 15.0]
    ], dtype=np.float32)
    img_hdu = fits.ImageHDU(data=img_data, name="IMAGE")
    img_hdu.header["BUNIT"] = "MJy/sr"
    img_hdu.header["CRVAL1"] = 127.6944
    img_hdu.header["CRVAL2"] = -39.1776
    img_hdu.header["CDELT1"] = -0.0017
    img_hdu.header["CDELT2"] = 0.0017

    # Flags HDU
    flag_data = np.array([
        [0, 0, 0],
        [0, 2, 0],  # Cosmic ray flag bit 1 (val 2)
        [0, 0, 4]   # Saturated flag bit 2 (val 4)
    ], dtype=np.int32)
    flags_hdu = fits.ImageHDU(data=flag_data, name="FLAGS")

    hdul = fits.HDUList([pri, img_hdu, flags_hdu])
    buf = io.BytesIO()
    hdul.writeto(buf)
    return buf.getvalue()

def test_load_and_extract_image(sample_fits_bytes):
    hdul = load_fits_cutout(sample_fits_bytes)
    assert len(hdul) == 3
    # Default scientific extraction preserves NaN as mask
    data, header = extract_primary_image(hdul)
    assert data.shape == (3, 3)
    assert np.isnan(data).any()
    assert header["BUNIT"] == "MJy/sr"

    # Explicit preserve_nan=False sanitizes for legacy display compatibility
    data_sanitized, _ = extract_primary_image(hdul, preserve_nan=False)
    assert not np.isnan(data_sanitized).any()

def test_extract_wcs(sample_fits_bytes):
    hdul = load_fits_cutout(sample_fits_bytes)
    _, header = extract_primary_image(hdul)
    wcs_info = extract_wcs_info(header)
    assert pytest.approx(wcs_info["crval1"], 0.001) == 127.6944
    assert pytest.approx(wcs_info["crval2"], 0.001) == -39.1776

def test_evaluate_quality_flags(sample_fits_bytes):
    hdul = load_fits_cutout(sample_fits_bytes)
    # Default call without mask metadata preserves explicit unknown/missing state
    default_summary = evaluate_quality_flags(hdul)
    assert default_summary["quality_state"] == "unknown_metadata_missing"
    assert default_summary["flagged_pixels"] == 0

    # Explicit fixture/test call allows legacy synthetic bits
    flag_summary = evaluate_quality_flags(hdul, allow_legacy_synthetic=True)
    assert flag_summary["quality_state"] == "legacy_synthetic"
    assert flag_summary["total_pixels"] == 9
    assert flag_summary["flagged_pixels"] == 2
    assert flag_summary["flag_breakdown"]["cosmic_ray"] == 1
    assert flag_summary["flag_breakdown"]["saturated"] == 1

def test_calculate_pixel_stats():
    arr = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)
    stats = calculate_pixel_stats(arr)
    assert stats["min_mjy_sr"] == 10.0
    assert stats["max_mjy_sr"] == 40.0
    assert stats["mean_mjy_sr"] == 25.0
    assert stats["median_mjy_sr"] == 25.0

def test_asinh_and_zscale_stretch():
    arr = np.linspace(0.1, 50.0, 100).reshape((10, 10)).astype(np.float32)
    asinh_u8 = apply_asinh_stretch(arr)
    assert asinh_u8.dtype == np.uint8
    assert asinh_u8.shape == (10, 10)
    assert asinh_u8.max() <= 255
    assert asinh_u8.min() >= 0

    zscale_u8 = apply_zscale_stretch(arr)
    assert zscale_u8.dtype == np.uint8
    assert zscale_u8.max() <= 255

def test_render_image_to_base64_png():
    u8_arr = np.zeros((16, 16), dtype=np.uint8)
    u8_arr[8, 8] = 255
    b64_str = render_image_to_base64_png(u8_arr)
    assert b64_str.startswith("data:image/png;base64,")
    
    # Inferno colormap
    inferno_b64 = render_image_to_base64_png(u8_arr, colormap="inferno")
    assert inferno_b64.startswith("data:image/png;base64,")

def test_render_image_to_base64_webp():
    u8_arr = np.linspace(0, 255, 256, dtype=np.uint8).reshape((16, 16))
    webp_b64 = render_image_to_base64(u8_arr, format="webp")
    assert webp_b64.startswith("data:image/webp;base64,")

    webp_inferno = render_image_to_base64(u8_arr, colormap="inferno", format="webp")
    assert webp_inferno.startswith("data:image/webp;base64,")

def test_extract_astropy_wcs_celestial():
    header = fits.Header()
    header["NAXIS"] = 3
    header["CTYPE1"] = "RA---TAN"
    header["CTYPE2"] = "DEC--TAN"
    header["CTYPE3"] = "WAVE"
    header["CRVAL1"] = 127.6944
    header["CRVAL2"] = -39.1776
    header["CRVAL3"] = 1.5
    w = extract_astropy_wcs(header)
    assert w is not None
    assert w.naxis == 2  # Extracted 2D celestial sub-WCS

def test_render_image_to_base64_float_sanitization():
    # Test float32 input with NaN to ensure no Pillow deprecation warning or exception
    float_arr = np.array([[10.5, np.nan], [200.2, 500.0]], dtype=np.float32)
    b64 = render_image_to_base64(float_arr, format="webp")
    assert b64.startswith("data:image/webp;base64,")

def test_spherex_documented_flags_distinguish_source_mask():
    from app.science.fits_processing import extract_fatal_quality_mask, extract_variance_data
    hdr = fits.Header()
    hdr["MSKN0000"] = "TRANSIENT"
    hdr["MSKM0000"] = 1
    hdr["MSKN0001"] = "OVERFLOW"
    hdr["MSKM0001"] = 2
    hdr["MSKN0006"] = "NONFUNC"
    hdr["MSKM0006"] = 64
    hdr["MSKN0021"] = "SOURCE"
    hdr["MSKM0021"] = 2097152

    # Array with 4 pixels:
    # 0: Clean (0)
    # 1: Nominal SOURCE only (2097152) -> should NOT be flagged as bad!
    # 2: Saturated / OVERFLOW + SOURCE (2097154) -> should be flagged as bad!
    # 3: Dead pixel / NONFUNC (64) -> should be flagged as bad!
    flags_data = np.array([0, 2097152, 2097154, 64], dtype=np.int32).reshape((2, 2))
    flags_hdu = fits.ImageHDU(data=flags_data, header=hdr, name="FLAGS")
    var_data = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32).reshape((2, 2))
    var_hdu = fits.ImageHDU(data=var_data, name="VARIANCE")
    hdul = fits.HDUList([fits.PrimaryHDU(), flags_hdu, var_hdu])

    summary = evaluate_quality_flags(hdul)
    assert summary["total_pixels"] == 4
    # Only pixels 2 and 3 have fatal defects. Pixel 1 (SOURCE only) is valid!
    assert summary["flagged_pixels"] == 2
    assert summary["flag_breakdown"]["saturated"] == 1
    assert summary["flag_breakdown"]["dead_unusable"] == 1
    assert summary["flag_breakdown"]["source_detection"] == 2

    fatal_mask = extract_fatal_quality_mask(hdul)
    assert fatal_mask[0, 0] is False or fatal_mask[0, 0] == 0  # Clean
    assert fatal_mask[0, 1] is False or fatal_mask[0, 1] == 0  # SOURCE only is not fatal!
    assert fatal_mask[1, 0] == True  # Saturated + SOURCE is fatal
    assert fatal_mask[1, 1] == True  # NONFUNC is fatal

    var = extract_variance_data(hdul)
    assert var is not None
    assert var.shape == (2, 2)

def test_apply_diverging_colormap():
    from app.science.fits_processing import apply_diverging_colormap
    u8_arr = np.array([[0, 64], [128, 255]], dtype=np.uint8)
    rgb = apply_diverging_colormap(u8_arr)
    assert rgb.shape == (2, 2, 3)
    # Check blue dominance at 0 (negative residual)
    assert rgb[0, 0, 2] > rgb[0, 0, 0]  # Blue > Red
    # Check neutral near 128 (zero residual)
    assert abs(int(rgb[1, 0, 0]) - int(rgb[1, 0, 1])) < 15
    assert abs(int(rgb[1, 0, 1]) - int(rgb[1, 0, 2])) < 15
    # Check red dominance at 255 (positive residual)
    assert rgb[1, 1, 0] > rgb[1, 1, 2]  # Red > Blue

    # Test Base64 output
    b64 = render_image_to_base64(u8_arr, colormap="diverging", format="png")
    assert b64.startswith("data:image/png;base64,")


