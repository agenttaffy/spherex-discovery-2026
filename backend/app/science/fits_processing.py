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

def evaluate_quality_flags(hdul: fits.HDUList) -> Dict[str, Any]:
    """
    Evaluates per-pixel data quality flags from the FLAGS extension.
    """
    if "FLAGS" not in hdul or hdul["FLAGS"].data is None:
        return {"flagged_pixels": 0, "total_pixels": 0, "flag_breakdown": {}}

    flags = hdul["FLAGS"].data.astype(np.int32)
    total_pixels = int(flags.size)
    flagged_mask = flags != 0
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
