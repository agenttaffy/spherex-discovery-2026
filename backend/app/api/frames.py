from typing import Optional, Literal
from fastapi import APIRouter, Query, HTTPException, Body
from pydantic import BaseModel
from app.models.schemas import FrameResponse
from app.services.cutout_service import cutout_service
from app.services.irsa_client import OBSERVATION_REGISTRY
from app.science.comparison import check_comparison_eligibility, compute_difference_frame
from app.science.fits_processing import (
    load_fits_cutout,
    extract_primary_image,
    render_image_to_base64,
    render_image_to_base64_png,
)

router = APIRouter()

class DiffRequest(BaseModel):
    frame_id_1: str
    frame_id_2: str
    format: Optional[str] = "png"

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

        diff_u8, stats = compute_difference_frame(i1, i2, wcs1=h1, wcs2=h2)
        diff_b64 = render_image_to_base64(diff_u8, format=req.format or "png")

        return {
            "eligible": True,
            "frame_1": req.frame_id_1,
            "frame_2": req.frame_id_2,
            "diff_stats": stats,
            "dimensions": [int(diff_u8.shape[0]), int(diff_u8.shape[1])],
            "image_base64": diff_b64,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing frame difference: {e}")
