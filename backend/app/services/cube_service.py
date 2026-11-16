"""Resolve and cache individual IRSA DR1 HEALPix FITS tiles."""

import csv
import hashlib
import os
import re
import ssl
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from urllib.parse import urlsplit

import astropy.units as u
import certifi
import httpx
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy_healpix import HEALPix

from app.config import CACHE_DIR, IRSA_SIA_BASE_URL
from app.science.spectral_cube import CubeCoverageError, sample_channel_map, sample_cube
from app.services.cloud_cube import sample_cloud_cube

COLLECTION = "spherex_dr1_cube"
HEALPIX = HEALPix(nside=32, order="nested", frame="icrs")
ARCHIVE_PATH = re.compile(r"/ibe/data/spherex/dr1/hips5_cube/[^/]+/Norder5/Dir\d+/Npix(\d+)_cube\.fits")
MAX_TILE_BYTES = 350_000_000
MAX_CACHED_TILES = 4
PINNED_DR1_CUBE_VERSION = os.getenv("SPHEREX_DR1_CUBE_VERSION", "hips_20261026")
if not re.fullmatch(r"hips_[0-9]{8}", PINNED_DR1_CUBE_VERSION):
    raise ValueError("SPHEREX_DR1_CUBE_VERSION must look like hips_YYYYMMDD")
_cache_lock = Lock()


def resolve_tile(client: httpx.Client, position: SkyCoord) -> tuple[int, str]:
    tile = int(HEALPIX.skycoord_to_healpix(position))
    response = client.get(IRSA_SIA_BASE_URL, timeout=8.0, params={
        "COLLECTION": COLLECTION,
        "POS": f"circle {position.icrs.ra.deg:.9f} {position.icrs.dec.deg:.9f} 0.0001",
        "RESPONSEFORMAT": "CSV",
    })
    response.raise_for_status()
    rows = csv.DictReader(response.text.splitlines())
    if not rows.fieldnames or "access_url" not in rows.fieldnames:
        raise ValueError("IRSA returned an unexpected cube search response")
    for row in rows:
        url = row.get("access_url") or ""
        parts = urlsplit(url)
        match = ARCHIVE_PATH.fullmatch(parts.path)
        if (parts.scheme == "https" and parts.netloc == "irsa.ipac.caltech.edu"
                and not parts.query and not parts.fragment and match
                and int(match[1]) == tile):
            return tile, url
    raise CubeCoverageError("IRSA returned no DR1 cube tile covering this coordinate")


def _cache_tile(client: httpx.Client, url: str, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (hashlib.sha256(url.encode()).hexdigest() + ".fits")
    if path.exists():
        path.touch()
        return path
    temporary: Path | None = None
    try:
        with client.stream("GET", url, headers={"Accept-Encoding": "identity"}) as response:
            response.raise_for_status()
            expected_size = int(response.headers.get("Content-Length", 0))
            if response.status_code != 200 or expected_size > MAX_TILE_BYTES:
                raise ValueError("Unexpected size or status for IRSA cube tile")
            with NamedTemporaryFile(dir=directory, suffix=".partial", delete=False) as output:
                temporary = Path(output.name)
                size = 0
                for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                    size += len(chunk)
                    if size > MAX_TILE_BYTES:
                        raise ValueError("IRSA cube tile exceeds the cache size limit")
                    output.write(chunk)
        if size == 0 or size % 2880 or (expected_size and size != expected_size):
            raise ValueError("Incomplete IRSA FITS cube tile")
        with fits.open(temporary, memmap=True) as cube:
            for name in ("IMAGE", "NHITS", "FLAGS", "SPECTRAL_CHANNELS", "WCS-WAVE"):
                cube[name]
        temporary.replace(path)
        stale = sorted(directory.glob("*.fits"), key=lambda item: item.stat().st_mtime, reverse=True)
        for item in stale[MAX_CACHED_TILES:]:
            item.unlink(missing_ok=True)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def load_cube_spectrum(ra: float, dec: float, channel: int | None = None, *, use_pinned: bool = False) -> dict:
    position = SkyCoord(ra * u.deg, dec * u.deg, frame="icrs")
    verify = ssl.create_default_context(cafile=certifi.where())
    with httpx.Client(timeout=httpx.Timeout(20.0, connect=8.0), verify=verify,
                      limits=httpx.Limits(max_connections=12, max_keepalive_connections=12)) as client:
        pinned = use_pinned
        try:
            if use_pinned:
                raise ValueError("Pinned DR1 cloud cube requested")
            tile, url = resolve_tile(client, position)
        except (httpx.HTTPError, ValueError):
            # IRSA publishes this specific DR1 product layout. This path is a
            # dated fallback, never a claim that the newest cube was discovered.
            pinned = True
            tile = int(HEALPIX.skycoord_to_healpix(position))
            directory = tile // 10000 * 10000
            url = ("https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/hips5_cube/"
                   f"{PINNED_DR1_CUBE_VERSION}/Norder5/Dir{directory}/Npix{tile}_cube.fits")
        result, cloud = sample_cloud_cube(client, url, position, channel)
    return {
        "collection": COLLECTION,
        "source": "cloud_dr1_pinned" if pinned else "irsa_archive",
        "cloud": {**cloud, "discovery": "pinned_dr1_release" if pinned else "irsa_sia",
                  "pinned_version": PINNED_DR1_CUBE_VERSION if pinned else None},
        "tile": tile,
        "fits_url": url,
        "ra": ra,
        "dec": dec,
        **result,
    }
