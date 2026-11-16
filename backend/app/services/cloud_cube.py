"""Bounded, version-consistent byte-range reads from IRSA's public S3 cube mirror."""

from bisect import bisect_right, insort
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import io
import math
import re
import time
from threading import Lock
from urllib.parse import urlsplit

import httpx
from astropy.io import fits
from astropy.wcs import WCS

from app.science.spectral_cube import CubeCoverageError, sample_channel_map, sample_cube

_PATH = re.compile(r"/ibe/data/spherex/dr1/hips5_cube/hips_[0-9]{8}/Norder5/Dir[0-9]+/Npix[0-9]+_cube\.fits")
MAX_OBJECT_BYTES = 350_000_000
MAX_TRANSFER_BYTES = 16_000_000
MAX_CACHED_RANGE_BYTES = 16_000_000
MAX_REQUEST_SECONDS = 35.0
_range_cache = OrderedDict()
_range_cache_lock = Lock()


class CloudCube:
    def __init__(self, client: httpx.Client, irsa_url: str):
        parts = urlsplit(irsa_url)
        if (parts.scheme != "https" or parts.netloc != "irsa.ipac.caltech.edu"
                or parts.query or parts.fragment or not _PATH.fullmatch(parts.path)):
            raise ValueError("Unrecognized IRSA cube URL")
        self.url = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com" + parts.path.removeprefix("/ibe/data/spherex")
        self.client = client
        self.etag = None
        self.length = None
        self.bytes_read = 0
        self.started = time.monotonic()
        self.starts = []
        self.chunks = {}
        self.lock = Lock()
        self.read(0, 2880)
        # Revalidate the object identity before reusing prior channel samples.
        with _range_cache_lock:
            entry = _range_cache.get(self.url)
            if entry and entry[0:2] == (self.etag, self.length):
                self.starts = list(entry[2])
                self.chunks = dict(entry[3])
                _range_cache.move_to_end(self.url)

    def remember(self):
        with self.lock:
            starts, chunks = list(self.starts), dict(self.chunks)
        if sum(map(len, chunks.values())) > MAX_CACHED_RANGE_BYTES:
            return
        with _range_cache_lock:
            _range_cache[self.url] = (self.etag, self.length, starts, chunks)
            _range_cache.move_to_end(self.url)
            while sum(sum(map(len, entry[3].values())) for entry in _range_cache.values()) > MAX_CACHED_RANGE_BYTES:
                _range_cache.popitem(last=False)

    def read(self, start: int, size: int) -> bytes:
        if time.monotonic() - self.started > MAX_REQUEST_SECONDS:
            raise ValueError("Cloud cube read exceeded its time limit")
        if start < 0 or size < 0 or size > MAX_TRANSFER_BYTES:
            raise ValueError("Invalid cloud FITS byte range")
        if self.length is not None:
            size = min(size, max(0, self.length - start))
        if not size:
            return b""
        with self.lock:
            index = bisect_right(self.starts, start) - 1
            if index >= 0:
                base = self.starts[index]
                chunk = self.chunks[base]
                offset = start - base
                if offset + size <= len(chunk):
                    return chunk[offset:offset + size]
            etag = self.etag
        end = start + size - 1
        headers = {"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"}
        if etag:
            headers["If-Match"] = etag
        for attempt in range(2):
            try:
                with self.client.stream("GET", self.url, headers=headers) as response:
                    if response.status_code in (429, 502, 503, 504) and not attempt:
                        pass
                    else:
                        response.raise_for_status()
                        match = re.fullmatch(rf"bytes {start}-{end}/(\d+)", response.headers.get("Content-Range", ""))
                        received_etag = response.headers.get("ETag")
                        if response.status_code != 206 or not match or not received_etag:
                            raise ValueError("Cloud cube returned an invalid byte range")
                        length = int(match[1])
                        if length <= 0 or length > MAX_OBJECT_BYTES or length % 2880:
                            raise ValueError("Cloud cube has an unexpected object size")
                        data = bytearray()
                        for chunk in response.iter_bytes(chunk_size=min(65536, size)):
                            data.extend(chunk)
                            if len(data) > size:
                                raise ValueError("Cloud cube returned more bytes than requested")
                            if time.monotonic() - self.started > MAX_REQUEST_SECONDS:
                                raise ValueError("Cloud cube read exceeded its time limit")
                        if len(data) != size:
                            raise ValueError("Cloud cube returned an invalid byte range")
                        break
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt:
                    raise
            time.sleep(.25)
        data = bytes(data)
        with self.lock:
            if self.etag is None:
                self.etag, self.length = received_etag, length
            if (self.etag, self.length) != (received_etag, length):
                raise ValueError("Cloud cube changed while being read")
            self.bytes_read += size
            if self.bytes_read > MAX_TRANSFER_BYTES:
                raise ValueError("Cloud cube request exceeded its transfer limit")
            if start not in self.chunks:
                insort(self.starts, start)
            if len(self.chunks.get(start, b"")) < size:
                self.chunks[start] = data
        return data

    def reader(self):
        return CloudCubeReader(self)


