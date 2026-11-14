import io
import base64
from typing import Dict, Any, Tuple, Optional, Union, Literal
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.visualization import ZScaleInterval
from PIL import Image

def load_fits_cutout(file_source: Union[bytes, str, io.BytesIO]) -> fits.HDUList:
    """
    Opens a FITS file or memory buffer and returns an HDUList.
    """
    if isinstance(file_source, bytes):
        return fits.HDUList.fromstring(file_source)
    elif isinstance(file_source, io.BytesIO):
        return fits.open(file_source)
    else:
        return fits.open(file_source)

# Documented SPHEREx Level 2 Mask Plane Classifications
SPHEREX_FATAL_FLAG_NAMES = {
    "TRANSIENT",
    "OVERFLOW",
    "SUR_ERROR",
    "NONFUNC",
    "MISSING_DATA",
    "HOT",
    "COLD",
    "NONLINEAR",
    "SNOWBALL",
}

SPHEREX_INFORMATIONAL_FLAG_NAMES = {
    "SOURCE",
    "FULLSAMPLE",
}

SPHEREX_ARTIFACT_FLAG_NAMES = {
    "DICHROIC",
    "PHANMISS",
    "PERSIST",
    "OUTLIER",
    "CROSSTALK",
    "GHOST",
    "GHOST_FPA",
    "GHOST_EXT",
    "STREAK",
    "BLOOM",
    "HALO",
}

def extract_primary_image(hdul: fits.HDUList) -> Tuple[np.ndarray, fits.Header]:
    """
    Extracts the calibrated IMAGE extension (surface brightness in MJy/sr).
    """
    if "IMAGE" in hdul:
        hdu = hdul["IMAGE"]
    elif len(hdul) > 1 and hdul[1].data is not None:
        hdu = hdul[1]
    elif hdul[0].data is not None:
        hdu = hdul[0]
    else:
        raise ValueError("No valid image data extension found in FITS HDUList.")

    data = hdu.data.astype(np.float32)
    # Sanitize non-finite values (NaN, Inf)
    finite_mask = np.isfinite(data)
    if not np.all(finite_mask):
        min_finite = np.min(data[finite_mask]) if np.any(finite_mask) else 0.0
        data[~finite_mask] = min_finite

    return data, hdu.header

def extract_wcs_info(header: fits.Header) -> Dict[str, Any]:
    """
    Extracts celestial WCS keywords from FITS header.
    """
    return {
        "crval1": header.get("CRVAL1"),
        "crval2": header.get("CRVAL2"),
        "crpix1": header.get("CRPIX1"),
        "crpix2": header.get("CRPIX2"),
        "cdelt1": header.get("CDELT1", header.get("CD1_1")),
        "cdelt2": header.get("CDELT2", header.get("CD2_2")),
        "ctype1": header.get("CTYPE1"),
        "ctype2": header.get("CTYPE2"),
    }

def parse_spherex_mask_planes(flags_header: Optional[fits.Header]) -> Dict[str, int]:
    """
    Parses documented SPHEREx Level 2 mask planes from FITS header cards (MSKNxxxx, MSKMxxxx).
    """
    planes: Dict[str, int] = {}
    if flags_header is None:
        return planes
    for k, v in flags_header.items():
        if k.startswith("MSKN"):
            suffix = k[4:]
            mkey = f"MSKM{suffix}"
            if mkey in flags_header:
                try:
                    planes[str(v).strip().upper()] = int(flags_header[mkey])
                except Exception:
                    pass
    return planes

def extract_fatal_quality_mask(hdul: fits.HDUList) -> Optional[np.ndarray]:
    """
    Returns a boolean 2D numpy array where True indicates a fatal defect (unusable pixel).
    Distinguishes nominal astronomical source detections from bad pixels.
    Returns None if no FLAGS extension is present.
    """
    if "FLAGS" not in hdul or hdul["FLAGS"].data is None:
        return None

    flags = hdul["FLAGS"].data.astype(np.int32)
    hdr = hdul["FLAGS"].header
    planes = parse_spherex_mask_planes(hdr)

    if planes:
        fatal_mask_val = 0
        for name in SPHEREX_FATAL_FLAG_NAMES:
            if name in planes:
                fatal_mask_val |= planes[name]
        return (flags & fatal_mask_val) != 0
    else:
        # Fallback for synthetic / mock FITS where bits 1, 2, 4, 8 are used
        legacy_fatal_bits = 1 | 2 | 4 | 8
        return (flags & legacy_fatal_bits) != 0

