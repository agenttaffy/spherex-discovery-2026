"""Audit real D6 point-source controls. No application data is updated."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

import astropy.units as u
import httpx
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time

from study_epsf_photometry import (
    AREA_MD5, CORE_RADIUS, FIT_RADIUS, PREVIEW, ROOT, WORK,
    describe, extract_astropy_wcs, fit, geometry, load_exposure, render_native,
)
from app.science.spectral_calibration import map_calibration_to_cutout

FIELDS = {
    "wise_field": ("2025W19_1B_0116_2", "2026W19_2A_0952_1"),
    "epsilon_field": ("2025W18_1B_0081_2", "2026W39_1A_0276_2"),
    "deep_field": ("2025W18_1B_0242_2", "2025W18_1B_0252_2"),
}
DEEP_CENTER = (270.0, 66.56)
CATALOGS = {
    "gaia": ("I/355/gaiadr3", "Source,RA_ICRS,DE_ICRS,pmRA,pmDE,Plx,RUWE,VarFlag,NSS,Dup"),
    "allwise": ("II/328/allwise", "AllWISE,RAJ2000,DEJ2000,RA_pm,DE_pm,W2mag,e_W2mag,ccf,ex,nb,na,sat2"),
}
CATALOG_RADIUS = 460 * u.arcsec
CATALOG_LIMIT = 5000
WISE_EPOCH = Time(55400, format="mjd", scale="utc").jyear
WAVE_MD5 = "e665c189ad63ca0cd032c0797e8aabf2"
WAVE_ID = "019f4f99-5f21-722d-bd8d-a6033df45708"


def number(row, key):
    try:
        return float(row.get(key, ""))
    except (TypeError, ValueError):
        return np.nan


def parse_catalog(text, columns):
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    reader = csv.DictReader(lines, delimiter="\t")
    if not set(columns.split(",")).issubset(reader.fieldnames or ()):
        raise ValueError("Unexpected catalog schema")
    ra_key, dec_key = columns.split(",")[1:3]
    rows = [{key: val.strip() for key, val in row.items() if key and val is not None}
            for row in reader if np.isfinite(number(row, ra_key)) and np.isfinite(number(row, dec_key))]
    if not rows or len(rows) >= CATALOG_LIMIT:
        raise ValueError("Catalog query empty or truncated")
    return rows


def get_catalog(client, cache, field, name, ra, dec):
    table, columns = CATALOGS[name]
    path = cache / f"{field}-{name}.json"
    if client is not None:
        reply = client.get("https://vizier.cfa.harvard.edu/viz-bin/asu-tsv", params={
            "-source": table, "-c": f"{ra:.8f} {dec:+.8f}", "-c.rs": CATALOG_RADIUS.value,
            "-out": columns, "-out.max": CATALOG_LIMIT,
        })
        reply.raise_for_status()
        rows = parse_catalog(reply.text, columns)
        path.write_text(json.dumps({"url": str(reply.url), "rows": rows}, indent=2), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))


def catalog_quality(g, w):
    return (all(np.isfinite(number(g, k)) for k in ("pmRA", "pmDE"))
            and 0 < number(g, "RUWE") <= 1.4 and 0 <= number(g, "Plx") <= 20
            and g["NSS"] == "0" and g["Dup"] == "0" and g["VarFlag"] != "VARIABLE"
            and np.isfinite(number(w, "W2mag")) and 0 < number(w, "e_W2mag") <= .15
            and len(w["ccf"]) == 4 and w["ccf"][1] == "0" and number(w, "sat2") == 0
            and w["ex"] == "0" and w["nb"] == "1" and w["na"] == "0")


def gaia_at(coords, rows, jyear):
    proper_motion = np.asarray([[number(row, k) for k in ("pmRA", "pmDE")] for row in rows])
    offsets = np.where(np.isfinite(proper_motion), proper_motion, 0) * ((jyear - 2016.0) * u.mas)
    return coords.spherical_offsets_by(offsets[:, 0], offsets[:, 1])


def crossmatches(gaia, wise):
    gaia_ref = SkyCoord([number(row, "RA_ICRS") for row in gaia],
                        [number(row, "DE_ICRS") for row in gaia], unit="deg")
    has_motion_position = [np.isfinite(number(row, "RA_pm")) and np.isfinite(number(row, "DE_pm")) for row in wise]
    wise_motion = SkyCoord(
        [number(row, "RA_pm" if known else "RAJ2000") for row, known in zip(wise, has_motion_position)],
        [number(row, "DE_pm" if known else "DEJ2000") for row, known in zip(wise, has_motion_position)], unit="deg",
    )
    old_gaia = gaia_at(gaia_ref, gaia, WISE_EPOCH)
    nearest, separations, _ = old_gaia.match_to_catalog_sky(wise_motion)
    reverse, _, _ = wise_motion.match_to_catalog_sky(old_gaia)
    matched = [(i, int(w), float(sep.arcsec)) for i, (w, sep) in enumerate(zip(nearest, separations))
               if reverse[w] == i and sep <= 1 * u.arcsec]
    clean = [(i, w, sep) for i, w, sep in matched
             if has_motion_position[w] and catalog_quality(gaia[i], wise[w])]
    return gaia_ref, wise_motion, matched, clean


def response_overlap(a, b):
    """Worst overlap across both cores, normalized by the wider nominal interval."""
    lower_a, upper_a = np.asarray(a).T
    lower_b, upper_b = np.asarray(b).T
    span = np.minimum(upper_a[:, None], upper_b) - np.maximum(lower_a[:, None], lower_b)
    wider = np.maximum((upper_a - lower_a)[:, None], upper_b - lower_b)
    return float(np.min(np.clip(span / wider, 0, 1)))


def recovery_status(diagnostic):
    if diagnostic["status"] != "experimental fit":
        return diagnostic["status"]
    significance = diagnostic["formal_snr"]
    if significance < 5:
        return "insufficient formal S/N"
    if diagnostic["chi2_tail"] < .01:
        return "poor nominal fit residuals"
    if (diagnostic["centroid_trials"] != 4 or
            max(diagnostic["centroid_change_sigma"], diagnostic["gradient_change_sigma"]) > .1 * significance):
        return "centroid or background sensitivity"
    return "positional recovery only"


def phase_reference(hdul):
    """Compare the renderer against the IRSA notebook's Photutils implementation."""
    from photutils.psf import ImagePSF
    grid = np.arange(11)
    yy, xx = np.meshgrid(grid, grid, indexing="ij")
    peak_difference = 0.0
    count = 0
    for row in hdul["EPSF"].data[[0, 20, 220, 420, 440]]:
        template = row["EPSF"]
        ref = ImagePSF(template, oversampling=5)
        for x, y in ((5, 5), (5.5, 5.5), (5.1, 4.8), (4.71, 5.36)):
            expected = ref.evaluate(xx, yy, 1, x, y)
            expected /= expected.sum()
            actual = render_native(template, x, y, (5, 5), (xx, yy))
            peak_difference = max(peak_difference, float(np.max(np.abs(expected - actual))))
            count += 1
    return {"stamps": count, "maximum_pixel_difference_fraction": peak_difference}


