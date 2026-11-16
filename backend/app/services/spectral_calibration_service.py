"""Resolve spectral calibration artifacts by the science image's plane UUID."""

import csv
import hashlib
import re
import ssl
import logging
from dataclasses import dataclass
from tempfile import NamedTemporaryFile
from pathlib import Path

import certifi
import httpx
from astropy.io import fits

from app.config import CACHE_DIR, DEMO_CACHE_ONLY, IRSA_TAP_BASE_URL
from app.science.calibrated_comparison import prepare_calibrated_exposure
from app.science.spectral_calibration import spectral_calibration_plane_id

IRSA_HOST = "https://irsa.ipac.caltech.edu"
logger = logging.getLogger(__name__)
_PATH = re.compile(
    r"/?ibe/data/spherex/(?P<release>dr1|qr3|qr2)/spectral_wcs/"
    r"cal-s?wcs-v[\w.+-]+/(?P<detector>[1-6])/[\w.+-]+\.fits"
)
_CHECKSUM = re.compile(r"(?:md5:)?[a-fA-F0-9]{32}")


@dataclass(frozen=True)
class CalibrationArtifact:
    plane_id: str
    url: str
    checksum: str
    # Most mappings use an independently published IRSA TAP checksum. Other
    # sources must be named explicitly and must never masquerade as TAP metadata.
    checksum_source: str = "IRSA TAP published MD5"
    association_url: str | None = None
    sha256: str | None = None


# IRSA TAP job 28334899. Both DR1 and QR3 science headers reference this UUID.
_VERIFIED_D6 = CalibrationArtifact(
    "019f4f99-5f21-722d-bd8d-a6033df45708",
    f"{IRSA_HOST}/ibe/data/spherex/dr1/spectral_wcs/cal-swcs-v5-2026-191/6/"
    "spectral_wcs_D6_spx_cal-swcs-v5-2026-191.fits",
    "e665c189ad63ca0cd032c0797e8aabf2",
)

# Evidence source is recorded on each artifact. D3 and D5 are from exact
# completed IRSA TAP jobs 28349004 and 28350118, respectively.
_VERIFIED_ARTIFACTS = {
    # DataLink for each linked science observation returned the named spectral
    # WCS product; that exact science FITS HISTORY names the UUID below. Using
    # the mapping for another exposure is an inference from the same globally
    # identifying plane UUID and detector, not a fresh DataLink check of that
    # exposure. Both digests were computed locally from separately downloaded
    # identical IRSA and S3 bytes; they are not published IRSA TAP checksums.
    ("dr1", "1", "019f4f98-edf0-744b-9600-424841d46dc0"): CalibrationArtifact(
        "019f4f98-edf0-744b-9600-424841d46dc0",
        f"{IRSA_HOST}/ibe/data/spherex/dr1/spectral_wcs/cal-swcs-v5-2026-191/1/"
        "spectral_wcs_D1_spx_cal-swcs-v5-2026-191.fits",
        "624790eba5fdde40a6cb2187099e415d",
        "Locally computed MD5; identical IRSA and public S3 mirror bytes",
        "https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=ivo%3A%2F%2Firsa.ipac%2Fspherex_dr1%3F2025W36_1A_0095_1%2FD1",
        "44fb48b236e25a99d42c8986da0064cc58359527e1fc76e182eda52371a1ae23",
    ),
    ("dr1", "2", "019f4f99-03f1-7376-a5a0-676318f2ddb6"): CalibrationArtifact(
        "019f4f99-03f1-7376-a5a0-676318f2ddb6",
        f"{IRSA_HOST}/ibe/data/spherex/dr1/spectral_wcs/cal-swcs-v5-2026-191/2/"
        "spectral_wcs_D2_spx_cal-swcs-v5-2026-191.fits",
        "af87630c33716cd77ae54ab6c63d388d",
        "Locally computed MD5; identical IRSA and public S3 mirror bytes",
        "https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=ivo%3A%2F%2Firsa.ipac%2Fspherex_dr1%3F2026W17_2A_0308_3%2FD2",
        "0eb4e27f351e6161e21372818f9e811480a7ab8bab9295722f180791e151a463",
    ),
    ("dr1", "4", "019f4f99-3265-766b-b368-e28eb08fdbed"): CalibrationArtifact(
        "019f4f99-3265-766b-b368-e28eb08fdbed",
        f"{IRSA_HOST}/ibe/data/spherex/dr1/spectral_wcs/cal-swcs-v5-2026-191/4/"
        "spectral_wcs_D4_spx_cal-swcs-v5-2026-191.fits",
        "438a1d94ca7b392cf854f68d18bfd7db",
        "Locally computed MD5; identical IRSA and public S3 mirror bytes",
        "https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=ivo%3A%2F%2Firsa.ipac%2Fspherex_dr1%3F2026W17_1B_0162_3%2FD4",
        "dbdcb8addb4ffe817f31786c8cb359b1f47df3528173e9d4602b94c84f7d7c1a",
    ),
    ("dr1", "3", "019f4f99-19af-763f-8f2e-b7dc6cd00055"): CalibrationArtifact(
        "019f4f99-19af-763f-8f2e-b7dc6cd00055",
        f"{IRSA_HOST}/ibe/data/spherex/dr1/spectral_wcs/cal-swcs-v5-2026-191/3/"
        "spectral_wcs_D3_spx_cal-swcs-v5-2026-191.fits",
        "327f973e59efeaa101bf1fe9ac7c354e",
    ),
    ("dr1", "5", "019f4f99-48fc-73a4-b778-eb25bf616d6b"): CalibrationArtifact(
        "019f4f99-48fc-73a4-b778-eb25bf616d6b",
        f"{IRSA_HOST}/ibe/data/spherex/dr1/spectral_wcs/cal-swcs-v5-2026-191/5/"
        "spectral_wcs_D5_spx_cal-swcs-v5-2026-191.fits",
        "d59bd98b5d1d14ae8d74499b1c1ccb3f",
    ),
    **{(release, "6", _VERIFIED_D6.plane_id): _VERIFIED_D6 for release in ("dr1", "qr3")},
}


