"""Bounded native-WCS and passband preflight for a real moving-source demonstration."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import io
import json
from pathlib import Path

import astropy.units as u
import httpx
import numpy as np
from astropy.coordinates import SkyCoord, get_body_barycentric
from astropy.io import fits
from astropy.time import Time

from study_epsf_photometry import PREVIEW, ROOT
from app.science.calibrated_comparison import compare_calibrated_pair, prepare_calibrated_exposure
from app.science.target_astrometry import REFERENCES, footprint_pixel, predict
from validate_d6_controls import WAVE_ID, WAVE_MD5, response_overlap

CACHE = ROOT / "data/cache/target_validation/motion_study"
ADDITIONAL = CACHE.parent / "additional_epochs"
SOURCES = {
    "Barnard's Star": "barnards_star", "Epsilon Indi B": "epsilon_indi_b",
    "WISE 0855": "wise_0855", "RW Aurigae": "rw_aurigae", "R Draconis": "r_draconis",
}
PARALLAX = {"wise_0855": 439.0, "rw_aurigae": 15.42, "r_draconis": 1.2509}
EXTRA = ("kapteyn", "lalande_21185", "wolf_359")
GAIA_IDS = {"kapteyn": "4810594479418041856", "lalande_21185": "762815470562110464",
            "wolf_359": "3864972938605115520", "barnards_star": "4472832130942575872",
            "epsilon_indi_b": "6412596012146801152"}
BASELINE_DAYS = 180
MIN_OVERLAP = .9


def apparent_position(target, epoch, catalog):
    if target in catalog:
        row = catalog[target]["row"]
        origin = SkyCoord(float(row["RA_ICRS"]) * u.deg, float(row["DE_ICRS"]) * u.deg,
                          distance=(1000 / float(row["Plx"])) * u.pc,
                          pm_ra_cosdec=float(row["pmRA"]) * u.mas / u.yr,
                          pm_dec=float(row["pmDE"]) * u.mas / u.yr,
                          radial_velocity=float(row["RV"] or 0) * u.km / u.s,
                          obstime=Time(2016., format="jyear", scale="tcb"), frame="icrs")
        space = origin.apply_space_motion(new_obstime=epoch)
        vector = space.cartesian.without_differentials() - get_body_barycentric("earth", epoch)
    else:
        origin = predict(REFERENCES[target], epoch)
        vector = origin.cartesian * ((1000 / PARALLAX[target]) * u.pc) - get_body_barycentric("earth", epoch)
    return SkyCoord(vector, frame="icrs", representation_type="spherical")


def candidate_rows(rows, count=4):
    """Select spread-out exposure IDs in each side of 2026-01-01 UTC."""
    unique = {}
    for row in rows:
        if row.get("energy_bandpassname") != "SPHEREx-D6" or not row.get("access_url"):
            continue
        mid = (float(row["t_min"]) + float(row["t_max"])) / 2
        unique.setdefault(row["obs_id"], dict(observation=row["obs_id"], release=row["release"],
                                              midpoint_query=mid, access_url=row["access_url"]))
    all_rows = sorted(unique.values(), key=lambda row: row["midpoint_query"])
    boundary = Time("2026-01-01", scale="utc").mjd
    groups = [[r for r in all_rows if r["midpoint_query"] < boundary],
              [r for r in all_rows if r["midpoint_query"] >= boundary]]
    return all_rows, [row for group in groups for row in evenly_sample(group, count)]


def evenly_sample(rows, count):
    if len(rows) <= count:
        return rows
    return [rows[i] for i in np.linspace(0, len(rows) - 1, count).round().astype(int)]


def capture_catalog(client, path):
    def fetch(item):
        target, source = item
        response = client.get("https://vizier.cfa.harvard.edu/viz-bin/asu-tsv", params={
            "-source": "I/355/gaiadr3", "Source": source,
            "-out": "Source,RA_ICRS,DE_ICRS,pmRA,pmDE,Plx,RV,RUWE", "-out.max": 2,
        })
        response.raise_for_status()
        lines = [line for line in response.text.splitlines() if line and not line.startswith("#")]
        rows = [{k: v.strip() for k, v in row.items()} for row in csv.DictReader(lines, delimiter="\t")
                if row.get("Source", "").strip() == source]
        if len(rows) != 1:
            raise ValueError(f"Gaia DR3 source {source} did not resolve uniquely")
        return target, dict(url=str(response.url), row=rows[0])

    with ThreadPoolExecutor(max_workers=3) as pool:
        references = dict(pool.map(fetch, GAIA_IDS.items()))
    path.write_text(json.dumps(references, indent=2), encoding="utf-8")


def search_archive(client, catalog):
    def query(job):
        target, release = job
        at = apparent_position(target, Time(2026.0, format="jyear"), catalog)
        request = dict(COLLECTION=release, POS=f"circle {at.ra.deg:.8f} {at.dec.deg:.8f} 0.012",
                       RESPONSEFORMAT="CSV", MAXREC=3000)
        url = "https://irsa.ipac.caltech.edu/SIA"
        try:
            res = client.get(url, params=request)
            if not res.is_success:
                res = client.get(url, params=request)
        except httpx.RequestError as err:
            return dict(target=target, release=release, url=str(client.build_request("GET", url, params=request).url),
                        http=None, error=type(err).__name__, rows=[])
        payload = dict(target=target, release=release, url=str(res.url), http=res.status_code, rows=[])
        if res.is_success:
            reader = csv.DictReader(io.StringIO(res.text.lstrip("\ufeff")))
            if not {"obs_id", "energy_bandpassname", "t_min", "t_max", "access_url"}.issubset(reader.fieldnames or ()):
                payload["error"] = "Unexpected SIA CSV header"
            else:
                payload["rows"] = [dict(row, release=release) for row in reader
                                   if row.get("energy_bandpassname") == "SPHEREx-D6"]
        return payload

    jobs = [(key, release) for key in EXTRA for release in ("spherex_dr1", "spherex_qr3")]
    with ThreadPoolExecutor(max_workers=4) as pool:
        searches = list(pool.map(query, jobs))
    records = []
    for target in EXTRA:
        source_rows = [row for query in searches if query["target"] == target for row in query["rows"]]
        _, subset = candidate_rows(source_rows)
        records.extend(dict(row, target=target) for row in subset)

    with ThreadPoolExecutor(max_workers=4) as pool:
        cutouts = list(pool.map(lambda row: fetch_cutout(client, catalog, row, "0.0350"), records))
    path = CACHE / "archive.json"
    path.write_text(json.dumps(dict(searches=searches, cutouts=cutouts), indent=2), encoding="utf-8")


def fetch_cutout(client, catalog, row, size):
    at = apparent_position(row["target"], Time(row["midpoint_query"], format="mjd", scale="utc"), catalog)
    params = {"center": f"{at.ra.deg:.7f},{at.dec.deg:.7f}", "size": size}
    result = {k: row[k] for k in ("target", "midpoint_query", "observation", "release", "access_url")}
    try:
        response = client.get(row["access_url"], params=params)
    except httpx.RequestError as err:
        url = str(client.build_request("GET", row["access_url"], params=params).url)
        return dict(result, cutout_url=url, http=None, error=type(err).__name__)
    result.update(cutout_url=str(response.url), http=response.status_code)
    if response.is_success:
        try:
            with fits.open(io.BytesIO(response.content)) as hdul:
                if hdul["IMAGE"].header.get("OBSID") != row["observation"]:
                    raise ValueError("Cutout observation header disagrees")
        except (KeyError, OSError, ValueError) as err:
            result["error"] = str(err)
        else:
            filename = hashlib.sha256(str(response.url).encode()).hexdigest() + ".fits"
            (CACHE / filename).write_bytes(response.content)
            result["file"] = filename
    return result


def retry_failed_cutouts(client, catalog):
    path = CACHE / "archive.json"
    archive = json.loads(path.read_text())

    def retry(row):
        if row.get("file") or row.get("primary_failure"):
            return row
        retried = fetch_cutout(client, catalog, row, "0.0250")
        return dict(retried, primary_failure=row)

    with ThreadPoolExecutor(max_workers=4) as pool:
        archive["cutouts"] = list(pool.map(retry, archive["cutouts"]))
    path.write_text(json.dumps(archive, indent=2), encoding="utf-8")


def summarize_frame(path, meta, wave_data, catalog):
    with fits.open(path) as hdul:
        head = hdul["IMAGE"].header
        exposure = prepare_calibrated_exposure(hdul, wave_data, plane_id=WAVE_ID, checksum=WAVE_MD5)
        epoch = Time(head["MJD-AVG"], format="mjd", scale="utc")
        position = apparent_position(meta["target"], epoch, catalog)
        px = footprint_pixel(exposure.wcs, exposure.image.shape, position)
        summary = dict(meta, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                       mjd=epoch.mjd, utc=epoch.isot, predicted_deg=[position.ra.deg, position.dec.deg],
                       pixel=px)
        if px is None or not px["inside"]:
            return dict(summary, core=None, passbands=None), exposure
        yy, xx = np.indices(exposure.image.shape)
        radius = np.hypot(xx - px["x"], yy - px["y"])
        core = radius <= 2.5
        valid = exposure.usable()
        wave = exposure.wavelength[core]
        band = exposure.bandwidth[core]
        intervals = np.column_stack((wave - band / 2, wave + band / 2))
        passbands = intervals.tolist() if intervals.size and np.isfinite(intervals).all() else None
        counts = [int((core & valid).sum()), int(core.sum())]
        contained = min(px["x"] + .5, px["y"] + .5,
                        exposure.image.shape[1] - .5 - px["x"], exposure.image.shape[0] - .5 - px["y"]) >= 2.5
        # copy data because FITS file closes before comparing exposures
        for name in ("image", "variance", "bad", "wavelength", "bandwidth"):
            setattr(exposure, name, np.array(getattr(exposure, name), copy=True))
        return dict(summary, core=counts, core_contained=contained, passbands=passbands), exposure


def assess_pair(first, second):
    a, exp_a = first
    b, exp_b = second
    baseline = b["mjd"] - a["mjd"]
    apos, bpos = (SkyCoord(*f["predicted_deg"], unit="deg") for f in (a, b))
    east, north = apos.spherical_offsets_to(bpos)
    overlap = response_overlap(a["passbands"], b["passbands"]) if a["passbands"] and b["passbands"] else None
    reasons = []
    if a["observation"] == b["observation"] or baseline < BASELINE_DAYS:
        reasons.append("independent exposures at least 180 days apart required")
    if any(not f.get("core_contained") or f["core"][0] != f["core"][1] for f in (a, b)):
        reasons.append("masked, unavailable or clipped source core")
    if overlap is None or overlap < MIN_OVERLAP - 1e-12:
        reasons.append("source-core passbands below 90% overlap or unavailable")
    try:
        compared = compare_calibrated_pair(exp_a, exp_b, minimum_passband_overlap=MIN_OVERLAP)
        field_count = compared["retained_pixels"]
        field_rejection = None
    except ValueError as exc:
        field_count, field_rejection = 0, str(exc)
    if not field_count:
        reasons.append("no matched valid pixels in aligned fields")
    return dict(target=a["target"], observations=[a["observation"], b["observation"]], baseline_days=baseline,
                endpoints=[{key: f.get(key) for key in ("release", "detector", "utc", "predicted_deg", "core")}
                           for f in (a, b)],
                expected_east_north_arcsec=[east.arcsec, north.arcsec],
                expected_displacement_arcsec=apos.separation(bpos).arcsec,
                source_core_overlap=overlap, aligned_field_pixels=field_count,
                aligned_field_rejection=field_rejection, rejection_reasons=reasons,
                observed_centroid_displacement=None, observed_uncertainty=None,
                stationary_control=None, validated_motion=False)


def write_matrix(pair_groups):
    header = ["sample", "target", "observation_1", "observation_2", "release_1", "release_2", "detector",
              "utc_1", "utc_2", "baseline_days", "prediction_1_deg", "prediction_2_deg", "expected_shift_arcsec",
              "core_1_valid_total", "core_2_valid_total", "minimum_core_overlap", "matched_field_pixels",
              "observed_shift", "observed_uncertainty", "stationary_control", "preflight_result"]
    with (CACHE / "motion_pair_matrix.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        for name, pairs in pair_groups:
            for row in pairs:
                a, b = row["endpoints"]
                writer.writerow([name, row["target"], *row["observations"], a["release"], b["release"], a["detector"],
                                 a["utc"], b["utc"], row["baseline_days"], a["predicted_deg"], b["predicted_deg"],
                                 row["expected_displacement_arcsec"], a["core"], b["core"], row["source_core_overlap"],
                                 row["aligned_field_pixels"], row["observed_centroid_displacement"],
                                 row["observed_uncertainty"], row["stationary_control"],
                                 " | ".join(row["rejection_reasons"]) or "preflight only, independent centroid validation required"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    network = parser.add_mutually_exclusive_group()
    network.add_argument("--fetch", action="store_true", help="Run the bounded public SIA and cutout search.")
    network.add_argument("--retry-failed", action="store_true", help="Retry each failed cutout once with a smaller size.")
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    catalog_path = CACHE / "catalog.json"
    if args.fetch and not catalog_path.exists():
        with httpx.Client(timeout=18) as client:
            capture_catalog(client, catalog_path)
    catalog = json.loads(catalog_path.read_text())
    if args.fetch:
        with httpx.Client(timeout=18) as client:
            search_archive(client, catalog)
    if args.retry_failed:
        with httpx.Client(timeout=18) as client:
            retry_failed_cutouts(client, catalog)
    spectral = (ROOT / f"data/cache/spectral-{WAVE_MD5}.fits").read_bytes()
    archive = json.loads((CACHE / "archive.json").read_text()) if (CACHE / "archive.json").is_file() else {}
    frames, stage_pairs, supplements, extra_pairs, unavailable = {}, [], [], [], []
    for row in json.loads((PREVIEW / "demo_dataset.json").read_text()):
        key = hashlib.sha256(row["cutout_url"].encode()).hexdigest() + ".fits"
        target = SOURCES[row["target_name"]]
        frames.setdefault(target, []).append(summarize_frame(PREVIEW / key, dict(
            target=target, observation=row["obs_id"], release=row["collection"],
            detector=row["detector"], url=row["cutout_url"], sample="staged"), spectral, catalog))
    for samples in frames.values():
        stage_pairs.append(assess_pair(*sorted(samples, key=lambda s: s[0]["mjd"])))
    for row in json.loads((ADDITIONAL / "evidence.json").read_text()):
        if not row.get("file") or not (ADDITIONAL / row["file"]).is_file():
            continue
        if any(row["id"] == f[0]["observation"] for f in frames[row["target"]]):
            continue
        sample = summarize_frame(ADDITIONAL / row["file"], dict(
            target=row["target"], observation=row["id"], release=row["release"],
            detector="SPHEREx-D6", url=row["url"], sample="previous supplement"), spectral, catalog)
        anchor = min(frames[row["target"]], key=lambda s: s[0]["mjd"])
        if sample[0]["mjd"] - anchor[0]["mjd"] >= BASELINE_DAYS:
            supplements.append(assess_pair(anchor, sample))
        frames[row["target"]].append(sample)
    for row in archive.get("cutouts", []):
        if not row.get("file"):
            continue
        meta = dict(target=row["target"], observation=row["observation"], release=row["release"],
                    detector="SPHEREx-D6", url=row["cutout_url"], sample="new bounded search")
        try:
            sample = summarize_frame(CACHE / row["file"], meta, spectral, catalog)
        except (KeyError, OSError, ValueError) as err:
            unavailable.append(dict(meta, reason=str(err)))
            continue
        frames.setdefault(row["target"], []).append(sample)
    for key in EXTRA:
        samples = sorted(frames.get(key, []), key=lambda s: s[0]["mjd"])
        for i, first in enumerate(samples):
            for second in samples[i + 1:]:
                if second[0]["mjd"] - first[0]["mjd"] >= BASELINE_DAYS:
                    extra_pairs.append(assess_pair(first, second))
    result = dict(frames={k: [s[0] for s in v] for k, v in frames.items()},
                  staged_pairs=stage_pairs, supplementary_pairs=supplements, catalog_pairs=extra_pairs,
                  uncalibrated_or_unreadable=unavailable)
    path = CACHE / "motion_preflight.json"
    path.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    pair_groups = (("staged", stage_pairs), ("supplementary", supplements), ("catalog", extra_pairs))
    write_matrix(pair_groups)
    for name, pairs in pair_groups:
        print(f"{name}: {len(pairs)} evaluated, {sum(not r['rejection_reasons'] for r in pairs)} pass preflight")
    print(path)


if __name__ == "__main__":
    main()
