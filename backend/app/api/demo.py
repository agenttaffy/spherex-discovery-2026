from fastapi import APIRouter
from typing import List
from app.models.schemas import DemoPreset

router = APIRouter()

OFFICIAL_PRESETS: List[DemoPreset] = [
    DemoPreset(
        id="barnards_star",
        name="Barnard's Star",
        ra=269.45208,
        dec=4.69339,
        description="Highest proper motion star known (10.3 arcsec/yr). Visible 1.6-pixel displacement across 1-year baseline.",
        target_type="High Proper Motion Star",
        default_collection="spherex_dr1",
        notable_feature="Astrometric motion across DR1 (Aug 2025) and QR3 (Aug 2026)",
    ),
    DemoPreset(
        id="wise_0855",
        name="WISE 0855",
        ra=133.79513,
        dec=-7.24515,
        description="Coldest known brown dwarf (~250 K), 7.2 light-years distant. Emits almost purely in mid-infrared wavelengths.",
        target_type="Y-type Sub-stellar Brown Dwarf",
        default_collection="spherex_dr1",
        notable_feature="Strong infrared emission in D4/D5 bands; invisible in optical",
    ),
    DemoPreset(
        id="rw_aurigae",
        name="RW Aurigae",
        ra=76.95420,
        dec=30.40140,
        description="Classical T Tauri binary system with circumstellar disk disruption causing dramatic photometric dimming.",
        target_type="Young Stellar Object / Variable Star",
        default_collection="spherex_dr1",
        notable_feature="Multi-magnitude infrared brightness variations",
    ),
    DemoPreset(
        id="r_draconis",
        name="R Draconis",
        ra=248.33750,
        dec=66.70420,
        description="Mira-type pulsating red giant with a 245-day period and large infrared pulsation amplitude.",
        target_type="Pulsating Asymptotic Giant Branch Star",
        default_collection="spherex_dr1",
        notable_feature="Periodic flux pulsation visible in Level 2 time series",
    ),
    DemoPreset(
        id="epsilon_indi_b",
        name="Epsilon Indi B",
        ra=330.84000,
        dec=-56.78600,
        description="Nearby binary brown dwarf system with prominent orbital and proper motion (4.7 arcsec/yr).",
        target_type="Binary Brown Dwarf System",
        default_collection="spherex_dr1",
        notable_feature="High proper motion and brown dwarf spectral signature",
    ),
]

@router.get("/demo", response_model=List[DemoPreset])
async def get_demo_presets():
    """
    Returns curated official competition test targets with verified SPHEREx coverage.
    """
    return OFFICIAL_PRESETS