def verified_artifact(release: str, detector: str, plane_id: str) -> CalibrationArtifact | None:
    artifact = _VERIFIED_ARTIFACTS.get((release, detector, plane_id))
    if artifact is None and release in {"dr1", "qr3"}:
        # The image HISTORY contains a globally identifying plane UUID. Reuse
        # across current releases is an inference from the identical UUID and
        # detector, based on the pinned artifact's documented association;
        # the association may come from TAP or an example DataLink exposure.
        other = "qr3" if release == "dr1" else "dr1"
        artifact = _VERIFIED_ARTIFACTS.get((other, detector, plane_id))
    return artifact


def verified_cached_bytes(artifact: CalibrationArtifact) -> bytes | None:
    name = f"spectral-{artifact.checksum}.fits"
    # Keep the legacy D6 cache readable while staging new maps separately.
    for path in (CACHE_DIR / "spectral-calibration" / name, CACHE_DIR / name):
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if (hashlib.md5(data).hexdigest() == artifact.checksum
                and (artifact.sha256 is None or hashlib.sha256(data).hexdigest() == artifact.sha256.lower())):
            return data
    return None


def download_verified_bytes(client: httpx.Client, artifact: CalibrationArtifact) -> bytes:
    """Read the documented calibration artifact from its public mirror or IRSA.

    The cloud URL is derived only from a validated IRSA calibration path. Both
    Both sources must satisfy the expected MD5 before use or caching, plus the
    expected SHA-256 when one is pinned. The digest source is recorded on the
    artifact: IRSA TAP metadata or locally computed matching mirror digests.
    """
    if not artifact.url.startswith(IRSA_HOST + "/"):
        raise ValueError("Unsupported calibration source")
    path = artifact.url.removeprefix(IRSA_HOST)
    if (not _PATH.fullmatch(path) or not _CHECKSUM.fullmatch(artifact.checksum)
            or (artifact.sha256 is not None and not re.fullmatch(r"[a-fA-F0-9]{64}", artifact.sha256))):
        raise ValueError("Unsupported calibration path or checksum")
    cloud = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com" + path.removeprefix("/ibe/data/spherex")
    last_error = None
    for url in (cloud, artifact.url):
        try:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                content = bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > 40_000_000:
                        raise ValueError("Spectral calibration file exceeds the size limit")
            data = bytes(content)
            if hashlib.md5(data).hexdigest() != artifact.checksum.lower().removeprefix("md5:"):
                raise ValueError("Spectral calibration checksum mismatch")
            if artifact.sha256 is not None and hashlib.sha256(data).hexdigest() != artifact.sha256.lower():
                raise ValueError("Spectral calibration SHA-256 mismatch")
            return data
        except (httpx.HTTPError, OSError, ValueError) as exc:
            last_error = exc
            logger.warning("Verified calibration download failed for %s: %s", url, exc)
    raise ValueError("The verified spectral calibration could not be downloaded from cloud or IRSA") from last_error