def extract_source_mask(hdul: fits.HDUList) -> Optional[np.ndarray]:
    """
    Returns a boolean 2D numpy array where True indicates a nominal astronomical source detection
    (e.g. SOURCE mask plane or FULLSAMPLE) rather than a fatal defect.
    Returns None if no FLAGS extension is present.
    """
    if "FLAGS" not in hdul or hdul["FLAGS"].data is None:
        return None

    flags = hdul["FLAGS"].data.astype(np.int32)
    hdr = hdul["FLAGS"].header
    planes = parse_spherex_mask_planes(hdr)

    if planes:
        source_bitmask = 0
        for name in SPHEREX_INFORMATIONAL_FLAG_NAMES:
            if name in planes:
                source_bitmask |= planes[name]
        return (flags & source_bitmask) != 0
    else:
        # Default mock: bit 32 for source detection if present
        return (flags & 32) != 0

def extract_calibrated_wavelength(
    hdul: fits.HDUList,
    target_coord: Optional[Tuple[float, float]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Extracts calibrated wavelength and bandwidth from the official SPHEREx WCS-WAVE
    tabular extension. Evaluates the 2D dispersion calibration at the target's celestial
    coordinates (or image center) on the detector focal plane.
    """
    if "WCS-WAVE" not in hdul or hdul["WCS-WAVE"].data is None:
        return None

    try:
        from scipy.interpolate import RegularGridInterpolator
        tb = hdul["WCS-WAVE"].data
        x_grid = np.asarray(tb["X"][0], dtype=np.float64)
        y_grid = np.asarray(tb["Y"][0], dtype=np.float64)
        vals = np.asarray(tb["VALUES"][0], dtype=np.float64)

        img_hdr = hdul["IMAGE"].header if "IMAGE" in hdul else hdul[1].header
        w = extract_astropy_wcs(img_hdr)

        px, py = None, None
        if target_coord is not None and w is not None:
            try:
                px, py = w.world_to_pixel_values(target_coord[0], target_coord[1])
            except Exception:
                pass

        if px is None or not np.isfinite(px) or py is None or not np.isfinite(py):
            naxis1 = img_hdr.get("NAXIS1", 12)
            naxis2 = img_hdr.get("NAXIS2", 12)
            px = (naxis1 - 1.0) / 2.0
            py = (naxis2 - 1.0) / 2.0

        crpix1w = float(img_hdr.get("CRPIX1W", 0.0))
        crpix2w = float(img_hdr.get("CRPIX2W", 0.0))
        crval1w = float(img_hdr.get("CRVAL1W", 1.0))
        crval2w = float(img_hdr.get("CRVAL2W", 1.0))

        full_x = (float(px) + 1.0 - crpix1w) + crval1w - 1.0
        full_y = (float(py) + 1.0 - crpix2w) + crval2w - 1.0

        interp_wave = RegularGridInterpolator((y_grid, x_grid), vals[:, :, 0], bounds_error=False, fill_value=None)
        interp_dwave = RegularGridInterpolator((y_grid, x_grid), vals[:, :, 1], bounds_error=False, fill_value=None)

        wave = float(interp_wave([[full_y, full_x]])[0])
        dwave = float(interp_dwave([[full_y, full_x]])[0])

        return {
            "wavelength_um": round(wave, 4),
            "bandwidth_um": round(dwave, 4),
            "calibration_method": "WCS-WAVE",
            "full_detector_x": round(float(full_x), 1),
            "full_detector_y": round(float(full_y), 1),
        }
    except Exception:
        return None

def extract_variance_data(hdul: fits.HDUList) -> Optional[np.ndarray]:
    """
    Extracts the error variance array from the VARIANCE extension if present.
    """
    if "VARIANCE" in hdul and hdul["VARIANCE"].data is not None:
        var = hdul["VARIANCE"].data.astype(np.float32)
        # Sanitize non-finite variance values
        var = np.where(np.isfinite(var) & (var >= 0), var, np.nan)
        return var
    return None

def evaluate_quality_flags(hdul: fits.HDUList) -> Dict[str, Any]:
    """
    Evaluates per-pixel data quality flags from the FLAGS extension.
    Distinguishes nominal astronomical source detections (SOURCE mask) from fatal defect flags.
    """
    if "FLAGS" not in hdul or hdul["FLAGS"].data is None:
        return {"flagged_pixels": 0, "total_pixels": 0, "flag_breakdown": {}}

    flags = hdul["FLAGS"].data.astype(np.int32)
    total_pixels = int(flags.size)
    hdr = hdul["FLAGS"].header
    planes = parse_spherex_mask_planes(hdr)

    if planes:
        # SPHEREx Level 2 FITS with documented mask metadata
        fatal_bitmask = 0
        for name in SPHEREX_FATAL_FLAG_NAMES:
            if name in planes:
                fatal_bitmask |= planes[name]

        fatal_mask = (flags & fatal_bitmask) != 0
        flagged_count = int(np.count_nonzero(fatal_mask))

        breakdown = {
            "dead_unusable": int(np.count_nonzero(flags & planes.get("NONFUNC", 64))),
            "saturated": int(np.count_nonzero(flags & planes.get("OVERFLOW", 2))),
            "cosmic_ray": int(np.count_nonzero(flags & (planes.get("SNOWBALL", 134217728) | planes.get("TRANSIENT", 1)))),
            "non_linear": int(np.count_nonzero(flags & planes.get("NONLINEAR", 32768))),
            "sur_error": int(np.count_nonzero(flags & planes.get("SUR_ERROR", 4))),
            "hot_pixel": int(np.count_nonzero(flags & planes.get("HOT", 1024))),
            "cold_pixel": int(np.count_nonzero(flags & planes.get("COLD", 2048))),
            "source_detection": int(np.count_nonzero(flags & planes.get("SOURCE", 2097152))),
            "stray_light_glint": int(np.count_nonzero(flags & (planes.get("GHOST", 4194304) | planes.get("BLOOM", 67108864) | planes.get("HALO", 268435456)))),
        }
    else:
        # Synthetic / mock FITS without header MSKN cards
        flagged_mask = (flags & (1 | 2 | 4 | 8 | 16)) != 0
        flagged_count = int(np.count_nonzero(flagged_mask))
        breakdown = {
            "dead_unusable": int(np.count_nonzero(flags & 1)),
            "cosmic_ray": int(np.count_nonzero(flags & 2)),
            "saturated": int(np.count_nonzero(flags & 4)),
            "non_linear": int(np.count_nonzero(flags & 8)),
            "stray_light_glint": int(np.count_nonzero(flags & 16)),
        }

    return {
        "flagged_pixels": flagged_count,
        "total_pixels": total_pixels,
        "flag_breakdown": breakdown,
    }

def calculate_pixel_stats(data: np.ndarray) -> Dict[str, float]:
    """
    Calculates scientific statistics on raw unscaled pixel values (MJy/sr).
    """
    finite_data = data[np.isfinite(data)]
    if len(finite_data) == 0:
        return {
            "min_mjy_sr": 0.0,
            "max_mjy_sr": 0.0,
            "mean_mjy_sr": 0.0,
            "std_mjy_sr": 0.0,
            "median_mjy_sr": 0.0,
        }

    return {
        "min_mjy_sr": round(float(np.min(finite_data)), 4),
        "max_mjy_sr": round(float(np.max(finite_data)), 4),
        "mean_mjy_sr": round(float(np.mean(finite_data)), 4),
        "std_mjy_sr": round(float(np.std(finite_data)), 4),
        "median_mjy_sr": round(float(np.median(finite_data)), 4),
    }

def apply_asinh_stretch(
    image: np.ndarray,
    non_linear_factor: float = 0.1,
    lower_pct: float = 0.5,
    upper_pct: float = 99.5,
) -> np.ndarray:
    """
    Applies display-only arcsinh stretch for optimal astronomical contrast.
    Does not modify underlying scientific measurements.
    """
    vmin = np.percentile(image, lower_pct)
    vmax = np.percentile(image, upper_pct)
    if vmax <= vmin:
        vmax = vmin + 1e-5

    norm = np.clip((image - vmin) / (vmax - vmin), 0.0, None)
    factor = max(non_linear_factor, 1e-4)
    stretched = np.arcsinh(norm / factor) / np.arcsinh(1.0 / factor)
    stretched = np.clip(stretched, 0.0, 1.0)
    return (stretched * 255.0).astype(np.uint8)

def apply_zscale_stretch(image: np.ndarray) -> np.ndarray:
    """
    Applies standard IRAF/Astropy ZScale contrast stretch.
    """
    zscale = ZScaleInterval()
    try:
        vmin, vmax = zscale.get_limits(image)
    except Exception:
        vmin, vmax = np.percentile(image, 1.0), np.percentile(image, 99.0)

    if vmax <= vmin:
        vmax = vmin + 1e-5

    norm = np.clip((image - vmin) / (vmax - vmin), 0.0, 1.0)
    return (norm * 255.0).astype(np.uint8)

def apply_stretch(image: np.ndarray, method: str = "asinh") -> np.ndarray:
    """
    Dispatches to requested stretch method.
    """
    if method == "zscale":
        return apply_zscale_stretch(image)
    elif method == "linear":
        vmin = np.percentile(image, 1.0)
        vmax = np.percentile(image, 99.0)
        if vmax <= vmin: vmax = vmin + 1e-5
        norm = np.clip((image - vmin) / (vmax - vmin), 0.0, 1.0)
        return (norm * 255.0).astype(np.uint8)
    else:
        # Default asinh
        return apply_asinh_stretch(image)

def apply_inferno_colormap(grayscale_u8: np.ndarray) -> np.ndarray:
    """
    Fast, dependency-free colormap (Inferno-like black->purple->orange->yellow).
    """
    # 256 RGB values
    x = np.linspace(0, 1, 256)
    r = np.clip(1.5 * x**0.8 - 0.1, 0, 1)
    g = np.clip(x**1.8 * 1.2 - 0.05, 0, 1)
    b = np.clip(np.sin(x * np.pi * 0.9) * 0.8 + 0.2 * (x > 0.8), 0, 1)
    palette = np.stack([r * 255, g * 255, b * 255], axis=-1).astype(np.uint8)
    return palette[grayscale_u8]

def apply_diverging_colormap(grayscale_u8: np.ndarray) -> np.ndarray:
    """
    Perceptually balanced diverging colormap (Cool-Warm: Blue -> Light Neutral -> Crimson Red)
    centered exactly at 128 (zero net flux residual).
    Complies with NASA Data Visualization guidelines for differential / residual imagery.
    """
    # 256 RGB values
    x = np.linspace(-1.0, 1.0, 256)
    r = np.zeros(256, dtype=np.float32)
    g = np.zeros(256, dtype=np.float32)
    b = np.zeros(256, dtype=np.float32)

    # Negative side (indices 0..127): Blue to light neutral
    neg_mask = x < 0
    t_neg = x[neg_mask] + 1.0  # 0.0 at x=-1 (idx 0), approaching 1.0
    r[neg_mask] = 0.08 + 0.85 * (t_neg ** 1.3)
    g[neg_mask] = 0.28 + 0.66 * (t_neg ** 1.1)
    b[neg_mask] = 0.75 + 0.22 * (t_neg ** 0.8)

    # Positive side (indices 128..255): light neutral to Crimson Red
    pos_mask = x >= 0
    t_pos = x[pos_mask]        # 0.0 at idx 128, 1.0 at idx 255
    r[pos_mask] = 0.94 - 0.12 * (t_pos ** 2.0)
    g[pos_mask] = 0.94 - 0.84 * (t_pos ** 1.1)
    b[pos_mask] = 0.97 - 0.84 * (t_pos ** 1.1)

    palette = np.stack([
        np.clip(r * 255, 0, 255),
        np.clip(g * 255, 0, 255),
        np.clip(b * 255, 0, 255),
    ], axis=-1).astype(np.uint8)
    return palette[grayscale_u8]

def extract_astropy_wcs(header: fits.Header) -> Optional[WCS]:
    """
    Constructs an Astropy WCS instance from FITS header if celestial keywords are present.
    Extracts 2D celestial sub-WCS if the header contains extra axes (e.g. NAXIS=3).
    """
    try:
        w = WCS(header)
        if hasattr(w, "has_celestial") and w.has_celestial and w.naxis > 2:
            return w.celestial
        return w
    except Exception:
        return None

def render_image_to_base64(
    uint8_image: np.ndarray,
    colormap: Optional[str] = None,
    format: Literal["png", "webp"] = "png",
) -> str:
    """
    Encodes uint8 2D array to Base64 data URI string (PNG or WebP).
    WebP provides smaller payload sizes for rapid multi-epoch timeline playback.
    """
    # Ensure uint8 array and flip vertically to match astronomical convention (North up, standard image coords)
    if uint8_image.dtype != np.uint8:
        uint8_image = np.clip(np.nan_to_num(uint8_image, nan=0.0), 0, 255).astype(np.uint8)
    flipped = np.flipud(uint8_image)
    
    if colormap == "inferno":
        rgb = apply_inferno_colormap(flipped)
        pil_img = Image.fromarray(rgb, mode="RGB")
    elif colormap in ("diverging", "coolwarm"):
        rgb = apply_diverging_colormap(flipped)
        pil_img = Image.fromarray(rgb, mode="RGB")
    else:
        pil_img = Image.fromarray(flipped, mode="L")

    buffer = io.BytesIO()
    fmt_str = (format or "png").lower()
    if fmt_str == "webp":
        pil_img.save(buffer, format="WEBP", quality=90)
        mime = "image/webp"
    else:
        pil_img.save(buffer, format="PNG")
        mime = "image/png"

    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:{mime};base64,{b64_str}"

def render_image_to_base64_png(
    uint8_image: np.ndarray,
    colormap: Optional[str] = None
) -> str:
    """
    Backwards-compatible wrapper for PNG rendering.
    """
    return render_image_to_base64(uint8_image, colormap=colormap, format="png")
