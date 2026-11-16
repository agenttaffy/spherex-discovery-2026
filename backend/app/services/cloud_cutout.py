"""Bounded range reads of public IRSA SPHEREx spectral images on AWS.

The cloud mirror contains full MEFs, not the IRSA cutout service. We slice the
native detector pixels and preserve their original metadata and calibration
references. The SIA search remains necessary to discover current observations.
"""
import io
import re
import time
from urllib.parse import urlsplit

import astropy.units as u
import httpx
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.wcs import WCS

_SOURCE = re.compile(
    r"/ibe/data/spherex/(?:dr1|qr3)/level2/[A-Za-z0-9_]+/"
    r"(?P<processing>l2b(?:_retry)?-v[A-Za-z0-9._+-]+)/(?P<detector>[1-6])/"
    r"level2_(?P<observation>[A-Za-z0-9_]+)D(?P=detector)_spx_(?P=processing)\.fits"
)
_HOST = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com"
_MAX_TOTAL = 24_000_000
_MAX_OBJECT = 250_000_000
_BLOCK = 128 * 1024
_MAX_SECONDS = 35.0


def cloud_url_from_irsa(access_url: str) -> str | None:
    """Map only official DR1/QR3 image URLs to the exact official S3 key."""
    parsed = urlsplit(access_url)
    if (parsed.scheme != "https" or parsed.netloc != "irsa.ipac.caltech.edu"
            or parsed.query or parsed.fragment or not _SOURCE.fullmatch(parsed.path)):
        return None
    return _HOST + parsed.path.removeprefix("/ibe/data/spherex")


def expected_image_identity(access_url: str) -> tuple[str, str] | None:
    """Return the observation and detector encoded in a supported official URL."""
    if not cloud_url_from_irsa(access_url):
        return None
    match = _SOURCE.fullmatch(urlsplit(access_url).path)
    return match["observation"], match["detector"]


