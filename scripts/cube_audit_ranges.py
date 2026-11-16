"""Strict FITS range reader used only for the DR1 coverage audit."""

from bisect import bisect_right, insort
from concurrent.futures import ThreadPoolExecutor
import io
import re
from threading import Lock

import httpx
from astropy.io import fits
from astropy.wcs import WCS


class ArchiveTile:
    def __init__(self, client: httpx.Client, canonical_url: str):
        self.client = client
        self.url = canonical_url.replace("irsa.ipac.caltech.edu/ibe/data/spherex",
                                         "nasa-irsa-spherex.s3.amazonaws.com")
        self.etag = None
        self.length = None
        self.starts = []
        self.chunks = {}
        self.lock = Lock()
        self.read(0, 2880)

    def read(self, start: int, size: int) -> bytes:
        if self.length is not None:
            size = min(size, max(0, self.length - start))
        if size == 0:
            return b""
        with self.lock:
            index = bisect_right(self.starts, start) - 1
            if index >= 0:
                cached_start = self.starts[index]
                cached = self.chunks[cached_start]
                relative = start - cached_start
                if relative + size <= len(cached):
                    return cached[relative:relative + size]
        end = start + size - 1
        for attempt in range(3):
            try:
                response = self.client.get(self.url, headers={"Range": f"bytes={start}-{end}",
                                                             "Accept-Encoding": "identity"})
                response.raise_for_status()
                match = re.fullmatch(rf"bytes {start}-{end}/(\d+)", response.headers.get("Content-Range", ""))
                etag = response.headers.get("ETag")
                if response.status_code != 206 or not match or not etag or len(response.content) != size:
                    raise ValueError(f"Invalid FITS range {start}-{end} from {self.url}")
                with self.lock:
                    if self.etag is None:
                        self.etag, self.length = etag, int(match[1])
                    if (etag, int(match[1])) != (self.etag, self.length):
                        raise ValueError(f"FITS object changed during retrieval: {self.url}")
                    if start not in self.chunks:
                        insort(self.starts, start)
                    if len(self.chunks.get(start, b"")) < size:
                        self.chunks[start] = response.content
                return response.content
            except httpx.HTTPError:
                if attempt == 2:
                    raise
        raise RuntimeError("FITS range retrieval did not complete")

    def reader(self):
        return TileReader(self)

    def known_sample_ranges(self, positions, map_channels=(1, 3)):
        """Prepare native spectrum samples and the requested channel-map windows."""
        with fits.open(self.reader(), memmap=False) as cube:
            sky = WCS(cube["IMAGE"].header, fobj=cube, naxis=[1, 2])
            by_position = [tuple(int(p + .5) for p in sky.world_to_pixel(pos)) for pos in positions]
            for name in ("IMAGE", "NHITS", "FLAGS"):
                hdu = cube[name]
                channels, height, width = hdu.shape
                assert channels == 102 and all(0 <= x < width and 0 <= y < height for x, y in by_position)
                assert abs(hdu.header["BITPIX"]) == 32 and "BZERO" not in hdu.header and "BSCALE" not in hdu.header
                start = hdu.fileinfo()["datLoc"]
                # Each plane uses one span from the lowest to highest requested sample.
                # The two displayed map planes additionally need a ±12 pixel window.
                offsets = [y * width + x for x, y in by_position]
                for channel in range(channels):
                    low, high = min(offsets), max(offsets)
                    if channel + 1 in map_channels:
                        low = min(max(0, y - 12) * width + max(0, x - 12) for x, y in by_position)
                        high = max(min(height - 1, y + 12) * width + min(width - 1, x + 12)
                                   for x, y in by_position)
                    yield start + 4 * (channel * height * width + low), 4 * (high - low + 1)


class TileReader(io.RawIOBase):
    def __init__(self, tile: ArchiveTile):
        self.tile = tile
        self.offset = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def seek(self, offset, whence=io.SEEK_SET):
        reference = {io.SEEK_SET: 0, io.SEEK_CUR: self.offset, io.SEEK_END: self.tile.length}
        position = reference[whence] + offset
        if position < 0:
            raise ValueError("Cannot seek before the FITS file")
        self.offset = position
        return self.offset

    def tell(self):
        return self.offset

    def read(self, size=-1):
        if size < 0:
            size = self.tile.length - self.offset
        result = self.tile.read(self.offset, size)
        self.offset += len(result)
        return result

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)


def prime_tiles(tiles, positions, map_channels=(1, 3)):
    with ThreadPoolExecutor(max_workers=24) as pool:
        tasks = [(tile, start, size) for index, tile in tiles.items()
                 for start, size in tile.known_sample_ranges(positions[index], map_channels)]
        for _ in pool.map(lambda args: args[0].read(*args[1:]), tasks):
            pass
