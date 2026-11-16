#!/usr/bin/env python3
"""Build and audit a candidate demo cache in a new directory."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from audit_demo_manifest import audit_manifest
from app.config import CACHE_DIR, MANIFESTS_DIR
from app.science.fits_processing import calculate_pixel_stats, extract_primary_image, load_fits_cutout


def probe_entries(probe: dict):
    for target, group in probe.items():
        ra, dec = group["ra"], group["dec"]
        for collection, found in group["collections"].items():
            for observation in found.get("sample_observations", [])[:2]:
                url = observation.get("access_url")
                if url:
                    yield {
                        "target_name": target,
                        "ra": ra, "dec": dec,
                        "collection": collection,
                        "obs_id": observation["obs_id"],
                        "detector": observation["detector"],
                        "cutout_url": f"{url}?center={ra:.6f},{dec:.6f}&size=0.0350",
                    }


def evidence_entries(evidence: list):
    for row in evidence:
        if not row.get("cutout_url"):
            print(f"{row['target']} / {row['release']}: unavailable ({row.get('errors', [])})")
            continue
        ra, dec = row["requested_degrees"]
        yield {
            "target_name": row["target"],
            "collection": f"spherex_{row['release']}",
            "ra": ra, "dec": dec,
            "obs_id": row["obs_id"],
            "detector": f"SPHEREx-D{row['detector']}",
            "cutout_url": row["cutout_url"],
            "predicted_degrees": row["predicted_degrees"],
        }


def verified_entry(entry: dict, content: bytes) -> dict:
    with load_fits_cutout(content) as cutout:
        header = cutout["IMAGE"].header
        if header["OBSID"] != entry["obs_id"] or f"SPHEREx-D{header['DETECTOR']}" != entry["detector"]:
            raise ValueError("FITS identity differs from the archive record")
        pixels, _ = extract_primary_image(cutout)
        predicted = entry.get("predicted_degrees")
        record = {
            **entry,
            "utc_date": header["DATE-OBS"],
            "dimensions": list(pixels.shape),
            "pixel_stats": calculate_pixel_stats(pixels),
        }
        if predicted is not None:
            sky = SkyCoord(predicted[0] * u.deg, predicted[1] * u.deg, frame="icrs")
            x, y = WCS(header).celestial.world_to_pixel(sky)
            height, width = pixels.shape
            if not (-0.5 <= x < width - 0.5 and -0.5 <= y < height - 0.5):
                raise ValueError("Epoch-corrected candidate lies outside the FITS cutout")
            record["catalog_coverage"] = "inside"
        return record


def fetch_candidate(client: httpx.Client, entry: dict, source: Path) -> tuple[str, bytes]:
    url = entry["cutout_url"]
    path = urlsplit(url)
    coords = f"{entry['ra']:.6f},{entry['dec']:.6f}"
    if (path.scheme != "https" or path.netloc != "irsa.ipac.caltech.edu"
            or not path.path.startswith("/ibe/data/spherex/") or not path.path.endswith(".fits")
            or parse_qs(path.query).get("center") != [coords]):
        raise ValueError("Expected an IRSA spectral-image cutout URL for the manifest coordinates")
    name = hashlib.sha256(url.encode()).hexdigest() + ".fits"
    for directory in dict.fromkeys((source, CACHE_DIR)):
        cached = directory / name
        if cached.is_file():
            return name, cached.read_bytes()
    with client.stream("GET", url) as response:
        response.raise_for_status()
        content = bytearray()
        for chunk in response.iter_bytes():
            content.extend(chunk)
            if len(content) > 25_000_000:
                raise ValueError("Cutout exceeds the 25 MB staging limit")
    return name, bytes(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument("--probe", type=Path, default=MANIFESTS_DIR / "probe_results.json")
    sources.add_argument("--evidence", type=Path, help="Use cutouts verified against epoch-corrected catalog positions")
    parser.add_argument("--source-cache", type=Path, default=CACHE_DIR)
    parser.add_argument("--stage-dir", type=Path, default=CACHE_DIR / "demo_refresh")
    args = parser.parse_args()

    source_path = args.evidence or args.probe
    try:
        content = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        parser.error(f"Could not read candidate inputs from {source_path}: {error}")
    entries = evidence_entries(content) if args.evidence else probe_entries(content)
    stage = args.stage_dir.resolve()
    try:
        stage.mkdir(parents=True, exist_ok=False)
    except OSError as error:
        parser.error(f"Use a new staging directory: {error}")
    manifest = []
    with httpx.Client(timeout=30) as client:
        for entry in entries:
            try:
                filename, data = fetch_candidate(client, entry, args.source_cache)
                record = verified_entry(entry, data)
                (stage / filename).write_bytes(data)
                manifest.append(record)
            except (OSError, ValueError, KeyError, httpx.HTTPError) as error:
                print(f"{entry['target_name']} / {entry['obs_id']}: {error}")

    manifest_path = stage / "demo_dataset.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report = audit_manifest(manifest_path=manifest_path, cache_dir=stage, strict_warnings=True)
    report_path = stage / "audit.json"
    report_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    print(f"Staged {len(manifest)} files at {stage}. Audit report: {report_path}")
    return int(report.overall_status != "PASS")


if __name__ == "__main__":
    sys.exit(main())
