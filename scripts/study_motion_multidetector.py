"""Bounded metadata selection and strict calibrated inspection for D1–D6 motion pairs."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from dataclasses import asdict
import hashlib
import io
import json
import re
from pathlib import Path

import httpx
import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.coordinates import SkyCoord

from study_motion_preflight import (
    BASELINE_DAYS, CACHE, ROOT, SOURCES, WAVE_ID, WAVE_MD5,
    apparent_position, assess_pair, footprint_pixel,
)
from app.science.fits_processing import SPHEREX_INFORMATIONAL_FLAG_NAMES, extract_astropy_wcs, parse_spherex_mask_planes
from app.science.spectral_calibration import spectral_calibration_plane_id
from app.services.spectral_calibration_service import find_calibration_artifact
from app.science.calibrated_comparison import prepare_calibrated_exposure

WORK = CACHE.parent / "motion_multidetector"
DETECTORS = tuple(f"SPHEREx-D{i}" for i in range(1, 7))
MAX_PAIRS_PER_DETECTOR = 3


def refresh_metadata(client, catalog, existing):
    def query(previous):
        target, release = previous["target"], previous["release"]
        sky = apparent_position(target, Time(2026., format="jyear"), catalog)
        params = dict(COLLECTION=release, POS=f"circle {sky.ra.deg:.8f} {sky.dec.deg:.8f} 0.012",
                      RESPONSEFORMAT="CSV", MAXREC=3000)
        url = str(client.build_request("GET", "https://irsa.ipac.caltech.edu/SIA", params=params).url)
        result = dict(target=target, release=release, url=url, rows=[])
        try:
            response = client.get(url)
            result["http"] = response.status_code
            response.raise_for_status()
            reader = csv.DictReader(response.text.lstrip("\ufeff").splitlines())
            columns = ("obs_id", "energy_bandpassname", "t_min", "t_max", "access_url", "s_ra", "s_dec", "s_region")
            if not set(columns).issubset(reader.fieldnames or ()):
                raise ValueError("Unexpected SIA CSV columns")
            result["rows"] = [{k: row[k] for k in columns} for row in reader
                              if row["energy_bandpassname"] in DETECTORS and row["access_url"]]
        except (ValueError, httpx.HTTPError) as exc:
            result["error"] = str(exc)
        return result

    with ThreadPoolExecutor(max_workers=5) as pool:
        return list(pool.map(query, existing))


def footprint_coordinates(region, ra, dec):
    """Approximate fractional position in a SIA quadrilateral, for ranking only."""
    if not region or not region.startswith("POLYGON ICRS "):
        return None
    vertices = np.fromstring(region.removeprefix("POLYGON ICRS "), sep=" ")
    if vertices.size < 8 or vertices.size % 2:
        return None
    v = vertices.reshape(-1, 2)[:4]
    x = ((v[:, 0] - ra + 180) % 360 - 180) * np.cos(np.deg2rad(dec))
    y = v[:, 1] - dec
    points = np.column_stack((x, y))
    matrix = np.column_stack((points[1] - points[0], points[3] - points[0]))
    if abs(np.linalg.det(matrix)) < 1e-9:
        return None
    uv = np.linalg.solve(matrix, -points[0])
    return uv if np.all((uv >= .015) & (uv <= .985)) else None


def select_pairs(queries, catalog):
    grouped = {}
    for query in queries:
        for row in query["rows"]:
            detector = row["energy_bandpassname"]
            if detector not in DETECTORS:
                continue
            key = (query["target"], detector)
            grouped.setdefault(key, {}).setdefault(
                row["obs_id"], dict(row, target=query["target"], release=query["release"],
                                    midpoint=(float(row["t_min"]) + float(row["t_max"])) / 2))
    candidates = []
    for (target, detector), matches in grouped.items():
        rows = sorted(matches.values(), key=lambda r: r["midpoint"])
        sky = apparent_position(target, Time([r["midpoint"] for r in rows], format="mjd", scale="utc"), catalog)
        projected = [(r, footprint_coordinates(r["s_region"], c.ra.deg, c.dec.deg)) for r, c in zip(rows, sky)]
        visible = [(r, uv) for r, uv in projected if uv is not None]
        pairs = []
        for i, (a, uv_a) in enumerate(visible):
            for b, uv_b in visible[i + 1:]:
                days = b["midpoint"] - a["midpoint"]
                if BASELINE_DAYS <= days <= 550:
                    score = float(np.linalg.norm(uv_b - uv_a) + abs(days - 365.25) / 1000)
                    pairs.append((score, a["obs_id"], b["obs_id"], a, b))
        if pairs:
            score, _, _, a, b = min(pairs)
            candidates.append(dict(target=target, detector=detector, rank=score, endpoints=[a, b]))
    ranked = sorted(candidates, key=lambda r: (r["rank"], r["target"], r["detector"]))
    selected = []
    def add_first(predicate):
        for row in ranked:
            if (row not in selected and predicate(row)
                    and sum(p["detector"] == row["detector"] for p in selected) < MAX_PAIRS_PER_DETECTOR):
                selected.append(row)
                return
    for detector in DETECTORS:
        add_first(lambda r: r["detector"] == detector and r["target"] in SOURCES.values())
    for target in dict.fromkeys(q["target"] for q in queries):
        if all(row["target"] != target for row in selected):
            add_first(lambda r: r["target"] == target)
    for detector in DETECTORS:
        add_first(lambda r: r["detector"] == detector and r["target"] not in SOURCES.values())
        while sum(p["detector"] == detector for p in selected) < MAX_PAIRS_PER_DETECTOR:
            count = len(selected)
            add_first(lambda r: r["detector"] == detector)
            if len(selected) == count:
                break
    return selected, candidates


def fetch_science(client, row, catalog, *, sizes=("0.0350", "0.0250"), fixed_center=None):
    center = fixed_center
    if center is None:
        sky = apparent_position(row["target"], Time(row["midpoint"], format="mjd", scale="utc"), catalog)
        center = f"{sky.ra.deg:.7f},{sky.dec.deg:.7f}"
    attempts = []
    for size in sizes:
        params = {"center": center, "size": size}
        url = str(client.build_request("GET", row["access_url"], params=params).url)
        path = WORK / (hashlib.sha256(url.encode()).hexdigest() + ".fits")
        if path.is_file():
            return dict(row, file=path.name, attempts=attempts + [dict(url=url, status="cached")])
        try:
            response = client.get(url)
            attempts.append(dict(url=url, status=response.status_code))
            response.raise_for_status()
            with fits.open(io.BytesIO(response.content)) as science:
                hdr = science["IMAGE"].header
                if hdr["OBSID"] != row["obs_id"] or f"SPHEREx-D{hdr['DETECTOR']}" != row["energy_bandpassname"]:
                    raise ValueError("Wrong observation or detector in FITS")
            path.write_bytes(response.content)
            return dict(row, file=path.name, attempts=attempts)
        except (httpx.HTTPError, OSError, ValueError, KeyError) as exc:
            if not attempts or attempts[-1]["url"] != url:
                attempts.append(dict(url=url))
            attempts[-1]["error"] = str(exc)
    return dict(row, file=None, attempts=attempts)


def native_summary(hdul, row, catalog):
    image = hdul["IMAGE"]
    flags = hdul["FLAGS"]
    variance = hdul["VARIANCE"].data
    shape = image.data.shape
    if flags.data.shape != shape or variance.shape != shape:
        raise ValueError("Core mask and variance must match the science image")
    epoch = Time(image.header["MJD-AVG"], format="mjd", scale="utc")
    sky = apparent_position(row["target"], epoch, catalog)
    pixel = footprint_pixel(extract_astropy_wcs(image.header), shape, sky)
    summary = dict(target=row["target"], observation=row["obs_id"], release=row["release"],
                   detector=row["energy_bandpassname"], utc=epoch.isot, mjd=epoch.mjd,
                   predicted_deg=[sky.ra.deg, sky.dec.deg], pixel=pixel, core=None,
                   core_contained=False, passbands=None, plane_id=spectral_calibration_plane_id(hdul))
    if not pixel or not pixel["inside"]:
        return summary, None
    yy, xx = np.indices(shape)
    x, y = pixel["x"], pixel["y"]
    core = np.hypot(xx - x, yy - y) <= 2.5
    defs = parse_spherex_mask_planes(flags.header)
    if not defs or not np.issubdtype(flags.data.dtype, np.integer):
        raise ValueError("Usable pixels need documented integer quality flags")
    allowed = 0
    for flag in SPHEREX_INFORMATIONAL_FLAG_NAMES:
        allowed |= defs.get(flag, 0)
    ok = (np.isfinite(image.data) & np.isfinite(variance) & (variance > 0)
          & ((flags.data.astype(np.int64) & ~allowed) == 0))
    summary["core"] = [int((core & ok).sum()), int(core.sum())]
    summary["core_contained"] = min(x + .5, y + .5, shape[1] - x - .5, shape[0] - y - .5) >= 2.5
    return summary, core


def get_calibration(client, hdul, summary, artifacts):
    plane_id = summary["plane_id"]
    if plane_id == WAVE_ID and summary["detector"] == "SPHEREx-D6":
        return (ROOT / f"data/cache/spectral-{WAVE_MD5}.fits").read_bytes(), WAVE_MD5
    record = artifacts.get(plane_id)
    saved = WORK / "spectral-artifacts.csv"
    if (not record or record.get("error")) and saved.is_file():
        record = calibration_from_catalog(saved, summary) or record
        if record and not record.get("error"):
            artifacts[plane_id] = record
    if record is None and client is not None:
        try:
            record = asdict(find_calibration_artifact(client, hdul, summary["release"].removeprefix("spherex_")))
        except (httpx.HTTPError, ValueError) as exc:
            record = dict(error=str(exc))
        artifacts[plane_id] = record
    if not record or record.get("error"):
        raise ValueError((record or {}).get("error", "No independently identified calibration artifact"))
    path = WORK / f"spectral-{record['checksum']}.fits"
    if not path.is_file() and client is not None:
        response = client.get(record["url"], timeout=40)
        response.raise_for_status()
        if hashlib.md5(response.content).hexdigest() != record["checksum"]:
            raise ValueError("Downloaded spectral calibration checksum mismatch")
        path.write_bytes(response.content)
    return path.read_bytes(), record["checksum"]


def calibration_from_catalog(path, summary):
    detector = summary["detector"].removeprefix("SPHEREx-D")
    release = summary["release"].removeprefix("spherex_")
    choices = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row.get("planeid") != summary["plane_id"]:
                continue
            uri = (row.get("uri") or "").removeprefix("https://irsa.ipac.caltech.edu").lstrip("/")
            match = re.fullmatch(rf"ibe/data/spherex/(dr1|qr3)/spectral_wcs/[\w.-]+/{detector}/[\w.-]+\.fits", uri)
            md5 = (row.get("contentchecksum") or "").strip().lower().removeprefix("md5:")
            if match and re.fullmatch(r"[0-9a-f]{32}", md5):
                choices.add((match[1], uri, md5))
    accepted = {row for row in choices if row[0] == release} or choices
    if len(accepted) != 1:
        return None
    _, uri, md5 = accepted.pop()
    return dict(plane_id=summary["plane_id"], url=f"https://irsa.ipac.caltech.edu/{uri}", checksum=md5)


def inspect(row, catalog, client, artifacts):
    if row.get("file") is None:
        return dict(observation=row["obs_id"], release=row["release"], detector=row["energy_bandpassname"],
                    archive_attempts=row["attempts"], error="FITS unavailable"), None
    with fits.open(WORK / row["file"], memmap=False) as hdul:
        summary, core = native_summary(hdul, row, catalog)
        summary["archive_attempts"] = row["attempts"]
        summary["fits_sha256"] = hashlib.sha256((WORK / row["file"]).read_bytes()).hexdigest()
        try:
            raw, checksum = get_calibration(client, hdul, summary, artifacts)
            exposure = prepare_calibrated_exposure(hdul, raw, plane_id=summary["plane_id"], checksum=checksum)
        except (ValueError, OSError, httpx.HTTPError) as exc:
            return dict(summary, calibration_error=str(exc)), None
        summary["calibration_md5"] = checksum
        if core is not None:
            wave, band = exposure.wavelength[core], exposure.bandwidth[core]
            intervals = np.column_stack((wave - band / 2, wave + band / 2))
            if np.isfinite(intervals).all() and intervals.size:
                summary["passbands"] = intervals.tolist()
            summary["core"][0] = int((core & exposure.usable()).sum())
        return summary, exposure


def evaluate(a, b):
    if a[1] is not None and b[1] is not None:
        return assess_pair(a, b)
    f1, f2 = a[0], b[0]
    reasons = []
    if any(f.get("error") for f in (f1, f2)):
        reasons.append("archive FITS unavailable")
    if any(f.get("calibration_error") for f in (f1, f2)):
        reasons.append("release/detector spectral calibration unverified")
    if any(f.get("pixel") is not None and not f["pixel"]["inside"] for f in (f1, f2)):
        reasons.append("prediction outside FITS coverage")
    if any(f.get("core") and (not f["core_contained"] or f["core"][0] != f["core"][1]) for f in (f1, f2)):
        reasons.append("masked or clipped source core")
    baseline, expected = None, None
    if "mjd" in f1 and "mjd" in f2:
        baseline = f2["mjd"] - f1["mjd"]
        expected = SkyCoord(*f1["predicted_deg"], unit="deg").separation(
            SkyCoord(*f2["predicted_deg"], unit="deg")).arcsec
    return dict(observations=[f["observation"] for f in (f1, f2)], baseline_days=baseline,
                expected_displacement_arcsec=expected,
                source_core_overlap=None, aligned_field_pixels=None, rejection_reasons=reasons,
                observed_centroid_displacement=None, observed_uncertainty=None, stationary_control=None,
                validated_motion=False)


def alignment_distances(a, b):
    """Diagnose a failed nearest-native-pixel gate without changing it."""
    if a is None or b is None:
        return None
    yy, xx = np.indices(a.image.shape)
    px, py = b.wcs.world_to_pixel(a.wcs.pixel_to_world(xx, yy))
    h, w = b.image.shape
    common = (px >= -.5) & (px < w - .5) & (py >= -.5) & (py < h - .5)
    distance = np.hypot(px[common] - np.floor(px[common] + .5), py[common] - np.floor(py[common] + .5))
    if not distance.size:
        return dict(common=0, within_half_pixel=0)
    return dict(common=distance.size, within_half_pixel=int((distance <= .5).sum()),
                minimum_pixels=float(distance.min()), maximum_pixels=float(distance.max()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="Fetch selected cutouts and missing calibrated maps.")
    parser.add_argument("--refresh-sia", action="store_true", help="Refresh the saved bounded metadata queries only.")
    parser.add_argument("--calibrate", action="store_true", help="Resolve or fetch calibration for the saved cutouts.")
    parser.add_argument("--wide-wise", action="store_true", help="Also test two wider cutouts of the selected WISE pair.")
    args = parser.parse_args()
    catalog = json.loads((WORK / "catalog.json").read_text())
    queries = json.loads((WORK / "sia.json").read_text())
    if args.refresh_sia:
        with httpx.Client(timeout=16) as client:
            queries = refresh_metadata(client, catalog, queries)
        (WORK / "sia.json").write_text(json.dumps(queries, indent=2))
        return
    selected, candidates = select_pairs(queries, catalog)
    (WORK / "selection.json").write_text(json.dumps(dict(selected=selected, candidates=candidates), indent=2))
    archive_path = WORK / "cutouts.json"
    cal_path = WORK / "calibration_artifacts.json"
    artifacts = json.loads(cal_path.read_text()) if cal_path.is_file() else {}
    if args.calibrate:
        artifacts = {key: value for key, value in artifacts.items() if not value.get("error")}
    with httpx.Client(timeout=15) as client:
        if args.fetch:
            rows = [row for pair in selected for row in pair["endpoints"]]
            with ThreadPoolExecutor(max_workers=5) as pool:
                archive = list(pool.map(lambda r: fetch_science(client, r, catalog), rows))
            archive_path.write_text(json.dumps(archive, indent=2))
        else:
            archive = json.loads(archive_path.read_text())
        expected = [(r["target"], r["obs_id"], r["energy_bandpassname"])
                    for p in selected for r in p["endpoints"]]
        if expected != [(r["target"], r["obs_id"], r["energy_bandpassname"]) for r in archive]:
            raise ValueError("Saved cutouts differ from the preserved metadata selection. Run --fetch.")
        results = []
        for i, pair in enumerate(selected):
            record = [inspect(row, catalog, client if args.fetch or args.calibrate else None, artifacts)
                      for row in archive[2*i:2*i+2]]
            if all("mjd" in r[0] for r in record):
                record.sort(key=lambda r: r[0]["mjd"])
            a, b = record
            results.append(dict(target=pair["target"], detector=pair["detector"], endpoints=[a[0], b[0]],
                                comparison=evaluate(a, b)))
        if args.wide_wise:
            pair = next(p for p in selected if p["target"] == "wise_0855" and p["detector"] == "SPHEREx-D6")
            wide = [fetch_science(client, row, catalog, sizes=("0.12",), fixed_center="133.7600,-7.24220")
                    for row in pair["endpoints"]]
            a, b = (inspect(row, catalog, None, artifacts) for row in wide)
            wide_result = dict(frames=[a[0], b[0]], comparison=evaluate(a, b),
                               alignment_distances=alignment_distances(a[1], b[1]))
            (WORK / "wise-wide-check.json").write_text(json.dumps(wide_result, indent=2, allow_nan=False))
        cal_path.write_text(json.dumps(artifacts, indent=2))
    (WORK / "results.json").write_text(json.dumps(results, indent=2, allow_nan=False))
    with (WORK / "pair_matrix.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("target", "detector", "exposure_1", "release_1", "UTC_1", "core_1",
                         "exposure_2", "release_2", "UTC_2", "core_2", "baseline_days", "predicted_shift_arcsec",
                         "prediction_1_deg", "prediction_2_deg", "source_overlap", "valid_aligned_pixels",
                         "measured_shift", "uncertainty", "stationary_control", "rejections"))
        for r in results:
            a, b = r["endpoints"]
            trial = r["comparison"]
            writer.writerow([r["target"], r["detector"], a["observation"], a["release"], a.get("utc"), a.get("core"),
                             b["observation"], b["release"], b.get("utc"), b.get("core"), trial["baseline_days"],
                             trial.get("expected_displacement_arcsec"), a.get("predicted_deg"), b.get("predicted_deg"),
                             trial["source_core_overlap"], trial["aligned_field_pixels"],
                             trial["observed_centroid_displacement"], trial["observed_uncertainty"], trial["stationary_control"],
                             " | ".join(trial["rejection_reasons"]) or "preflight only, independent centroid validation required"])
    print(f"{len(results)} selected pairs. {sum(not r['comparison']['rejection_reasons'] for r in results)} passed preflight.")


if __name__ == "__main__":
    main()
