from typing import Optional, Literal, List
import numpy as np
from fastapi import APIRouter, Query, HTTPException, Body
from pydantic import BaseModel
from app.models.schemas import FrameResponse
from app.services.cutout_service import cutout_service
from app.services.irsa_client import OBSERVATION_REGISTRY
from app.science.comparison import check_comparison_eligibility, compute_difference_frame
from app.science.stacking import compute_coadd_stack
from app.science.fits_processing import (
    load_fits_cutout,
    extract_primary_image,
    render_image_to_base64,
    render_image_to_base64_png,
    apply_stretch,
)

router = APIRouter()

class DiffRequest(BaseModel):
    frame_id_1: str
    frame_id_2: str
    format: Optional[str] = "png"

class StackRequest(BaseModel):
    frame_ids: List[str]
    method: Optional[Literal["mean", "median", "sum"]] = "mean"
    format: Optional[str] = "png"
    stretch: Optional[str] = "asinh"

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering frame: {str(e)}")

@router.post("/frames/diff")
async def diff_frames(req: DiffRequest = Body(...)):
    """
    Computes scientific difference image between two observations (frame 2 minus frame 1).
    Utilizes astropy / reproject WCS celestial alignment across epochs.
    """
    meta1 = OBSERVATION_REGISTRY.get(req.frame_id_1)
    meta2 = OBSERVATION_REGISTRY.get(req.frame_id_2)

    if not meta1 or not meta2:
        raise HTTPException(status_code=404, detail="One or both frame IDs not found in registry.")

    eligible, reason = check_comparison_eligibility(meta1, meta2)
    if not eligible:
        raise HTTPException(status_code=400, detail=f"Comparison ineligible: {reason}")

    try:
        # Fetch cutouts using cache or cutout service
        b1 = None
        if "cached_cutout_url" in meta1:
            from app.services.cache_service import cache_service
            b1 = cache_service.get(meta1["cached_cutout_url"])
        if not b1:
            b1 = await cutout_service.fetch_cutout_fits(meta1["access_url"], meta1["ra"], meta1["dec"])

        b2 = None
        if "cached_cutout_url" in meta2:
            from app.services.cache_service import cache_service
            b2 = cache_service.get(meta2["cached_cutout_url"])
        if not b2:
            b2 = await cutout_service.fetch_cutout_fits(meta2["access_url"], meta2["ra"], meta2["dec"])
        
        hd1 = load_fits_cutout(b1)
        hd2 = load_fits_cutout(b2)
        i1, h1 = extract_primary_image(hd1)
        i2, h2 = extract_primary_image(hd2)

        from app.science.fits_processing import extract_fatal_quality_mask
        mask1 = extract_fatal_quality_mask(hd1)
        mask2 = extract_fatal_quality_mask(hd2)

        diff_u8, stats = compute_difference_frame(i1, i2, wcs1=h1, wcs2=h2, mask1=mask1, mask2=mask2)
        diff_b64 = render_image_to_base64(diff_u8, format=req.format or "png")

        return {
            "eligible": True,
            "frame_1": req.frame_id_1,
            "frame_2": req.frame_id_2,
            "diff_stats": stats,
            "dimensions": [int(diff_u8.shape[0]), int(diff_u8.shape[1])],
            "image_base64": diff_b64,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing frame difference: {e}")

@router.post("/frames/stack")
async def stack_frames(req: StackRequest = Body(...)):
    """
    Computes scientific image co-addition / stacking across multiple observation frames.
    Uses astropy / reproject WCS celestial alignment to register frames onto a shared celestial grid.
    Computes SNR improvement factor (~sqrt(N)) and noise reduction statistics.
    """
    if not req.frame_ids or len(req.frame_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 frame IDs are required for co-addition/stacking.")
    if len(set(req.frame_ids)) < 2:
        raise HTTPException(status_code=400, detail="At least 2 distinct frame IDs are required for co-addition/stacking.")

    images = []
    wcs_list = []
    variances = []
    masks = []
    detectors = []
    resolved_ids = []
    metas = []

    for fid in req.frame_ids:
        meta = OBSERVATION_REGISTRY.get(fid)
        if not meta:
            raise HTTPException(status_code=404, detail=f"Frame ID '{fid}' not found in observation registry.")
        metas.append(meta)

    # Check celestial proximity across frames to ensure overlapping footprints
    ref_ra = float(metas[0].get("ra", 0.0))
    ref_dec = float(metas[0].get("dec", 0.0))
    for m in metas[1:]:
        c_ra = float(m.get("ra", 0.0))
        c_dec = float(m.get("dec", 0.0))
        delta_ra = (ref_ra - c_ra + 180.0) % 360.0 - 180.0
        mean_dec_rad = np.radians((ref_dec + c_dec) / 2.0)
        dist_deg = float(np.hypot(delta_ra * np.cos(mean_dec_rad), ref_dec - c_dec))
        if dist_deg > 0.5:
            raise HTTPException(
                status_code=400,
                detail=f"Frame '{m.get('id')}' pointing is too far from reference frame ({dist_deg:.2f}° > 0.5°). Co-addition requires overlapping celestial footprints."
            )

    for fid, meta in zip(req.frame_ids, metas):

        b = None
        if "cached_cutout_url" in meta:
            from app.services.cache_service import cache_service
            b = cache_service.get(meta["cached_cutout_url"])
        if not b and "access_url" in meta:
            from app.services.demo_service import demo_service
            b = demo_service.get_cached_cutout_for_url(meta["access_url"])
        if not b and "access_url" in meta:
            b = await cutout_service.fetch_cutout_fits(meta["access_url"], meta["ra"], meta["dec"])

        if not b:
            raise HTTPException(status_code=404, detail=f"Unable to load FITS data for frame '{fid}'.")

        try:
            hd = load_fits_cutout(b)
            img, hdr = extract_primary_image(hd)
            from app.science.fits_processing import extract_variance_data, extract_fatal_quality_mask
            var = extract_variance_data(hd)
            mask = extract_fatal_quality_mask(hd)
            images.append(img)
            wcs_list.append(hdr)
            variances.append(var)
            masks.append(mask)
            detectors.append(meta.get("detector"))
            resolved_ids.append(fid)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to process FITS cutout for frame '{fid}': {e}")

    try:
        stacked_float, stats = compute_coadd_stack(
            images=images,
            wcs_list=wcs_list,
            method=req.method or "mean",
            variances=variances,
            masks=masks,
            detectors=detectors,
        )
        u8_stacked = apply_stretch(stacked_float, method=req.stretch or "asinh")
        stacked_b64 = render_image_to_base64(u8_stacked, format=req.format or "png")

        return {
            "success": True,
            "method": stats["method"],
            "frame_count": stats["frame_count"],
            "frame_ids": resolved_ids,
            "dimensions": [int(stacked_float.shape[0]), int(stacked_float.shape[1])],
            "snr_improvement_factor": stats["snr_improvement_factor"],
            "theoretical_snr_gain": stats["theoretical_snr_gain"],
            "noise_stats": {
                "reference_noise_sigma": stats["reference_noise_sigma"],
                "stacked_noise_sigma": stats["stacked_noise_sigma"],
                "mean_flux_mjy_sr": stats["mean_flux_mjy_sr"],
                "max_flux_mjy_sr": stats["max_flux_mjy_sr"],
                "min_flux_mjy_sr": stats["min_flux_mjy_sr"],
            },
            "alignment_method": stats["alignment_method"],
            "image_base64": stacked_b64,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing frame co-addition: {e}")
