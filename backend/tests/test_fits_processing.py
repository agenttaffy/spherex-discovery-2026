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
    data, header = extract_primary_image(hdul)
    assert data.shape == (3, 3)
    # NaN should be sanitized
    assert not np.isnan(data).any()
    assert header["BUNIT"] == "MJy/sr"

def test_extract_wcs(sample_fits_bytes):
    hdul = load_fits_cutout(sample_fits_bytes)
    _, header = extract_primary_image(hdul)
    wcs_info = extract_wcs_info(header)
    assert pytest.approx(wcs_info["crval1"], 0.001) == 127.6944
    assert pytest.approx(wcs_info["crval2"], 0.001) == -39.1776

def test_evaluate_quality_flags(sample_fits_bytes):
    hdul = load_fits_cutout(sample_fits_bytes)
    flag_summary = evaluate_quality_flags(hdul)
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

