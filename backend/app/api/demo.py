import json

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.config import DEMO_CACHE_ONLY, MANIFESTS_DIR
from app.models.schemas import DemoPreset, ObservationRecord
from app.services.cache_service import cache_service
from app.services.demo_service import demo_service, OFFICIAL_PRESETS
from app.services.irsa_client import OBSERVATION_REGISTRY
from app.services.spectral_calibration_service import verified_artifact, verified_cached_bytes

router = APIRouter()

D5_PLANE = "019f4f99-48fc-73a4-b778-eb25bf616d6b"


@router.get("/demo/comparison", response_model=list[ObservationRecord])
def get_demo_comparison():
    """Register the fixed-footprint pair after verifying all local inputs."""
    artifact = verified_artifact("dr1", "5", D5_PLANE)
    if artifact is None or verified_cached_bytes(artifact) is None:
        raise HTTPException(503, "Eligible D5 pair unavailable: verified calibration is missing or fails its checksum.")

    entries = json.loads((MANIFESTS_DIR / "d5_comparison.json").read_text(encoding="utf-8"))
    records = []
    for entry in entries:
        cutout_url = entry["cutout_url"]
        if cache_service.get_verified(cutout_url, entry["sha256"]) is None:
            raise HTTPException(503, "Eligible D5 pair unavailable: a verified FITS cutout is missing or fails its checksum.")
        record = ObservationRecord(
            **entry, id=f"demo_comparison_{entry['obs_id']}_D5",
            access_url=cutout_url.split("?", 1)[0],
            search_provenance="cached_demo",
        )
        records.append((record, cutout_url, entry["sha256"]))
    OBSERVATION_REGISTRY.update({
        record.id: {**record.model_dump(), "cached_cutout_url": url, "cached_cutout_sha256": checksum}
        for record, url, checksum in records
    })
    return [record for record, _, _ in records]

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
