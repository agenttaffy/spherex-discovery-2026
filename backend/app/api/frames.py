import asyncio
import logging
from typing import Optional, Literal, List

import httpx
import numpy as np
from astropy.coordinates import angular_separation
from astropy.wcs import NoConvergence, WcsError
from fastapi import APIRouter, Query, HTTPException, Body
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.config import MAX_FOV_DEG
from app.models.schemas import FrameResponse
from app.services.cache_service import cache_service
from app.services.cutout_service import cutout_service, cutout_cache_key, validate_cutout_bytes
from app.services.irsa_client import OBSERVATION_REGISTRY
from app.services.spectral_calibration_service import load_calibrated_exposure, load_cached_calibrated_exposure
from app.science.calibrated_comparison import compare_calibrated_pair, coadd_calibrated_exposures
from app.science.fits_processing import (
    load_fits_cutout,
    extract_primary_image,
    render_image_to_base64,
    apply_stretch,
)

router = APIRouter()
logger = logging.getLogger(__name__)
MINIMUM_PASSBAND_OVERLAP = 0.9

class DiffRequest(BaseModel):
    frame_id_1: str
    frame_id_2: str
    fov: float = Field(default=0.04, gt=0, le=MAX_FOV_DEG)
    format: Optional[str] = "png"

class StackRequest(BaseModel):
    frame_ids: List[str]
    method: Optional[Literal["mean", "median", "sum"]] = "mean"
    fov: float = Field(default=0.04, gt=0, le=MAX_FOV_DEG)
    format: Optional[str] = "png"
    stretch: Optional[str] = "asinh"


class CompatiblePartnersRequest(BaseModel):
    frame_id: str
    candidate_ids: List[str] = Field(max_length=12)
    fov: float = Field(default=0.04, gt=0, le=MAX_FOV_DEG)


class CatalogProjectionRequest(BaseModel):
    frame_id: str
    fov: float = 0.05
    coordinates: List[List[float]]
    proper_motions: Optional[List[Optional[List[Optional[float]]]]] = None


