from typing import List, Dict, Any, Optional
from app.services.catalog_service import catalog_service

PROVENANCE_DEMO = "Curated Reference Catalog (Demo)"  # legacy identifier
PROVENANCE_LIVE_GAIA = "VizieR Gaia DR3 (J2016.0)"

async def query_reference_catalog(
    ra: float,
    dec: float,
    radius_deg: float = 0.08,
    catalog_name: str = "gaia_dr3",
) -> List[Dict[str, Any]]:
    """
    Queries Gaia DR3 near the requested position, preserving catalog provenance.
    """
    return await catalog_service.query_catalog(
        ra=ra,
        dec=dec,
        radius_deg=radius_deg,
        catalog_name=catalog_name,
    )
