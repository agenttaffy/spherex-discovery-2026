import io
import asyncio
import logging
import ssl
import certifi
import httpx
from typing import Optional, Dict, Any, Tuple
import numpy as np
from app.config import FIXTURES_DIR, DEMO_CACHE_ONLY
from app.services.cloud_cutout import cloud_cutout, cloud_url_from_irsa, expected_image_identity
from app.services.cache_service import cache_service
from app.services.irsa_client import OBSERVATION_REGISTRY
from app.science.target_astrometry import frame_predictions
from app.science.photometry_evidence import inspect_photometry
from app.science.fits_processing import (
    load_fits_cutout,
    extract_primary_image,
    extract_astropy_wcs,
    extract_wcs_info,
    cutout_footprint,
    evaluate_quality_flags,
    calculate_pixel_stats,
    apply_stretch,
    render_image_to_base64,
    render_image_to_base64_png,
)
from app.models.schemas import FrameResponse, PixelStats, FlagSummary, WCSInfo

logger = logging.getLogger(__name__)

def cutout_cache_key(base_access_url: str, ra: float, dec: float, fov_deg: float) -> str:
    # Older cache keys could contain a demo cutout copied under a different request.
    return f"cutout-v2:{base_access_url}?center={ra:.6f},{dec:.6f}&size={fov_deg:.4f}"


def validate_cutout_bytes(data: bytes, base_access_url: str) -> None:
    """Reject error pages, incomplete FITS, and mismatched observations before caching."""
    from astropy.io import fits
    if not data or len(data) % 2880:
        raise ValueError("Archive response is not a complete FITS file")
    try:
        with fits.open(io.BytesIO(data), memmap=False, lazy_load_hdus=False) as hdul:
            hdul.verify("exception")
            if any(name not in hdul for name in ("IMAGE", "FLAGS", "VARIANCE")):
                raise ValueError("Required image, quality or variance plane is absent")
            image = hdul["IMAGE"].data
            flags = hdul["FLAGS"].data
            variance = hdul["VARIANCE"].data
            if (image is None or image.ndim != 2 or image.size == 0 or flags is None or variance is None
                    or flags.shape != image.shape or variance.shape != image.shape
                    or not np.issubdtype(flags.dtype, np.integer)):
                raise ValueError("Image, quality and variance planes are invalid or have different shapes")
            expected = expected_image_identity(base_access_url)
            if expected:
                header = hdul["IMAGE"].header
                actual = (str(header.get("OBSID", "")).strip(), str(header.get("DETECTOR", "")).strip())
                if actual != expected:
                    raise ValueError("FITS observation identity does not match the requested image")
    except Exception as exc:
        raise ValueError(f"Archive response is not a valid SPHEREx FITS cutout: {exc}") from exc

