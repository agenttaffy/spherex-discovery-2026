from fastapi import APIRouter
from typing import List, Dict, Any
from app.models.schemas import DemoPreset
from app.services.demo_service import demo_service, OFFICIAL_PRESETS

router = APIRouter()

@router.get("/demo", response_model=List[DemoPreset])
async def get_demo_presets():
    """
    Returns curated official competition test targets with verified SPHEREx coverage.
    """
    return demo_service.get_presets()

@router.get("/demo/manifest")
async def get_demo_manifest() -> Dict[str, Any]:
    """
    Returns verified demonstration targets and full manifest metadata.
    """
    return {
        "total_cached_cutouts": len(demo_service.raw_manifest),
        "presets_count": len(OFFICIAL_PRESETS),
        "manifest": demo_service.raw_manifest,
    }
