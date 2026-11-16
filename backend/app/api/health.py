from datetime import datetime, timezone
import asyncio
from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.config import DEMO_CACHE_ONLY
from app.services.irsa_client import irsa_client
from app.services.cache_service import cache_service

router = APIRouter()

@router.get("/ready")
async def get_readiness():
    """Local process readiness does not depend on an external archive."""
    return {"status": "healthy", "demo_cache_only": DEMO_CACHE_ONLY}

@router.get("/health", response_model=HealthResponse)
async def get_health():
    """
    Returns system status, current UTC time, cached frame count,
    and live connectivity state to NASA IRSA.
    """
    try:
        irsa_ok = False if DEMO_CACHE_ONLY else await asyncio.wait_for(irsa_client.check_connectivity(), timeout=4.0)
    except asyncio.TimeoutError:
        irsa_ok = False
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        irsa_connected=irsa_ok,
        demo_cache_only=DEMO_CACHE_ONLY,
        cached_frames=cache_service.count(),
    )
