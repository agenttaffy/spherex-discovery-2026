import logging
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.science.spectral_cube import CubeCoverageError
from app.services.cube_preview import SAMPLE_DESCRIPTION, lookup_preview
from app.services.cube_service import load_cube_spectrum

router = APIRouter()
logger = logging.getLogger(__name__)


def unavailable_archive(ra: float, dec: float, channel: int | None,
                        reason: str, status: int, detail: str, cause: Exception):
    try:
        cached = lookup_preview(ra, dec, channel, reason)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, EOFError) as exc:
        logger.warning("Verified DR1 preview unavailable: %s", exc)
        cached = None
    if cached is not None:
        return cached
    raise HTTPException(status, detail) from cause


@router.get("/cube/spectrum")
def get_cube_spectrum(
    ra: float = Query(ge=0, lt=360),
    dec: float = Query(ge=-90, le=90),
    channel: int | None = Query(default=None, ge=1, le=102),
    source: Literal["archive_first", "preview_only", "pinned_cloud"] = "archive_first",
):
    if source == "preview_only":
        try:
            cached = lookup_preview(ra, dec, channel, "cached_preview_requested")
        except (OSError, ValueError, KeyError, TypeError, AttributeError, EOFError) as exc:
            raise HTTPException(503, "The verified cached preview is unavailable.") from exc
        if cached is None:
            raise HTTPException(404, "No cached preview exists for this coordinate.")
        return cached
    try:
        result = (load_cube_spectrum(ra, dec, channel, use_pinned=True) if source == "pinned_cloud"
                  else load_cube_spectrum(ra, dec, channel))
        return {**result, **SAMPLE_DESCRIPTION, "source": result.get("source", "irsa_archive")}
    except CubeCoverageError as exc:
        raise HTTPException(404, str(exc)) from exc
    except httpx.HTTPError as exc:
        logger.warning("DR1 cube request failed: %s", exc)
        return unavailable_archive(ra, dec, channel, "archive_unreachable", 503,
                                   "The IRSA cube archive could not be reached. Try again later.", exc)
    except (OSError, ValueError, KeyError) as exc:
        logger.warning("DR1 cube could not be read: %s", exc)
        return unavailable_archive(ra, dec, channel, "archive_unreadable", 502,
                                   "The archive returned a cube that could not be read.", exc)