def examine_frame(hdul, area, wave_data, center, gaia_rows, wise_rows, match, target, blanks, reference):
    exp = load_exposure(hdul, area)
    header = hdul["IMAGE"].header
    wcs = extract_astropy_wcs(header)
    epoch = Time(header["MJD-AVG"], format="mjd", scale="utc")
    gaia_ref, wise_catalog, _, clean = match
    gaia = gaia_at(gaia_ref, gaia_rows, epoch.jyear)
    gaia_xy = np.asarray(wcs.world_to_pixel(gaia)).T
    wise_xy = np.asarray(wcs.world_to_pixel(wise_catalog)).T
    wave, band = map_calibration_to_cutout(hdul, wave_data, plane_id=WAVE_ID, checksum=WAVE_MD5)
    h, w = exp.image.shape
    yy, xx = np.indices((h, w))
    target_xy = np.asarray(wcs.world_to_pixel(target)) if target is not None else None
    center_x, center_y = wcs.world_to_pixel(center)
    center_core = np.hypot(xx - center_x, yy - center_y) <= CORE_RADIUS
    center_intervals = np.column_stack((wave[center_core] - band[center_core] / 2,
                                        wave[center_core] + band[center_core] / 2))
    if not center_intervals.size or not np.isfinite(center_intervals).all():
        raise ValueError("Missing field-center spectral calibration")

    def covered(xy):
        sky = wcs.pixel_to_world(*xy)
        return center.separation(sky) + 36 * u.arcsec <= CATALOG_RADIUS

    excluded = Counter()
    rejects = []
    stars = []
    for i, j, separation in clean:
        xy = gaia_xy[i]
        x, y = xy
        source = dict(gaia_source=gaia_rows[i]["Source"], allwise_source=wise_rows[j]["AllWISE"])
        if not np.isfinite(xy).all() or not (0 <= x < w and 0 <= y < h):
            excluded["outside FITS footprint"] += 1
            rejects.append(dict(source, reason="outside FITS footprint"))
            continue
        if not covered(xy) or (target is not None and np.linalg.norm(xy - target_xy) <= 7):
            excluded["catalog boundary or named target vicinity"] += 1
            rejects.append(dict(source, reason="catalog boundary or named target vicinity"))
            continue
        gaia_distance = np.linalg.norm(gaia_xy - xy, axis=1)
        wise_distance = np.linalg.norm(wise_xy - xy, axis=1)
        gaia_distance[i] = wise_distance[j] = np.inf
        closest = float(min(np.nanmin(gaia_distance), np.nanmin(wise_distance)))
        if closest <= 5:
            excluded["catalog neighbor"] += 1
            rejects.append(dict(source, reason="catalog neighbor", nearest_other_pixels=closest))
            continue
        diagnostic, trial = describe(exp, tuple(xy))
        status = recovery_status(diagnostic)
        info = {"gaia_source": gaia_rows[i]["Source"], "allwise_source": wise_rows[j]["AllWISE"],
                "match_separation_arcsec": separation, "broad_w2_mag": number(wise_rows[j], "W2mag"),
                "broad_w2_error_mag": number(wise_rows[j], "e_W2mag"), "result": status,
                "matched_d6_reference_flux": None, **diagnostic}
        if trial is not None:
            radius = np.hypot(xx - x, yy - y)
            core = radius <= CORE_RADIUS
            if np.isfinite(wave[core]).all() and np.isfinite(band[core]).all():
                info["core_passbands_um"] = np.column_stack((wave[core] - band[core] / 2,
                                                            wave[core] + band[core] / 2)).tolist()
            # Compare the prototype's per-pixel conversion to the source-center-area convention.
            _, _, model = geometry(exp, tuple(xy))
            native = model[0] * exp.area_factor
            center_model = (native / exp.area_factor[round(y), round(x)], *model[1:])
            center_fit = fit(exp, exp.image, center_model)
            if trial.amplitude:
                info["center_area_change_fraction"] = float((center_fit.amplitude / trial.amplitude) - 1)
        stars.append(info)

    nulls, null_screen = [], Counter()
    if blanks:
        for y in range(6, h - 6, 10):
            for x in range(6, w - 6, 10):
                xy = (x + .5, y + .5)
                if not covered(xy) or (target is not None and np.linalg.norm(target_xy - xy) <= 7):
                    null_screen["catalog boundary or named target vicinity"] += 1
                elif any(np.any(np.linalg.norm(points - xy, axis=1) <= 5.5) for points in (gaia_xy, wise_xy)):
                    null_screen["catalog neighbor"] += 1
                elif exp.source[np.hypot(xx - xy[0], yy - xy[1]) <= FIT_RADIUS].any():
                    null_screen["SOURCE flag"] += 1
                else:
                    diagnostic, trial = describe(exp, xy)
                    if trial is None:
                        null_screen[diagnostic["status"]] += 1
                    else:
                        nulls.append(diagnostic)
    return dict(mjd=epoch.mjd, dimensions=[h, w], stars=stars, excluded=dict(excluded), catalog_rejections=rejects,
                nulls=nulls, null_screen=dict(null_screen),
                field_center_core_passbands_um=center_intervals.tolist(),
                maximum_relative_area_span=float(np.ptp(exp.area_factor) / exp.area_factor.min()),
                photutils_reference=phase_reference(hdul) if reference else None)