class CloudRangeReader(io.RawIOBase):
    """Seekable reader requiring consistent, exact HTTP byte ranges and ETags."""
    def __init__(self, client: httpx.Client, url: str):
        super().__init__()
        self.client, self.url = client, url
        self.offset = 0
        self.length = None
        self.etag = None
        self.transferred = 0
        self.started = time.monotonic()
        self.blocks = {}
        self._fetch(0, 2880)

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.offset

    def seek(self, offset, whence=io.SEEK_SET):
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.offset, io.SEEK_END: self.length}[whence]
        position = base + offset
        if position < 0:
            raise ValueError("Cannot seek before the cloud FITS file")
        self.offset = position
        return position

    def _fetch(self, start: int, size: int) -> bytes:
        if self.length is not None:
            size = min(size, max(0, self.length - start))
        if not size:
            return b""
        if time.monotonic() - self.started > _MAX_SECONDS:
            raise ValueError("Cloud cutout exceeded its time limit")
        if self.transferred + size > _MAX_TOTAL:
            raise ValueError("Cloud image requires too much data for a bounded cutout")
        end = start + size - 1
        headers = {"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"}
        if self.etag:
            headers["If-Match"] = self.etag
        with self.client.stream("GET", self.url, headers=headers) as response:
            response.raise_for_status()
            match = re.fullmatch(rf"bytes {start}-{end}/(\d+)", response.headers.get("Content-Range", ""))
            etag = response.headers.get("ETag")
            if response.status_code != 206 or not match or not etag:
                raise ValueError("Cloud server returned an invalid FITS byte range")
            length = int(match.group(1))
            if length > _MAX_OBJECT or length % 2880 or (self.length is not None and (length != self.length or etag != self.etag)):
                raise ValueError("Cloud FITS size or object identity changed")
            result = bytearray()
            for chunk in response.iter_bytes(chunk_size=min(65536, size)):
                result.extend(chunk)
                if len(result) > size:
                    raise ValueError("Cloud server returned more bytes than requested")
                if time.monotonic() - self.started > _MAX_SECONDS:
                    raise ValueError("Cloud cutout exceeded its time limit")
            if len(result) != size:
                raise ValueError("Cloud server returned a truncated FITS byte range")
        self.length, self.etag = length, etag
        self.transferred += size
        return bytes(result)

    def read(self, size=-1):
        if size < 0:
            size = self.length - self.offset
        size = min(size, max(0, self.length - self.offset))
        output = bytearray()
        while size:
            block_start = (self.offset // _BLOCK) * _BLOCK
            if block_start not in self.blocks:
                self.blocks[block_start] = self._fetch(block_start, _BLOCK)
            block = self.blocks[block_start]
            relative = self.offset - block_start
            take = min(size, len(block) - relative)
            if take <= 0:
                raise ValueError("Unexpected end of cloud FITS byte range")
            output += block[relative:relative + take]
            self.offset += take
            size -= take
        return bytes(output)

    def readinto(self, buffer):
        value = self.read(len(buffer))
        buffer[:len(value)] = value
        return len(value)


def cloud_cutout(access_url: str, ra: float, dec: float, fov_deg: float) -> bytes:
    url = cloud_url_from_irsa(access_url)
    if not url:
        raise ValueError("Cloud cutout requires an official SPHEREx spectral image URL")
    if not all(np.isfinite([ra, dec, fov_deg])) or not (0 <= ra < 360 and -90 <= dec <= 90 and 0 < fov_deg <= 0.3):
        raise ValueError("Invalid cloud cutout position or field of view")
    with httpx.Client(timeout=httpx.Timeout(8.0, connect=5.0), follow_redirects=False) as client:
        reader = CloudRangeReader(client, url)
        with fits.open(reader, memmap=False) as source:
            image = source["IMAGE"]
            if image.shape is None or len(image.shape) != 2:
                raise ValueError("Cloud image is not a two-dimensional SPHEREx exposure")
            path_info = _SOURCE.fullmatch(urlsplit(access_url).path)
            if (str(image.header.get("OBSID", "")).strip() != path_info["observation"]
                    or str(image.header.get("DETECTOR", "")).strip() != path_info["detector"]):
                raise ValueError("Cloud FITS observation identity does not match its archive URL")
            # Cutout2D's section access avoids reading the entire detector plane.
            cutout = Cutout2D(image.section, SkyCoord(ra * u.deg, dec * u.deg),
                              fov_deg * u.deg, wcs=WCS(image.header), mode="trim")
            sy, sx = cutout.slices_original
            if not cutout.data.size:
                raise ValueError("The requested position does not overlap the cloud image")
            output = [fits.PrimaryHDU(header=source[0].header.copy())]
            for name in ("IMAGE", "FLAGS", "VARIANCE", "ZODI"):
                if name not in source:
                    if name != "ZODI":
                        raise ValueError(f"Cloud image lacks the required {name} extension")
                    continue
                hdu = source[name]
                if hdu.shape != image.shape:
                    raise ValueError(f"Cloud {name} plane does not match the image")
                header = hdu.header.copy()
                # Parent checksums describe the uncropped detector plane and
                # must not be carried over as checksums of this cutout.
                for key in ("CHECKSUM", "DATASUM"):
                    if key in header:
                        del header[key]
                # Preserve the complete original WCS, including SIP and both
                # detector and WCS-WAVE alternate coordinate references.
                for axis, offset in ((1, sx.start), (2, sy.start)):
                    for suffix in ("", "A", "W"):
                        key = f"CRPIX{axis}{suffix}"
                        if key in header:
                            header[key] -= offset
                pixels = np.array(cutout.data if name == "IMAGE" else hdu.section[sy, sx], copy=True)
                output.append(fits.ImageHDU(data=pixels, header=header, name=name))
            # Preserve the ePSF and wavelength lookup products without changes.
            for name in ("EPSF", "WCS-WAVE"):
                if name in source:
                    output.append(source[name].copy())
            buffer = io.BytesIO()
            fits.HDUList(output).writeto(buffer, output_verify="exception")
            return buffer.getvalue()
