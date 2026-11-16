from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Body
from pydantic import BaseModel
from app.science.coordinates import parse_coordinates
from app.services.irsa_client import irsa_client, OBSERVATION_REGISTRY
from app.services.cutout_service import cutout_service
from app.services.catalog_service import catalog_service, CatalogUnavailable
from app.science.fits_processing import load_fits_cutout, extract_primary_image
from app.science.photometry import build_lightcurve_series
from app.science.report import generate_discovery_report
from app.science.spectrum import generate_spectrum_for_target

router = APIRouter()

class MotionRequest(BaseModel):
    frame_id_1: str
    frame_id_2: str
    target_ra: Optional[float] = None
    target_dec: Optional[float] = None
    pixel_scale_arcsec: Optional[float] = 6.2

class ReportRequest(BaseModel):
    target_name: str
    ra: float
    dec: float
    target_type: Optional[str] = None
    motion_data: Optional[Dict[str, Any]] = None
    photometry_data: Optional[Dict[str, Any]] = None
    observations: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    spectrum_data: Optional[Dict[str, Any]] = None

@router.get("/science/catalogs")
async def get_catalogs(
    ra: str = Query(..., description="Right Ascension in decimal degrees or sexagesimal"),
    dec: str = Query(..., description="Declination in decimal degrees or sexagesimal"),
    radius: float = Query(0.08, description="Search radius in degrees"),
    catalog: str = Query("gaia_dr3", description="Reference catalog (gaia_dr3)"),
):
    """
    Returns reference catalog stars (e.g. Gaia DR3) with proper motions and magnitudes
    near given coordinates.
    """
    try:
        ra_deg, dec_deg = parse_coordinates(ra, dec)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if radius <= 0 or radius > 1.0:
        raise HTTPException(status_code=400, detail="Radius must be between 0.001 and 1.0 degrees.")

    try:
        sources = await catalog_service.query_catalog(
            ra=ra_deg, dec=dec_deg, radius_deg=radius, catalog_name=catalog,
        )
    except CatalogUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "catalog": catalog,
        "center": {"ra": ra_deg, "dec": dec_deg},
        "radius_deg": radius,
        "total_sources": len(sources),
        "sources": sources,
    }

@router.get("/science/photometry")
async def get_photometry(
    ra: str = Query(..., description="Right Ascension in decimal degrees or sexagesimal"),
    dec: str = Query(..., description="Declination in decimal degrees or sexagesimal"),
    collection: Optional[str] = Query(None, description="SPHEREx collection (or None/ALL for all surveys)"),
    detector: Optional[str] = Query(None, description="Detector filter (e.g. SPHEREx-D1)"),
    fov: float = Query(0.04, description="Cutout radius in degrees"),
):
    """
    Extracts circular aperture photometry time series across all available epochs for a target coordinate.
    """
    try:
        ra_deg, dec_deg = parse_coordinates(ra, dec)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if fov <= 0 or fov > 2.0:
        raise HTTPException(status_code=400, detail="FOV must be between 0.001 and 2.0 degrees.")

    coll_filter = None if (not collection or collection.lower() in ("all", "none")) else collection

    # 1. Fetch matching observation records
    observations = await irsa_client.query_observations(
        ra=ra_deg,
        dec=dec_deg,
        radius_deg=fov,
        collection=coll_filter,
        detector=detector,
        limit=60,
    )

    # 2. Extract image cutouts for each epoch
    epoch_frames = []
    for obs in observations:
        # Analysis never downloads every search result in the background.
        from app.services.cache_service import cache_service
        from app.services.cutout_service import cutout_cache_key
        reg_item = OBSERVATION_REGISTRY.get(obs.id, {})
        cached_url = reg_item.get("cached_cutout_url")
        checksum = reg_item.get("cached_cutout_sha256")
        b = cache_service.get_verified(cached_url, checksum) if cached_url and checksum else (cache_service.get(cached_url) if cached_url else None)
        if not b and obs.access_url:
            key = cutout_cache_key(obs.access_url, obs.ra, obs.dec, fov)
            # Match the viewer's precedence and use only local cache; never
            # initiate a cloud or IRSA download for background analysis.
            b = cache_service.get(key) or cache_service.get(f"cloud-{key}")

        if b:
            try:
                hd = load_fits_cutout(b)
                img, hdr = extract_primary_image(hd, preserve_nan=True)
                from app.science.fits_processing import (
                    extract_variance_data,
                    extract_fatal_quality_mask,
                    extract_source_mask,
                )
                var = extract_variance_data(hd)
                mask = extract_fatal_quality_mask(hd)
                src_mask = extract_source_mask(hd)
                epoch_frames.append({
                    "frame_id": obs.id,
                    "obs_id": obs.obs_id,
                    "mjd": obs.mjd,
                    "utc_date": obs.utc_date,
                    "detector": obs.detector,
                    "collection": obs.collection,
                    "image": img,
                    "header": hdr,
                    "variance": var,
                    "mask": mask,
                    "source_mask": src_mask,
                })
            except Exception:
                pass

    series = build_lightcurve_series(epoch_frames, target_ra=ra_deg, target_dec=dec_deg)
    series["target"] = {"ra": ra_deg, "dec": dec_deg}
    series["analysis_source"] = "cached_cutouts_only"
    series["observations_considered"] = len(observations)
    series["cutouts_available"] = len(epoch_frames)
    return series