def compare_epochs(first, second):
    second_by_source = {item["gaia_source"]: item for item in second["stars"]}
    results = []
    for a in first["stars"]:
        b = second_by_source.get(a["gaia_source"])
        if b is None:
            continue
        overlap = (response_overlap(a["core_passbands_um"], b["core_passbands_um"])
                   if "core_passbands_um" in a and "core_passbands_um" in b else None)
        reason = "two clean positional recoveries required"
        if a["result"] == b["result"] == "positional recovery only":
            reason = "nominal passband overlap below 90% or unavailable"
            if overlap is not None and overlap >= .9:
                reason = "eligible for repeat diagnostics with verified calibration"
        results.append(dict(gaia_source=a["gaia_source"], overlap=overlap, status=reason,
                            epoch_results=[a["result"], b["result"]]))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="Fetch public catalog neighborhoods and missing wider cutouts.")
    parser.add_argument("--photutils-check", action="store_true", help="Compare native stamps with installed Photutils.")
    args = parser.parse_args()
    cache = WORK / "real_controls"
    cache.mkdir(exist_ok=True)
    release_map = WORK / "SAPM-D6-v3.fits"
    if hashlib.md5(release_map.read_bytes()).hexdigest() != AREA_MD5:
        raise ValueError("Unexpected D6 solid-angle map checksum")
    with fits.open(release_map) as hdul:
        area = hdul["IMAGE"].data.copy()
    spectral = (ROOT / f"data/cache/spectral-{WAVE_MD5}.fits").read_bytes()
    entries = {r["obs_id"]: r for r in json.loads((PREVIEW / "demo_dataset.json").read_text())}
    deep_base = "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W18_1B/l2b-v27-2026-196/6/"
    for oid, size in zip(FIELDS["deep_field"], ("0.16", ".12")):
        entries[oid] = dict(collection="spherex_dr1", predicted_degrees=DEEP_CENTER, size=size,
                            cutout_url=f"{deep_base}level2_{oid}D6_spx_l2b-v27-2026-196.fits")
    report = {}
    with httpx.Client(timeout=30) as http:
        for name, ids in FIELDS.items():
            ra, dec = np.mean([entries[key]["predicted_degrees"] for key in ids], axis=0)
            center = SkyCoord(ra, dec, unit="deg")
            catalogs = {key: get_catalog(http if args.fetch else None, cache, name, key, ra, dec)
                        for key in CATALOGS}
            gaia, wise = (catalogs[key]["rows"] for key in ("gaia", "allwise"))
            match = crossmatches(gaia, wise)
            frames = {}
            for index, oid in enumerate(ids):
                path = WORK / f"{oid}-wide-fits.fits"
                metadata = path.with_suffix(".json")
                entry = entries[oid]
                if not path.is_file() and args.fetch:
                    cr, cd = entry["predicted_degrees"]
                    raw = http.get(entry["cutout_url"].split("?")[0],
                                   params={"center": f"{cr:.7f},{cd:.7f}", "size": entry.get("size", "0.16")})
                    raw.raise_for_status()
                    with fits.open(io.BytesIO(raw.content)) as check:
                        _ = check["IMAGE"].data.shape
                    path.write_bytes(raw.content)
                    metadata.write_text(json.dumps({"url": str(raw.url)}), encoding="utf-8")
                with fits.open(path) as hdul:
                    if hdul["IMAGE"].header.get("OBSID") != oid:
                        raise ValueError(f"Unexpected exposure in {path}")
                    target = None if name == "deep_field" else SkyCoord(*entry["predicted_degrees"], unit="deg")
                    frame = examine_frame(hdul, area, spectral, center, gaia, wise, match, target,
                                          index == 0, args.photutils_check)
                frames[oid] = dict(collection=entry["collection"], **frame,
                                   artifact=json.loads(metadata.read_text())["url"],
                                   sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            report[name] = dict(catalogs={k: {"url": v["url"], "rows": len(v["rows"])} for k, v in catalogs.items()},
                                mutual_matches=len(match[2]), catalog_eligible=len(match[3]), frames=frames,
                                field_center_overlap=response_overlap(*(f["field_center_core_passbands_um"]
                                                                         for f in frames.values())),
                                repeats=compare_epochs(*frames.values()))
    out = cache / "real_source_controls.json"
    out.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
