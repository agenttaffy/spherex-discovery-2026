from datetime import datetime, timezone
from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.services.irsa_client import irsa_client
from app.services.cache_service import cache_service

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def get_health():
    """
    Returns system status, current UTC time, cached frame count,
    and live connectivity state to NASA IRSA.
    """
    irsa_ok = await irsa_client.check_connectivity()
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        irsa_connected=irsa_ok,
        cached_frames=cache_service.count(),
    )
