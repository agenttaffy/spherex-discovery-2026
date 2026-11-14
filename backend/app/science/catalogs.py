from typing import List, Dict, Any, Optional
from app.services.catalog_service import catalog_service, CURATED_GAIA_CATALOG

PROVENANCE_DEMO = "Curated Reference Catalog (Demo)"
PROVENANCE_LIVE_GAIA = "Live ESA Gaia TAP"

async def query_reference_catalog(
    ra: float,
    dec: float,
    radius_deg: float = 0.08,
    catalog_name: str = "gaia_dr3",
) -> List[Dict[str, Any]]:
    """
    Queries celestial reference sources (Gaia DR3 / CatWISE) near (ra, dec).
    Explicitly labels provenance as either 'Curated Reference Catalog (Demo)'
    or 'Live ESA Gaia TAP'.
    """
    return await catalog_service.query_catalog(
        ra=ra,
        dec=dec,
        radius_deg=radius_deg,
        catalog_name=catalog_name,
    )
