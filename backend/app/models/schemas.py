from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

class ObservationRecord(BaseModel):
    id: str
    obs_id: str
    collection: Optional[str] = "spherex_dr1"
    detector: str
    mjd: Optional[float] = None
    utc_date: Optional[str] = None
    em_min: Optional[float] = None
    em_max: Optional[float] = None
    access_url: str
    ra: float
    dec: float
    search_provenance: str = "unknown"
    search_snapshot_saved: Optional[str] = None
    catalog_coverage: Optional[Literal["inside", "outside"]] = None

class ObservationQueryResponse(BaseModel):
    target: Dict[str, Any]
    collection: str
    total_found: int
    total_found_is_lower_bound: bool = False
    returned_count: int
    observations: List[ObservationRecord]

class PixelStats(BaseModel):
    min_mjy_sr: float
    max_mjy_sr: float
    mean_mjy_sr: float
    std_mjy_sr: float
    median_mjy_sr: float

class FlagSummary(BaseModel):
    quality_state: str = "unknown"
    flagged_pixels: int
    total_pixels: int
    flag_breakdown: Dict[str, int]

class WCSInfo(BaseModel):
    crval1: Optional[float] = None
    crval2: Optional[float] = None
    crpix1: Optional[float] = None
    crpix2: Optional[float] = None
    cdelt1: Optional[float] = None
    cdelt2: Optional[float] = None
    ctype1: Optional[str] = None
    ctype2: Optional[str] = None

class FootprintPixel(BaseModel):
    x: float
    y: float
    inside: bool


class TargetPrediction(BaseModel):
    ra: float
    dec: float
    mjd: float
    pixel: FootprintPixel | None
    reference_url: str


class PhotometryEvidence(BaseModel):
    status: Literal["unavailable"] = "unavailable"
    aperture_status: Literal["not_checked", "unavailable", "field_sample_only"] = "not_checked"
    reason: str
    epsf_present: bool
    core_pixels: int | None = None
    usable_core_pixels: int | None = None
    background_pixels: int | None = None


class FrameResponse(BaseModel):
    frame_id: str
    obs_id: str
    collection: str
    detector: str
    utc_date: Optional[str] = None
    dimensions: List[int]
    pixel_stats: PixelStats
    flag_summary: FlagSummary
    wcs: WCSInfo
    footprint_icrs_deg: Optional[List[List[float]]] = None
    image_base64: str
    colormapped_base64: Optional[str] = None
    provenance_url: str
    is_synthetic: bool = False
    image_provenance: str = "unknown"
    target_predictions: Dict[str, TargetPrediction] = Field(default_factory=dict)
    target_photometry: Dict[str, PhotometryEvidence] = Field(default_factory=dict)

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    irsa_connected: bool
    demo_cache_only: bool = False
    cached_frames: int

class DemoPreset(BaseModel):
    id: str
    name: str
    ra: float
    dec: float
    description: str
    target_type: str
    default_collection: str
    notable_feature: str
