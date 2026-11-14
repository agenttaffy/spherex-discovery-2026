from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Body
from pydantic import BaseModel
from app.science.coordinates import parse_coordinates
from app.services.irsa_client import irsa_client, OBSERVATION_REGISTRY
from app.services.cutout_service import cutout_service
from app.services.catalog_service import catalog_service
from app.science.comparison import check_comparison_eligibility
from app.science.fits_processing import load_fits_cutout, extract_primary_image
from app.science.motion import measure_astrometric_motion
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
    catalog: str = Query("gaia_dr3", description="Catalog name (gaia_dr3, simbad)"),
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

    sources = await catalog_service.query_catalog(
        ra=ra_deg,
        dec=dec_deg,
        radius_deg=radius,
        catalog_name=catalog,
    )
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
        limit=20,
    )

    if not observations and coll_filter is not None:
        # Also check without collection filter
        observations = await irsa_client.query_observations(
            ra=ra_deg,
            dec=dec_deg,
            radius_deg=fov,
            collection=None,
            detector=detector,
            limit=20,
        )

    # 2. Extract image cutouts for each epoch
    epoch_frames = []
    for obs in observations:
        b = None
        cached_url = obs.access_url
        reg_item = OBSERVATION_REGISTRY.get(obs.id)
        if reg_item and "cached_cutout_url" in reg_item:
            from app.services.cache_service import cache_service
            b = cache_service.get(reg_item["cached_cutout_url"])
        if not b:
            try:
                b = await cutout_service.fetch_cutout_fits(obs.access_url, obs.ra, obs.dec, fov_deg=fov)
            except Exception:
                b = None

        if b:
            try:
                hd = load_fits_cutout(b)
                img, hdr = extract_primary_image(hd)
                from app.science.fits_processing import extract_variance_data, extract_fatal_quality_mask
                var = extract_variance_data(hd)
                mask = extract_fatal_quality_mask(hd)
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
                })
            except Exception:
                pass

    series = build_lightcurve_series(epoch_frames, target_ra=ra_deg, target_dec=dec_deg)
    series["target"] = {"ra": ra_deg, "dec": dec_deg}
    return series

@router.get("/science/spectrum")
async def get_spectrum(
    ra: str = Query(..., description="Right Ascension in decimal degrees or sexagesimal"),
    dec: str = Query(..., description="Declination in decimal degrees or sexagesimal"),
    collection: Optional[str] = Query(None, description="SPHEREx collection (or None/ALL for all surveys)"),
    fov: float = Query(0.04, description="Cutout radius in degrees"),
):
    """
    Computes on-the-fly calibrated Spectral Energy Distribution (SED: Flux vs. Wavelength)
    across the 6 SPHEREx detector arrays (0.75 - 5.00 µm) and all 102 spectroscopic channels.
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
        limit=50,
    )

    if not observations and coll_filter is not None:
        observations = await irsa_client.query_observations(
            ra=ra_deg,
            dec=dec_deg,
            radius_deg=max(fov, 0.08),
            collection=None,
            limit=50,
        )

    # Preload cutouts for observations if accessible
    for obs in observations:
        reg_item = OBSERVATION_REGISTRY.get(obs.id)
        has_cached = False
        if reg_item and "cached_cutout_url" in reg_item:
            from app.services.cache_service import cache_service
            has_cached = cache_service.get(reg_item["cached_cutout_url"]) is not None
        if not has_cached and obs.access_url:
            from app.services.demo_service import demo_service
            has_cached = demo_service.get_cached_cutout_for_url(obs.access_url) is not None
        if not has_cached and obs.access_url:
            try:
                await cutout_service.fetch_cutout_fits(obs.access_url, obs.ra, obs.dec, fov_deg=fov)
            except Exception:
                pass

    spectrum = generate_spectrum_for_target(
        ra=ra_deg,
        dec=dec_deg,
        observations=observations,
        cutout_fetcher=cutout_service,
        fov_deg=fov,
    )
    return spectrum

@router.post("/science/motion")
async def compute_astrometric_motion(req: MotionRequest = Body(...)):
    """
    Calculates astrometric vector shift and proper motion rate between two observation epochs.
    """
    meta1 = OBSERVATION_REGISTRY.get(req.frame_id_1)
    meta2 = OBSERVATION_REGISTRY.get(req.frame_id_2)

    if not meta1 or not meta2:
        raise HTTPException(status_code=404, detail="One or both frame IDs not found in registry.")

    eligible, reason = check_comparison_eligibility(meta1, meta2)
    if not eligible:
        raise HTTPException(status_code=400, detail=f"Comparison ineligible: {reason}")

    # Fetch cutout bytes
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

    i1, h1 = extract_primary_image(load_fits_cutout(b1))
    i2, h2 = extract_primary_image(load_fits_cutout(b2))

    tgt_coord = None
    if req.target_ra is not None and req.target_dec is not None:
        tgt_coord = (req.target_ra, req.target_dec)

    motion = measure_astrometric_motion(
        img1=i1,
        img2=i2,
        meta1=meta1,
        meta2=meta2,
        wcs1=h1,
        wcs2=h2,
        target_coord=tgt_coord,
        pixel_scale_arcsec=req.pixel_scale_arcsec or 6.2,
    )

    return {
        "eligible": True,
        "frame_1": req.frame_id_1,
        "frame_2": req.frame_id_2,
        "motion": motion,
    }

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
