from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ObservationRecord(BaseModel):
    id: str
    obs_id: str
    collection: str
    detector: str
    mjd: Optional[float] = None
    utc_date: Optional[str] = None
    em_min: Optional[float] = None
    em_max: Optional[float] = None
    access_url: str
    ra: float
    dec: float

class ObservationQueryResponse(BaseModel):
    target: Dict[str, Any]
    collection: str
    total_found: int
    returned_count: int
    observations: List[ObservationRecord]

class PixelStats(BaseModel):
    min_mjy_sr: float
    max_mjy_sr: float
    mean_mjy_sr: float
    std_mjy_sr: float
    median_mjy_sr: float

class FlagSummary(BaseModel):
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
    image_base64: str
    colormapped_base64: Optional[str] = None
    provenance_url: str
    is_synthetic: bool = False

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    irsa_connected: bool
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
