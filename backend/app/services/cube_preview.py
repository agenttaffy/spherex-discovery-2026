"""Verified compact DR1 samples for the five staged demo coordinates."""

from datetime import date
from functools import lru_cache
import gzip
import hashlib
import json
from math import isfinite
from pathlib import Path

from app.config import MANIFESTS_DIR

SOURCE_PINS = MANIFESTS_DIR / "cube_preview_sources.json"
PREVIEW_FILE = MANIFESTS_DIR / "cube_preview.json.gz"
COORDINATE_TOLERANCE_DEG = 0.000005
PIXEL_MAP_SIZE = 25
MAX_JSON_BYTES = 16_000_000
STATUSES = frozenset({"measured", "no_coverage", "flagged", "blank_channel", "missing_wavelength"})
SAMPLE_DESCRIPTION = {
    "sample_kind": "coadded_dr1_sky_pixel",
    "observation_epoch": None,
    "source_association": "unconfirmed",
}


def canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def channel_digest(channels: list) -> str:
    return hashlib.sha256(canonical_json(channels)).hexdigest()


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def validate_preview(document: dict, pins: list) -> None:
    require(document["schema"] == 1, "Unexpected cube preview schema")
    date.fromisoformat(document["generated_on"])
    samples = document["samples"]
    expected = {pin["id"]: pin for pin in pins}
    require(len(expected) == 5 and set(samples) == set(expected), "Unexpected cube preview sample keys")
    for key, sample in samples.items():
        pin = expected[key]
        require(all(sample[field] == pin[field] for field in ("ra", "dec", "tile", "pixel", "source")),
                f"Cube preview provenance mismatch for {key}")
        channels = sample["channels"]
        require([row["channel"] for row in channels] == list(range(1, 103)), f"Invalid channel ordering for {key}")
        require(channel_digest(channels) == pin["channels_sha256"], f"Cube preview channel digest mismatch for {key}")
        require(set(sample["maps"]) == {str(i) for i in range(1, 103)}, f"Incomplete channel maps for {key}")
        for row in channels:
            channel = row["channel"]
            status = row["status"]
            brightness = row["surface_brightness_mjy_sr"]
            require(status in STATUSES and (brightness is not None) == (status == "measured"),
                    f"Invalid status/value for {key} channel {channel}")
            require((channel in (51, 52)) == (status == "blank_channel"),
                    f"Invalid DR1 blank slot for {key} channel {channel}")
            window = sample["maps"][str(channel)]
            pixels = window["pixels"]
            center = PIXEL_MAP_SIZE // 2
            require(window["channel"] == channel and (window["center_x"], window["center_y"]) == (center, center)
                    and len(pixels) == PIXEL_MAP_SIZE and all(len(line) == PIXEL_MAP_SIZE for line in pixels),
                    f"Invalid map size or center for {key} channel {channel}")
            require(all(value is None or (type(value) in (int, float) and isfinite(value))
                        for line in pixels for value in line), f"Invalid map pixels for {key} channel {channel}")
            if status != "missing_wavelength":
                require(pixels[center][center] == brightness, f"Map center disagrees for {key} channel {channel}")
            if status == "blank_channel":
                require(all(value is None for line in pixels for value in line), f"Nonempty blank channel for {key}")


def read_preview(path: Path, pins_path: Path = SOURCE_PINS) -> dict:
    with gzip.open(path, "rb") as handle:
        content = handle.read(MAX_JSON_BYTES + 1)
    require(len(content) <= MAX_JSON_BYTES, "Cube preview exceeds size limit")
    document = json.loads(content)
    validate_preview(document, json.loads(pins_path.read_text(encoding="utf-8")))
    return document


@lru_cache(maxsize=2)
def _load_revision(path: Path, modified_ns: int, size: int) -> dict:
    return read_preview(path)


def lookup_preview(ra: float, dec: float, channel: int | None, reason: str) -> dict | None:
    stat = PREVIEW_FILE.stat()
    document = _load_revision(PREVIEW_FILE, stat.st_mtime_ns, stat.st_size)
    matches = [
        (key, row) for key, row in document["samples"].items()
        if abs(ra - row["ra"]) <= COORDINATE_TOLERANCE_DEG
        and abs(dec - row["dec"]) <= COORDINATE_TOLERANCE_DEG
    ]
    if len(matches) != 1:
        return None
    key, row = matches[0]
    result = {
        **SAMPLE_DESCRIPTION,
        "source": "cached_dr1_preview",
        "collection": "spherex_dr1_cube",
        "tile": row["tile"],
        "fits_url": row["source"]["fits_url"],
        "ra": ra,
        "dec": dec,
        "pixel": row["pixel"],
        "channels": row["channels"],
        "preview": {
            "preset_id": key,
            "generated_on": document["generated_on"],
            "sample_coordinate": {"ra": row["ra"], "dec": row["dec"]},
            "coordinate_tolerance_deg": COORDINATE_TOLERANCE_DEG,
            "archive_failure": reason,
            "provenance": row["source"],
        },
    }
    if channel is not None:
        result["channel_map"] = row["maps"][str(channel)]
    return result