class CloudCubeReader(io.RawIOBase):
    def __init__(self, tile: CloudCube):
        self.tile, self.offset = tile, 0

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.offset

    def seek(self, offset, whence=io.SEEK_SET):
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.offset, io.SEEK_END: self.tile.length}[whence]
        self.offset = base + offset
        if self.offset < 0:
            raise ValueError("Cannot seek before the FITS object")
        return self.offset

    def read(self, size=-1):
        if size < 0:
            size = self.tile.length - self.offset
        data = self.tile.read(self.offset, size)
        self.offset += len(data)
        return data

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)


def sample_cloud_cube(client: httpx.Client, url: str, position, channel: int | None) -> tuple[dict, dict]:
    """Read only native spectrum pixels and one small map, never the full FITS tile."""
    remote = CloudCube(client, url)
    ranges = []
    with fits.open(remote.reader(), memmap=False) as cube:
        wcs = WCS(cube["IMAGE"].header, fobj=cube, naxis=[1, 2])
        px, py = wcs.world_to_pixel(position)
        if not (float('-inf') < px < float('inf') and float('-inf') < py < float('inf')):
            raise CubeCoverageError("Position could not be projected into this HPX tile")
        x, y = math.floor(float(px) + .5), math.floor(float(py) + .5)
        for name in ("IMAGE", "NHITS", "FLAGS"):
            hdu = cube[name]
            channels, height, width = hdu.shape
            if channels != 102 or not (0 <= x < width and 0 <= y < height):
                raise CubeCoverageError("Position falls outside this HPX tile")
            if hdu.header["BITPIX"] != -32 and not (name != "IMAGE" and hdu.header["BITPIX"] == 32):
                raise ValueError("Unexpected cloud cube data representation")
            if "BZERO" in hdu.header or "BSCALE" in hdu.header:
                raise ValueError("Scaled cloud cube planes are not supported")
            offset = hdu.fileinfo()["datLoc"]
            for index in range(channels):
                low = high = y * width + x
                if channel == index + 1:
                    low = max(0, y - 12) * width + max(0, x - 12)
                    high = min(height - 1, y + 12) * width + min(width - 1, x + 12)
                ranges.append((offset + 4 * (index * height * width + low), 4 * (high - low + 1)))
    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(lambda item: remote.read(*item), ranges))
    with fits.open(remote.reader(), memmap=False) as cube:
        result = sample_cube(cube, position)
        if channel is not None:
            result["channel_map"] = sample_channel_map(cube, result["pixel"]["x"], result["pixel"]["y"], channel)
    remote.remember()
    return result, {"cloud_url": remote.url, "etag": remote.etag, "bytes_transferred": remote.bytes_read}
