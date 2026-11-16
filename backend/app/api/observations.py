from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from app.models.schemas import ObservationQueryResponse
from app.science.coordinates import parse_coordinates
from app.services.irsa_client import irsa_client
from app.config import DEFAULT_FOV_DEG, MAX_FOV_DEG

router = APIRouter()

@router.get("/observations", response_model=ObservationQueryResponse)
async def get_observations(
    ra: str = Query(..., description="Right Ascension in decimal degrees or sexagesimal"),
    dec: str = Query(..., description="Declination in decimal degrees or sexagesimal"),
    fov: float = Query(DEFAULT_FOV_DEG, description="Field of View / search radius in degrees"),
    collection: str = Query("spherex_dr1", description="Wide: spherex_dr1, spherex_qr3 or ALL; opt-in deep: spherex_dr1_deep, spherex_qr3_deep or DEEP"),
    detector: Optional[str] = Query(None, description="Optional detector filter (e.g. SPHEREx-D1)"),
    limit: int = Query(50, ge=1, le=200, description="Max observations to return"),
):
    """
    Queries NASA IRSA SIA2 service for SPHEREx observations matching coordinates.
    """
    # 1. Parse and validate coordinates
    try:
        ra_deg, dec_deg = parse_coordinates(ra, dec)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Bound FOV
    if fov <= 0.0 or fov > MAX_FOV_DEG:
        raise HTTPException(
            status_code=400,
            detail=f"Field of View {fov} deg out of allowed range (0.001 to {MAX_FOV_DEG} deg).",
        )

    # 3. Query IRSA
    records = await irsa_client.query_observations(
        ra=ra_deg,
        dec=dec_deg,
        radius_deg=fov,
        collection=collection,
        detector=detector,
        limit=limit,
    )

    return ObservationQueryResponse(
        target={"ra": ra_deg, "dec": dec_deg, "fov": fov},
        collection=collection,
        total_found=len(records),
        total_found_is_lower_bound=(collection.upper() == "DEEP" or collection.lower().endswith("_deep") or len(records) >= limit or any(
            record.search_provenance in {"saved_irsa_search", "cached_demo", "demo_metadata", "cloud_header_survey"} for record in records
        )),
        returned_count=len(records),
        observations=records,
    )