@router.post("/frames/project-catalog")
async def project_catalog(req: CatalogProjectionRequest):
    """Project ICRS catalog positions through the displayed cutout's celestial WCS."""
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    from astropy.wcs.utils import wcs_to_celestial_frame
    from app.science.fits_processing import extract_astropy_wcs

    if req.fov <= 0 or req.fov > 2 or len(req.coordinates) > 500:
        raise HTTPException(status_code=400, detail="Invalid field of view or too many coordinates.")
    meta = OBSERVATION_REGISTRY.get(req.frame_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Observation not found.")
    if any(len(p) != 2 or not np.isfinite(p).all() or not -90 <= p[1] <= 90 for p in req.coordinates):
        raise HTTPException(status_code=400, detail="Invalid ICRS coordinate.")
    if req.proper_motions is not None and (len(req.proper_motions) != len(req.coordinates) or any(
        motion is not None and len(motion) != 2 for motion in req.proper_motions
    )):
        raise HTTPException(status_code=400, detail="Proper motions must correspond to the catalog coordinates.")
    try:
        data = await _comparison_cutout(meta, req.fov)
        image, header = extract_primary_image(load_fits_cutout(data), preserve_nan=True)
        wcs = extract_astropy_wcs(header)
        if wcs is None or not wcs.has_celestial:
            raise ValueError("Celestial WCS is unavailable")
        if not req.coordinates:
            return {"positions": []}
        from app.science.gaia_motion import propagate_gaia_positions
        try:
            start, end = float(header["MJD-BEG"]), float(header["MJD-END"])
            exposure_mjd = (start + end) / 2 if np.isfinite([start, end]).all() and start < end else None
        except (KeyError, TypeError, ValueError):
            exposure_mjd = None
        coords, propagated = propagate_gaia_positions(req.coordinates, req.proper_motions, exposure_mjd)
        sky = SkyCoord(ra=coords[:, 0] * u.deg, dec=coords[:, 1] * u.deg, frame="icrs")
        celestial = wcs.celestial
        native = sky.transform_to(wcs_to_celestial_frame(celestial))
        positions = []
        for lon, lat, shifted in zip(native.spherical.lon.deg, native.spherical.lat.deg, propagated):
            try:
                px, py = celestial.all_world2pix([[lon, lat]], 0, quiet=False)[0]
                if np.isfinite(px) and np.isfinite(py) and -0.5 <= px < image.shape[1] - 0.5 and -0.5 <= py < image.shape[0] - 0.5:
                    positions.append({"x": float(px), "y": float(py), "motion_applied": bool(shifted)})
                else:
                    positions.append(None)
            except Exception:
                # A failed inverse WCS must never be presented as a matched source.
                positions.append(None)
        return {"positions": positions, "exposure_mjd": exposure_mjd}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Catalog projection unavailable: {exc}") from exc

@router.get("/frames/{frame_id}", response_model=FrameResponse)
async def get_frame(
    frame_id: str,
    stretch: str = Query("asinh", description="Contrast stretch (asinh, zscale, linear)"),
    fov: float = Query(0.05, description="Cutout size in degrees"),
    format: str = Query("png", description="Image output format: png or webp"),
):
    """
    Fetches and renders a SPHEREx observation cutout frame with scientific metadata.
    Supports PNG and WebP output formats.
    """
    try:
        frame = await cutout_service.get_frame(
            frame_id=frame_id,
            stretch=stretch,
            fov_deg=fov,
            format=format,
        )
        return frame
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering frame: {str(e)}")

async def _comparison_cutout(meta: dict, fov: float) -> bytes:
    if checksum := meta.get("cached_cutout_sha256"):
        data = cache_service.get_verified(meta["cached_cutout_url"], checksum)
        if data is None:
            raise ValueError("A verified demo FITS cutout is missing or fails its checksum")
        return data
    cached = cache_service.get(meta["cached_cutout_url"]) if meta.get("cached_cutout_url") else None
    if cached is not None:
        return cached
    return await cutout_service.fetch_cutout_fits(meta["access_url"], meta["ra"], meta["dec"], fov_deg=fov)


def _validated_comparison(cutouts: list[bytes], metadata: list[dict]) -> dict:
    exposures, calibrations, intervals, observation_ids = [], [], [], []
    for data, meta in zip(cutouts, metadata):
        with load_fits_cutout(data) as science:
            header = science["IMAGE"].header
            obs_id = header["OBSID"]
            detector = str(header["DETECTOR"]).strip()
            if obs_id != meta["obs_id"] or f"SPHEREx-D{detector}" != meta["detector"]:
                raise ValueError("FITS exposure identity does not match the selected observation")
            start, end = float(header["MJD-BEG"]), float(header["MJD-END"])
            if not np.isfinite([start, end]).all() or start >= end:
                raise ValueError("FITS exposure time interval is unavailable")
            intervals.append((start, end))
            if obs_id in observation_ids:
                raise ValueError("Select two independent exposures")
            observation_ids.append(obs_id)
            release = meta["collection"].removeprefix("spherex_").removesuffix("_deep")
            if release not in {"dr1", "qr3", "qr2"}:
                raise ValueError("The science release could not be verified")
            exposure, artifact = load_calibrated_exposure(science, release)
            exposures.append(exposure)
            calibrations.append({
                "observation_id": obs_id, "science_release": release,
                "plane_id": artifact.plane_id, "calibration_url": artifact.url,
                "md5": artifact.checksum,
                "checksum_source": artifact.checksum_source,
                "association_url": artifact.association_url,
                "sha256": artifact.sha256,
            })
    ordered_intervals = sorted(intervals)
    if any(current[0] < previous[1] for previous, current in zip(ordered_intervals, ordered_intervals[1:])):
        raise ValueError("Selected exposure time intervals overlap")
    result = (compare_calibrated_pair(*exposures, minimum_passband_overlap=MINIMUM_PASSBAND_OVERLAP)
              if len(exposures) == 2 else
              coadd_calibrated_exposures(exposures, minimum_passband_overlap=MINIMUM_PASSBAND_OVERLAP))
    result["calibrations"] = calibrations
    return result


def _cached_partner_cutout(meta: dict, fov: float) -> bytes | None:
    """Read an already-cached exact cutout, with no image or archive requests."""
    if checksum := meta.get("cached_cutout_sha256"):
        return cache_service.get_verified(meta.get("cached_cutout_url", ""), checksum)
    if meta.get("cached_cutout_url"):
        cached = cache_service.get(meta["cached_cutout_url"])
        if cached is not None:
            return cached
    try:
        key = cutout_cache_key(meta["access_url"], meta["ra"], meta["dec"], fov)
        for candidate in (key, f"cloud-{key}"):
            data = cache_service.get(candidate)
            if data:
                validate_cutout_bytes(data, meta["access_url"])
                return data
    except (KeyError, TypeError, ValueError):
        return None
    return None


def _prepare_cached_partner(data: bytes, meta: dict):
    """Use the same identity, time and calibration guards as comparison."""
    with load_fits_cutout(data) as science:
        header = science["IMAGE"].header
        obs_id = header["OBSID"]
        detector = str(header["DETECTOR"]).strip()
        if obs_id != meta["obs_id"] or f"SPHEREx-D{detector}" != meta["detector"]:
            raise ValueError("FITS exposure identity mismatch")
        start, end = float(header["MJD-BEG"]), float(header["MJD-END"])
        if not np.isfinite([start, end]).all() or start >= end:
            raise ValueError("Exposure interval unavailable")
        release = meta["collection"].removeprefix("spherex_").removesuffix("_deep")
        if release not in {"dr1", "qr3", "qr2"}:
            raise ValueError("Science release unavailable")
        exposure, _ = load_cached_calibrated_exposure(science, release)
        return exposure, (start, end), obs_id


def _scan_cached_partners(frame_id: str, candidate_ids: list[str], fov: float) -> dict:
    reference = OBSERVATION_REGISTRY.get(frame_id)
    if reference is None:
        raise HTTPException(404, "Reference observation not found.")
    candidates = []
    missing = 0
    for candidate_id in dict.fromkeys(candidate_ids):
        if candidate_id == frame_id:
            continue
        meta = OBSERVATION_REGISTRY.get(candidate_id)
        if meta is None:
            missing += 1
            continue
        try:
            same_center = (abs(float(meta["ra"]) - float(reference["ra"])) < 0.000001 and
                           abs(float(meta["dec"]) - float(reference["dec"])) < 0.000001)
        except (KeyError, TypeError, ValueError):
            missing += 1
            continue
        if same_center and meta.get("detector") == reference.get("detector"):
            candidates.append((candidate_id, meta))
    checked, unavailable, matches = 0, missing, []
    try:
        data = _cached_partner_cutout(reference, fov)
        if not data:
            raise ValueError("Reference cutout not cached")
        prepared, interval, ref_obs = _prepare_cached_partner(data, reference)
    except Exception:
        return {"checked": 0, "unavailable": unavailable + len(candidates), "matches": []}
    for candidate_id, meta in candidates:
        try:
            data = _cached_partner_cutout(meta, fov)
            if not data:
                raise ValueError("Candidate cutout not cached")
            candidate, other_interval, obs_id = _prepare_cached_partner(data, meta)
        except Exception:
            unavailable += 1
            continue
        checked += 1
        if obs_id == ref_obs or max(interval[0], other_interval[0]) < min(interval[1], other_interval[1]):
            continue
        try:
            result = compare_calibrated_pair(prepared, candidate, minimum_passband_overlap=MINIMUM_PASSBAND_OVERLAP)
        except (ValueError, NoConvergence, WcsError):
            continue
        matches.append({"frame_id": candidate_id, "retained_pixels": result["retained_pixels"],
                        "reference_pixels": result["reference_pixels"],
                        "minimum_retained_overlap": result["minimum_retained_overlap"]})
    return {"checked": checked, "unavailable": unavailable, "matches": matches}


@router.post("/frames/compatible-partners")
async def compatible_partners(req: CompatiblePartnersRequest):
    """Check up to 12 candidates using already cached images and calibration only."""
    return await run_in_threadpool(_scan_cached_partners, req.frame_id, req.candidate_ids, req.fov)


async def _compare_selected(frame_ids: list[str], fov: float) -> dict:
    metadata = []
    for frame_id in frame_ids:
        meta = OBSERVATION_REGISTRY.get(frame_id)
        if not meta:
            raise HTTPException(404, f"Observation '{frame_id}' was not found.")
        metadata.append(meta)
    if frame_ids[0] == frame_ids[1]:
        raise HTTPException(400, "Select two distinct observations.")
    if all(meta.get("ra") is not None and meta.get("dec") is not None for meta in metadata):
        first = np.deg2rad([metadata[0]["ra"], metadata[0]["dec"]])
        for meta in metadata[1:]:
            other = np.deg2rad([meta["ra"], meta["dec"]])
            if np.rad2deg(angular_separation(*first, *other)) > max(0.5, 2 * fov):
                raise HTTPException(400, "A cutout is too far from reference frame to overlap.")
    if any(meta.get("detector") != metadata[0].get("detector") for meta in metadata[1:]):
        raise HTTPException(422, "Select two observations from the same detector for calibrated comparison.")
    try:
        cutouts = await asyncio.gather(*(_comparison_cutout(meta, fov) for meta in metadata))
        return await run_in_threadpool(_validated_comparison, cutouts, metadata)
    except (ValueError, OSError, KeyError, httpx.HTTPError, NoConvergence, WcsError) as exc:
        logger.info("Rejected comparison between %s: %s", frame_ids, exc)
        reason = str(exc) if isinstance(exc, ValueError) and not isinstance(exc, httpx.HTTPError) else "Required FITS or calibration data unavailable."
        raise HTTPException(
            422, f"Could not verify per-pixel wavelength compatibility using spectral WCS calibration. {reason}",
        ) from exc


def _comparison_metadata(result: dict) -> dict:
    return {key: result[key] for key in (
        "alignment", "compatibility", "minimum_passband_overlap", "minimum_retained_overlap",
        "retained_pixels", "reference_pixels", "calibrations",
    )}


def _science_plane(values: np.ndarray, valid: np.ndarray) -> list:
    return np.where(valid, values.astype(object), None).tolist()


@router.post("/frames/diff")
async def diff_frames(req: DiffRequest = Body(...)):
    """Compute frame 2 minus frame 1 for matched native exposure pixels."""
    result = await _compare_selected([req.frame_id_1, req.frame_id_2], req.fov)
    difference = result["difference"]
    variance = result["difference_variance"]
    valid = np.isfinite(difference)
    retained = difference[valid]
    limit = max(float(np.max(np.abs(retained))), np.finfo(float).tiny)
    display = np.full(difference.shape, 128, dtype=np.uint8)
    display[valid] = np.round(127.5 * (1 + retained / limit)).astype(np.uint8)
    format = req.format or "png"
    return {
        "eligible": True,
        "frame_1": req.frame_id_1, "frame_2": req.frame_id_2,
        "diff_stats": {
            "rms_diff_mjy_sr": float(np.sqrt(np.mean(retained**2))),
            "peak_positive_flux": float(max(0, retained.max())),
            "peak_negative_flux": float(min(0, retained.min())),
            "sigma_mjy_sr": float(np.median(np.sqrt(variance[valid]))),
            "alignment_method": "native_wcs",
        },
        "dimensions": list(difference.shape),
        "calibration": _comparison_metadata(result),
        "surface_brightness_mjy_sr": _science_plane(difference, valid),
        "variance_mjy_sr_squared": _science_plane(variance, valid),
        "image_base64": render_image_to_base64(display, format=format, valid_mask=valid),
        "colormapped_base64": render_image_to_base64(
            display, colormap="coolwarm", format=format, valid_mask=valid,
        ),
    }


@router.post("/frames/stack")
async def stack_frames(req: StackRequest = Body(...)):
    """Co-add independent exposures over their validated pixel overlap."""
    if len(req.frame_ids) < 2 or len(set(req.frame_ids)) != len(req.frame_ids):
        raise HTTPException(400, "At least 2 distinct frame IDs are required.")
    if len(req.frame_ids) > 6:
        raise HTTPException(422, "Select at most six exposures for a calibrated co-add.")
    method = req.method or "mean"
    if method == "median" and len(req.frame_ids) != 2:
        raise HTTPException(422, "Median co-add is supported only for two exposures; select mean or sum.")
    result = await _compare_selected(req.frame_ids, req.fov)
    # A two-value median equals the arithmetic mean.
    factor = len(req.frame_ids) if method == "sum" else 1
    values = result["mean"] * factor
    variance = result["mean_variance"] * factor**2
    valid = np.isfinite(values)
    retained = values[valid]
    display = np.zeros(values.shape, dtype=np.uint8)
    display[valid] = apply_stretch(retained, method=req.stretch or "asinh")
    return {
        "success": True,
        "method": method, "frame_count": len(req.frame_ids), "frame_ids": req.frame_ids,
        "dimensions": list(values.shape),
        "snr_improvement_factor": None,
        "snr_gain_status": "unavailable",
        "theoretical_snr_gain": None,
        "noise_stats": {
            "reference_noise_sigma": None,
            "stacked_noise_sigma": float(np.median(np.sqrt(variance[valid]))),
            "mean_flux_mjy_sr": float(retained.mean()),
            "max_flux_mjy_sr": float(retained.max()),
            "min_flux_mjy_sr": float(retained.min()),
        },
        "alignment_method": "native_wcs",
        "calibration": _comparison_metadata(result),
        "surface_brightness_mjy_sr": _science_plane(values, valid),
        "variance_mjy_sr_squared": _science_plane(variance, valid),
        "image_base64": render_image_to_base64(display, format=req.format or "png", valid_mask=valid),
    }