def load_calibrated_exposure(science: fits.HDUList, release: str):
    plane_id = spectral_calibration_plane_id(science)
    detector = str(science["IMAGE"].header.get("DETECTOR", "")).strip()
    verify = ssl.create_default_context(cafile=certifi.where())
    with httpx.Client(verify=verify, timeout=5.0) as client:
        artifact = verified_artifact(release, detector, plane_id)
        if artifact is None:
            if DEMO_CACHE_ONLY:
                raise ValueError(f"Exact detector D{detector} calibration is unresolved in the local demo")
            artifact = find_calibration_artifact(client, science, release)
        data = verified_cached_bytes(artifact)
        download_needed = data is None
        if download_needed:
            if DEMO_CACHE_ONLY:
                raise ValueError(f"Verified detector D{detector} calibration bytes are missing from the local cache")
            data = download_verified_bytes(client, artifact)
        exposure = prepare_calibrated_exposure(
            science, data, plane_id=artifact.plane_id, checksum=artifact.checksum,
        )
        if download_needed:
            path = CACHE_DIR / "spectral-calibration" / f"spectral-{artifact.checksum}.fits"
            path.parent.mkdir(parents=True, exist_ok=True)
            temp: Path | None = None
            try:
                with NamedTemporaryFile(dir=path.parent, suffix=".partial", delete=False) as output:
                    temp = Path(output.name)
                    output.write(data)
                temp.replace(path)
            finally:
                if temp is not None:
                    temp.unlink(missing_ok=True)
        return exposure, artifact


def find_calibration_artifact(
    client: httpx.Client, science: fits.HDUList, release: str,
) -> CalibrationArtifact:
    plane_id = spectral_calibration_plane_id(science)
    detector = str(science["IMAGE"].header.get("DETECTOR", "")).strip()
    response = client.get(IRSA_TAP_BASE_URL, params={
        "REQUEST": "doQuery",
        "LANG": "ADQL",
        "FORMAT": "csv",
        "QUERY": "SELECT uri, contentchecksum FROM spherex.artifact "
                 f"WHERE planeid='{plane_id}'",
    })
    response.raise_for_status()
    rows = csv.DictReader(response.text.splitlines())
    if not rows.fieldnames or not {"uri", "contentchecksum"}.issubset(rows.fieldnames):
        raise ValueError("Unexpected IRSA calibration catalog response")
    candidates = set()
    for row in rows:
        path = (row["uri"] or "").removeprefix(IRSA_HOST)
        checksum = (row["contentchecksum"] or "").strip().lower()
        match = _PATH.fullmatch(path)
        if (match and match["detector"] == detector
                and _CHECKSUM.fullmatch(checksum)):
            candidates.add((match["release"], f"{IRSA_HOST}/{path.lstrip('/')}",
                            checksum.removeprefix("md5:")))
    choices = {item for item in candidates if item[0] == release}
    if not choices and release in {"dr1", "qr3"}:
        # DR1 and QR3 can reference the exact same calibration plane UUID.
        choices = {item for item in candidates if item[0] in {"dr1", "qr3"}}
    if len(choices) != 1:
        raise ValueError("No unique calibration artifact with a published checksum for this release and detector")
    _, url, checksum = choices.pop()
    return CalibrationArtifact(plane_id, url, checksum)
