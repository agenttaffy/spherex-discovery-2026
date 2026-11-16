"""Atomically refresh the five-coordinate DR1 cube preview from pinned FITS products."""

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

import httpx
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits

from cube_audit_ranges import ArchiveTile, prime_tiles

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import CACHE_DIR
from app.science.spectral_cube import sample_channel_map, sample_cube
from app.services.cube_preview import (
    PREVIEW_FILE, SOURCE_PINS, canonical_json, channel_digest, read_preview, require,
)
from app.services.cube_service import HEALPIX


def verify_local(path: Path, source: dict) -> None:
    require(path.stat().st_size == source["bytes"], f"Incomplete source FITS: {path}")
    with path.open("rb") as handle:
        algorithm = "sha256" if source["sha256"] else "md5"
        expected = source["sha256"] or source["etag_md5"]
        require(hashlib.file_digest(handle, algorithm).hexdigest() == expected, f"Source checksum mismatch: {path}")


def extract(pin: dict, cube: fits.HDUList, position: SkyCoord) -> dict:
    source = pin["source"]
    require(cube[0].header["DATE-BEG"] == source["date_beg"] and cube[0].header["DATE-END"] == source["date_end"],
            f"FITS observation window changed for {pin['id']}")
    spectrum = sample_cube(cube, position)
    require(spectrum["pixel"] == pin["pixel"], f"Native pixel mismatch for {pin['id']}")
    require(channel_digest(spectrum["channels"]) == pin["channels_sha256"],
            f"FITS channel audit mismatch for {pin['id']}")
    x, y = spectrum["pixel"]["x"], spectrum["pixel"]["y"]
    maps = {}
    for number in range(1, 103):
        window = sample_channel_map(cube, x, y, number)
        index = (number - 1, slice(y - 12, y + 13), slice(x - 12, x + 13))
        image = cube["IMAGE"].section[index]
        hits = cube["NHITS"].section[index]
        flags = cube["FLAGS"].section[index].astype(np.uint32)
        valid = np.isfinite(image) & (hits > 0) & ((flags & 0xFFDFFFFF) == 0)
        if number in (51, 52):
            valid[:] = False
        expected = np.where(valid, image.astype(float), np.nan)
        actual = np.array(window["pixels"], dtype=float)
        require(np.array_equal(actual, expected, equal_nan=True), f"Native map mismatch for {pin['id']} channel {number}")
        maps[str(number)] = window
    return {**{field: pin[field] for field in ("ra", "dec", "tile", "pixel", "source")},
            "channels": spectrum["channels"], "maps": maps}


def atomic_publish(document: dict, output: Path, pins_path: Path = SOURCE_PINS) -> None:
    temporary = None
    try:
        with NamedTemporaryFile(dir=output.parent, suffix=".pending", delete=False) as file:
            temporary = Path(file.name)
            file.write(gzip.compress(canonical_json(document), compresslevel=6, mtime=0))
            file.flush()
            os.fsync(file.fileno())
        read_preview(temporary, pins_path)
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PREVIEW_FILE)
    parser.add_argument("--generated-on", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--archive-ranges", action="store_true", help="Read pinned public mirror ranges for missing tiles.")
    args = parser.parse_args()
    pins = json.loads(SOURCE_PINS.read_text(encoding="utf-8"))
    with ExitStack() as stack:
        client = stack.enter_context(httpx.Client(timeout=25, limits=httpx.Limits(max_connections=24,
                                                   max_keepalive_connections=24)))
        archives, local, positions, samples = {}, {}, {}, {}
        for pin in pins:
            tile, source = pin["tile"], pin["source"]
            position = SkyCoord(pin["ra"], pin["dec"], unit="deg")
            require(int(HEALPIX.skycoord_to_healpix(position)) == tile, f"Unexpected HPX tile for {pin['id']}")
            positions[tile] = [position]
            name = hashlib.sha256(source["fits_url"].encode()).hexdigest() + ".fits"
            candidates = (CACHE_DIR / "dr1_cube" / name, CACHE_DIR / "cube_coverage" / "dr1_cube" / name)
            found = next((path for path in candidates if path.is_file()), None)
            if found is not None:
                verify_local(found, source)
                local[tile] = found
            elif args.archive_ranges:
                archive = ArchiveTile(client, source["fits_url"])
                require(archive.etag.strip('"') == source["etag_md5"] and archive.length == source["bytes"],
                        f"Archive product identity changed for tile {tile}")
                archives[tile] = archive
            else:
                raise FileNotFoundError(f"Need pinned FITS tile {tile}; stage it or use --archive-ranges")
        print(f"Reading {len(local)} verified full tile(s) and {len(archives)} pinned range tile(s)", flush=True)
        prime_tiles(archives, positions, range(1, 103))
        for pin in pins:
            tile = pin["tile"]
            with fits.open(local[tile] if tile in local else archives[tile].reader(), memmap=tile in local) as cube:
                samples[pin["id"]] = extract(pin, cube, positions[tile][0])
            print(f"Verified 102 spectrum slots and maps for {pin['id']} (tile {tile})", flush=True)
        atomic_publish({"schema": 1, "generated_on": args.generated_on, "samples": samples}, args.output)
        print(f"Published verified preview locally: {args.output.stat().st_size} bytes")


if __name__ == "__main__":
    main()