class CutoutService:
    async def fetch_cutout_fits(
        self,
        base_access_url: str,
        ra: float,
        dec: float,
        fov_deg: float = 0.05
    ) -> bytes:
        data, _ = await self.fetch_cutout_with_source(base_access_url, ra, dec, fov_deg)
        return data

    async def fetch_cutout_with_source(
        self, base_access_url: str, ra: float, dec: float, fov_deg: float = 0.05
    ) -> Tuple[bytes, str]:
        """
        Fetches FITS cutout from local cache or NASA IRSA IBE service.
        Checks exact cutout URL hash, demo manifest cache mappings, and live IRSA endpoints.
        """
        cutout_url = f"{base_access_url}?center={ra:.6f},{dec:.6f}&size={fov_deg:.4f}"

        # 1. Check exact key in cache
        cache_key = cutout_cache_key(base_access_url, ra, dec, fov_deg)
        cached = cache_service.get(cache_key)
        if cached:
            try:
                validate_cutout_bytes(cached, base_access_url)
                return cached, "cached_archive_cutout"
            except ValueError:
                logger.warning("Ignoring an invalid cached IRSA cutout")

        # The public cloud copy is a full image, so read only bounded byte
        # ranges and construct a native-pixel MEF cutout locally. Keep its
        # cache key distinct so the provenance remains honest on later reads.
        cloud_key = f"cloud-{cache_key}"
        cached_cloud = cache_service.get(cloud_key)
        if cached_cloud:
            try:
                validate_cutout_bytes(cached_cloud, base_access_url)
                return cached_cloud, "cached_cloud_cutout"
            except ValueError:
                logger.warning("Ignoring an invalid cached cloud cutout")
        if DEMO_CACHE_ONLY:
            raise ValueError("This cutout is not available in the local demo cache.")
        if not DEMO_CACHE_ONLY and cloud_url_from_irsa(base_access_url):
            try:
                cloud_data = await asyncio.to_thread(cloud_cutout, base_access_url, ra, dec, fov_deg)
                validate_cutout_bytes(cloud_data, base_access_url)
                cache_service.set(cloud_key, cloud_data)
                return cloud_data, "live_cloud_cutout"
            except Exception as exc:
                # Cloud access, image geometry or range integrity can fail.
                # The original IRSA service remains an independent fallback.
                logger.warning("Public cloud cutout unavailable; trying IRSA cutout service: %s", exc)

        # 3. Fetch live from NASA IRSA IBE
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        async with httpx.AsyncClient(verify=ssl_ctx, timeout=30.0) as client:
            for attempt in range(2):
                try:
                    resp = await client.get(cutout_url, headers={"User-Agent": "SPHEREx-Discovery/1.0"})
                    if resp.status_code not in (429, 502, 503, 504) or attempt == 1:
                        break
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt == 1:
                        raise
                await asyncio.sleep(0.5)
            if resp.status_code != 200:
                raise ValueError(f"IRSA IBE cutout returned status {resp.status_code}: {resp.text[:120]}")

            fits_bytes = resp.content
            validate_cutout_bytes(fits_bytes, base_access_url)
            # Never cache a transient HTTP 200 maintenance/error page.
            cache_service.set(cache_key, fits_bytes)
            return fits_bytes, "live_archive_cutout"

    def generate_synthetic_fixture(self, obs_id: str, detector: str) -> bytes:
        """
        Generates an explicitly labeled synthetic fallback FITS fixture
        in the rare event of archive downtime.
        """
        from astropy.io import fits
        pri_hdu = fits.PrimaryHDU()
        pri_hdu.header["TELESCOP"] = "SPHEREx-SIMULATED"
        pri_hdu.header["COMMENT"] = "SIMULATED TEST FIXTURE - NOT REAL OBSERVATION"
        
        # Synthetic Gaussian point source on background
        np.random.seed(abs(hash(obs_id)) % 2**32)
        y, x = np.mgrid[-10:10, -10:10]
        # Simulate slight motion per obs_id
        shift = (hash(obs_id) % 5) * 0.5
        star = 15.0 * np.exp(-((x - shift)**2 + y**2) / (2.0 * 1.5**2))
        noise = np.random.normal(1.2, 0.15, (20, 20)).astype(np.float32)
        img_data = (star + noise).astype(np.float32)
        
        img_hdu = fits.ImageHDU(data=img_data, name="IMAGE")
        img_hdu.header["BUNIT"] = "MJy/sr"
        img_hdu.header["CRVAL1"] = 133.795
        img_hdu.header["CRVAL2"] = -7.245
        
        flags_data = np.zeros((20, 20), dtype=np.int32)
        flags_hdu = fits.ImageHDU(data=flags_data, name="FLAGS")
        
        hdul = fits.HDUList([pri_hdu, img_hdu, flags_hdu])
        buf = io.BytesIO()
        hdul.writeto(buf)
        return buf.getvalue()

    async def get_frame(
        self,
        frame_id: str,
        stretch: str = "asinh",
        fov_deg: float = 0.05,
        format: str = "png",
    ) -> FrameResponse:
        """
        Retrieves observation by frame_id, downloads or loads cutout,
        processes extensions, and returns FrameResponse.
        """
        is_synthetic = False
        image_provenance = "unknown"

        # Look up metadata in active registry
        meta = OBSERVATION_REGISTRY.get(frame_id)
        if not meta:
            # Check if it matches a fixture in fixtures dir
            fixture_path = FIXTURES_DIR / f"{frame_id}.fits"
            if fixture_path.exists():
                fits_bytes = fixture_path.read_bytes()
                obs_id = frame_id
                collection = "spherex_dr1"
                detector = "SPHEREx-D1"
                utc_date = "2025-05-01T00:00:00"
                access_url = "local://fixtures"
                image_provenance = "local_fixture"
            else:
                raise KeyError(f"Frame ID '{frame_id}' not found in active observations registry.")
        else:
            obs_id = meta["obs_id"]
            collection = meta["collection"]
            detector = meta["detector"]
            utc_date = meta["utc_date"]
            access_url = meta["access_url"]
            ra = meta["ra"]
            dec = meta["dec"]

            # Check if exact cached cutout URL is recorded in metadata
            cached_url = meta.get("cached_cutout_url")
            fits_bytes = None
            if checksum := meta.get("cached_cutout_sha256"):
                fits_bytes = cache_service.get_verified(cached_url, checksum)
                if fits_bytes is None:
                    raise ValueError("Verified demo FITS cutout is missing or fails its checksum")
                image_provenance = "cached_demo_cutout"
            elif cached_url:
                fits_bytes = cache_service.get(cached_url)
                if fits_bytes:
                    image_provenance = "cached_demo_cutout"

            if not fits_bytes:
                try:
                    fits_bytes, image_provenance = await self.fetch_cutout_with_source(access_url, ra, dec, fov_deg=fov_deg)
                except Exception as e:
                    raise ValueError("IRSA could not deliver this observation's image. Try another observation or retry later.") from e

        # Parse FITS
        hdul = load_fits_cutout(fits_bytes)
        img_array, header = extract_primary_image(hdul, preserve_nan=True)
        wcs_dict = extract_wcs_info(header)
        flags_dict = evaluate_quality_flags(hdul)
        stats_dict = calculate_pixel_stats(img_array)

        # Apply visual contrast stretch
        stretched_u8 = apply_stretch(img_array, method=stretch)
        
        # Render image previews
        gray_b64 = render_image_to_base64(stretched_u8, format=format)
        inferno_b64 = render_image_to_base64(stretched_u8, colormap="inferno", format=format)

        predictions = frame_predictions(header, extract_astropy_wcs(header), img_array.shape) \
            if not is_synthetic and image_provenance != "local_fixture" else {}
        return FrameResponse(
            frame_id=frame_id,
            obs_id=obs_id,
            collection=collection,
            detector=detector,
            utc_date=utc_date,
            dimensions=list(img_array.shape),
            pixel_stats=PixelStats(**stats_dict),
            flag_summary=FlagSummary(**flags_dict),
            wcs=WCSInfo(**wcs_dict),
            footprint_icrs_deg=cutout_footprint(header, img_array.shape) if not is_synthetic else None,
            image_base64=gray_b64,
            colormapped_base64=inferno_b64,
            provenance_url=access_url if not is_synthetic else f"simulated://synthetic_fixture/{obs_id}",
            is_synthetic=is_synthetic,
            image_provenance=image_provenance,
            target_predictions=predictions,
            target_photometry={key: inspect_photometry(hdul, prediction)
                               for key, prediction in predictions.items()},
        )

cutout_service = CutoutService()