@router.get("/science/spectrum")
async def get_spectrum(
    ra: str = Query(..., description="Right Ascension in decimal degrees or sexagesimal"),
    dec: str = Query(..., description="Declination in decimal degrees or sexagesimal"),
    collection: Optional[str] = Query(None, description="SPHEREx collection (or None/ALL for all surveys)"),
    fov: float = Query(0.04, description="Cutout radius in degrees"),
):
    """
    Summarizes available cached detector field samples without fabricating a spectrum.
    """
    try:
        ra_deg, dec_deg = parse_coordinates(ra, dec)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if fov <= 0 or fov > 2.0:
        raise HTTPException(status_code=400, detail="FOV must be between 0.001 and 2.0 degrees.")

    coll_filter = None if (not collection or collection.lower() in ("all", "none")) else collection

    observations = await irsa_client.query_observations(
        ra=ra_deg,
        dec=dec_deg,
        radius_deg=max(fov, 0.08),
        collection=coll_filter,
        limit=60,
    )

    spectrum = generate_spectrum_for_target(
        ra=ra_deg,
        dec=dec_deg,
        observations=observations,
        cutout_fetcher=cutout_service,
        fov_deg=fov,
    )
    spectrum["analysis_source"] = "cached_cutouts_only"
    spectrum["observations_considered"] = len(observations)
    return spectrum

@router.post("/science/motion")
async def compute_astrometric_motion(req: MotionRequest = Body(...)):
    """Do not report proper motion without verified cross-epoch source association."""
    if req.frame_id_1 not in OBSERVATION_REGISTRY or req.frame_id_2 not in OBSERVATION_REGISTRY:
        raise HTTPException(status_code=404, detail="One or both frame IDs not found in registry.")
    raise HTTPException(status_code=422, detail=(
        "Automatic motion measurement is unavailable: source association, image quality, "
        "wavelength compatibility, and astrometric uncertainties must be independently validated. "
        "Use blink or a validated difference to inspect the field."
    ))


@router.post("/science/report")
async def make_discovery_report(req: ReportRequest = Body(...)):
    """
    Generates a formal Space Apps scientific discovery report with J2000 coordinates,
    proper motion analysis, lightcurve summary, and IRSA archive DOIs.
    """
    report = generate_discovery_report(
        target_name=req.target_name,
        ra_deg=req.ra,
        dec_deg=req.dec,
        target_type=req.target_type,
        motion_data=req.motion_data,
        photometry_data=req.photometry_data,
        observations=req.observations,
        notes=req.notes,
        spectrum_data=req.spectrum_data,
    )
    return report
