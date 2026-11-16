"""Local D6 forced-fit diagnostic study. Never exports named-target fluxes."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from scipy.interpolate import RectBivariateSpline
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.science.fits_processing import (
    SPHEREX_INFORMATIONAL_FLAG_NAMES,
    extract_astropy_wcs,
    parse_spherex_mask_planes,
)
from app.science.target_astrometry import REFERENCES, footprint_pixel, predict

PREVIEW = ROOT / "data/cache/demo_multiepoch"
WORK = ROOT / "data/cache/target_validation/epsf_study"
AREA_MD5 = "c01934ebcdd287f96e94c2af6ba9be26"
ARCSEC2_TO_SR = (1 * u.arcsec**2).to_value(u.sr)
FIT_RADIUS = 4.5
CORE_RADIUS = 2.5


@dataclass
class Exposure:
    image: np.ndarray
    variance: np.ndarray
    area_factor: np.ndarray
    valid: np.ndarray
    source: np.ndarray
    zone_table: np.ndarray
    oversampling: tuple[int, int]
    offset: tuple[int, int]


@dataclass
class Fit:
    amplitude: float
    sigma: float
    reduced_chi2: float
    probability: float
    rms: float
    core_abs_pull: float


def load_exposure(hdul, area_grid):
    header = hdul["IMAGE"].header
    image = hdul["IMAGE"].data.astype(float)
    variance = hdul["VARIANCE"].data.astype(float)
    flags = hdul["FLAGS"].data
    brightness = u.MJy / u.sr
    if (u.Unit(header["BUNIT"]) != brightness
            or u.Unit(hdul["VARIANCE"].header["BUNIT"]) != brightness**2
            or image.ndim != 2 or variance.shape != image.shape
            or flags.shape != image.shape or not np.issubdtype(flags.dtype, np.integer)):
        raise ValueError("Invalid image, variance or flag plane")
    if (str(header["DETECTOR"]) != "6" or header["DETCOORD"] != "sky"
            or any(header[f"CTYPE{i}A"] != "LINEAR" or header[f"CDELT{i}A"] != 1
                   or header[f"CRVAL{i}A"] != 0 or header[f"CRPIX{i}A"] % 1
                   for i in (1, 2))
            or any(k in header for k in ("CD1_1A", "CD1_2A", "CD2_1A", "CD2_2A"))
            or any(header.get(k, v) != v for k, v in
                   (("PC1_1A", 1), ("PC1_2A", 0), ("PC2_1A", 0), ("PC2_2A", 1)))):
        raise ValueError("Unsupported detector mapping")
    x0, y0 = (int(1 - header[f"CRPIX{i}A"]) for i in (1, 2))
    height, width = image.shape
    if not (0 <= x0 <= area_grid.shape[1] - width and 0 <= y0 <= area_grid.shape[0] - height):
        raise ValueError("Cutout outside area calibration")
    area = area_grid[y0:y0 + height, x0:x0 + width].astype(float)
    if not (np.isfinite(area) & (area > 0)).all():
        raise ValueError("Invalid pixel solid angle")

    definitions = parse_spherex_mask_planes(hdul["FLAGS"].header)
    if not definitions.get("SOURCE"):
        raise ValueError("Missing source flag definition")
    harmless = 0
    for name in SPHEREX_INFORMATIONAL_FLAG_NAMES:
        harmless |= definitions.get(name, 0)
    flags = flags.astype(np.int64)
    valid = ((flags & ~harmless) == 0) & np.isfinite(image) & np.isfinite(variance) & (variance > 0)
    epsf = hdul["EPSF"]
    oversampling = (epsf.header["OVSMPX"], epsf.header["OVSMPY"])
    if epsf.data is None or len(epsf.data) != 441 or oversampling != (5, 5):
        raise ValueError("Unexpected D6 ePSF zone count or oversampling")
    return Exposure(image, variance, area * ARCSEC2_TO_SR * 1e12, valid,
                    (flags & definitions["SOURCE"]) != 0, epsf.data, oversampling, (x0, y0))


def render_native(table, x0, y0, oversampling, phase_origin):
    """Evaluate the already-effective PSF at native centers, keeping signed lobes."""
    if table.shape != (33, 33) or not np.isfinite(table).all() or not np.isclose(table.sum(), 1):
        raise ValueError("Unexpected ePSF sampling or normalization")
    x, y = phase_origin
    tx = (x - x0) * oversampling[0] + (table.shape[1] - 1) / 2
    ty = (y - y0) * oversampling[1] + (table.shape[0] - 1) / 2
    ix, iy = np.arange(table.shape[1]), np.arange(table.shape[0])
    within = (tx >= 0) & (tx <= ix[-1]) & (ty >= 0) & (ty <= iy[-1])
    stamp = np.zeros_like(tx, dtype=float)
    spline = RectBivariateSpline(ix, iy, table.T)
    stamp[within] = spline.ev(tx[within], ty[within])
    total = stamp.sum()
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Invalid native ePSF normalization")
    return stamp / total


def geometry(exposure, position, valid=None):
    x, y = position
    yy, xx = np.indices(exposure.image.shape)
    dx, dy = xx - x, yy - y
    radius = np.hypot(dx, dy)
    valid = exposure.valid if valid is None else valid
    core = radius <= CORE_RADIUS
    annulus = (radius >= 3.3) & (radius <= FIT_RADIUS) & valid & ~exposure.source
    selected = (radius <= FIT_RADIUS) & valid & ((radius < 3.3) | ~exposure.source)
    counts = dict(core=[int((core & valid).sum()), int(core.sum())], annulus=int(annulus.sum()),
                  fit_pixels=int(selected.sum()))
    h, w = exposure.image.shape
    tail = max((32 / 2) / step for step in exposure.oversampling)
    if min(x + .5, y + .5, w - .5 - x, h - .5 - y) < max(FIT_RADIUS, np.sqrt(2) * tail):
        return counts, "fit footprint crosses cutout edge", None
    if not valid[core].all():
        return counts, "core contains masked or invalid pixels", None
    quadrants = [(dx >= 0) & (dy >= 0), (dx >= 0) & (dy < 0),
                 (dx < 0) & (dy >= 0), (dx < 0) & (dy < 0)]
    if counts["annulus"] < 20 or min(int((q & annulus).sum()) for q in quadrants) < 2:
        return counts, "insufficient source-excluded background", None
    det_x, det_y = x + exposure.offset[0], y + exposure.offset[1]
    table = exposure.zone_table
    zone = ((np.abs(det_x - table["XCENTER"]) < table["XWIDTH"] / 2)
            & (np.abs(det_y - table["YCENTER"]) < table["YWIDTH"] / 2))
    if zone.sum() != 1:
        return counts, "no unique local ePSF zone", None
    psf_row = table[zone][0]
    stamp = render_native(psf_row["EPSF"], x, y, exposure.oversampling, (xx, yy))
    counts["epsf_zone"] = [int(psf_row["BINX"]), int(psf_row["BINY"])]
    return counts, None, (stamp / exposure.area_factor, selected, core, dx, dy)


def fit(exposure, sample, model, plane=False):
    source, selected, core, dx, dy = model
    columns = [source[selected], np.ones(selected.sum())]
    if plane:
        columns.extend([dx[selected], dy[selected]])
    weight = 1 / np.sqrt(exposure.variance[selected])
    matrix = np.column_stack(columns)
    weighted = matrix * weight[:, None]
    observed = sample[selected]
    scales = np.linalg.norm(weighted, axis=0)
    if not (np.isfinite(scales) & (scales > 0)).all():
        raise ValueError("Invalid design columns")
    scaled = weighted / scales
    coef, _, rank, sv = np.linalg.lstsq(scaled, observed * weight, rcond=None)
    dof = len(observed) - matrix.shape[1]
    if rank != matrix.shape[1] or dof < 1 or sv[0] / sv[-1] > 30:
        raise ValueError("Rank-deficient or ill-conditioned fit")
    sigma = np.linalg.norm(np.linalg.pinv(scaled)[0]) / scales[0]
    residual = observed - matrix @ (coef / scales)
    pull = residual * weight
    squared = float(pull @ pull)
    return Fit(coef[0] / scales[0], sigma, squared / dof, chi2.sf(squared, dof),
               float(np.sqrt(np.mean(residual**2))), float(np.mean(np.abs(pull[core[selected]]))))


def describe(exposure, position):
    counts, reason, model = geometry(exposure, position)
    summary = dict(pixel=position, **counts)
    if reason:
        return dict(summary, status=reason), None
    result = fit(exposure, exposure.image, model)
    planar = fit(exposure, exposure.image, model, plane=True)
    changes = []
    for dx, dy in ((-.2, 0), (.2, 0), (0, -.2), (0, .2)):
        _, _, alternate = geometry(exposure, (position[0] + dx, position[1] + dy))
        if alternate is not None:
            shifted = fit(exposure, exposure.image, alternate)
            changes.append(abs(shifted.amplitude - result.amplitude) / result.sigma)
    return dict(summary, status="experimental fit", formal_snr=result.amplitude / result.sigma,
                reduced_chi2=result.reduced_chi2, chi2_tail=result.probability,
                rms_mjy_sr=result.rms, core_mean_abs_pull=result.core_abs_pull,
                gradient_change_sigma=abs(planar.amplitude - result.amplitude) / result.sigma,
                centroid_change_sigma=max(changes) if changes else None, centroid_trials=len(changes)), result


def injection_trials(exposure, center):
    """Reuse actual detector samples and mask; repeated phases share the same noise."""
    trials = []
    for dx, dy in ((0, 0), (-.25, -.25), (-.25, .25), (.25, -.25), (.25, .25)):
        where = (center[0] + dx, center[1] + dy)
        _, reason, model = geometry(exposure, where)
        if reason:
            trials.append(dict(offset=[dx, dy], status=reason))
            continue
        blank = fit(exposure, exposure.image, model)
        _, _, displaced = geometry(exposure, (where[0] + .2, where[1]))
        unknown_or_contaminated = exposure.valid.copy()
        unknown_or_contaminated[round(where[1]), round(where[0])] = False
        assert geometry(exposure, where, unknown_or_contaminated)[2] is None
        for snr in (3, 5, 10, 20):
            flux = snr * blank.sigma
            injected = exposure.image + flux * model[0]
            recovered = fit(exposure, injected, model)
            error = recovered.amplitude - flux
            shifted_error = None
            if displaced is not None:
                shifted = fit(exposure, injected, displaced).amplitude
                shifted_blank = fit(exposure, exposure.image, displaced).amplitude
                shifted_error = (shifted - shifted_blank) / flux - 1
            _, selected, _, x, y = model
            # Unit-noise-scale gradient across the radius, not an observed flux.
            slope = float(np.median(np.sqrt(exposure.variance[selected]))) / FIT_RADIUS
            gradient_error = (fit(exposure, injected + slope * (x - y), model).amplitude
                              - recovered.amplitude) / flux
            trials.append(dict(offset=[dx, dy], status="experimental", nominal_snr=snr,
                               relative_error=error / flux, error_sigma=error / recovered.sigma,
                               incremental_error=(error - blank.amplitude) / flux,
                               displaced_error=shifted_error, gradient_error=gradient_error,
                               reduced_chi2=recovered.reduced_chi2))
    return trials


def gaia_candidates(exposure, rows, midpoint, wcs, target):
    results = []
    for row in rows:
        if not row["pmRA"] or not row["pmDE"]:
            continue
        position = predict(dict(ra=float(row["RA_ICRS"]), dec=float(row["DE_ICRS"]), epoch_jyear=2016,
                                pm_ra_cosdec=float(row["pmRA"]), pm_dec=float(row["pmDE"])), midpoint)
        px = footprint_pixel(wcs, exposure.image.shape, position)
        if px is None or not px["inside"]:
            continue
        point = (px["x"], px["y"])
        if np.hypot(point[0] - target[0], point[1] - target[1]) < 4:
            continue
        summary, _ = describe(exposure, point)
        results.append(dict(gaia_source=row["Source"], gmag=float(row["Gmag"]), **summary))
    return results


def wide_controls(path, area):
    """Use the WISE epoch with both catalogs, avoiding repeat sky patches."""
    oid = "2026W19_2A_0952_1"
    cutout = path / f"{oid}-wide-fits.fits"
    catalog_paths = {key: path / f"{oid}-wide-{key}.json" for key in ("gaia", "allwise")}
    if not cutout.is_file() or not all(p.is_file() for p in catalog_paths.values()):
        return {"status": "wider control cutout or catalogs unavailable"}
    catalogs = {key: json.loads(p.read_text()) for key, p in catalog_paths.items()}
    if any(catalog.get("status") != 200 or not (0 < len(catalog["rows"]) < 2000)
           for catalog in catalogs.values()):
        return {"status": "complete public catalog query unavailable"}
    with fits.open(cutout) as hdul:
        exp = load_exposure(hdul, area)
        wcs = extract_astropy_wcs(hdul["IMAGE"].header)
        epoch = Time(hdul["IMAGE"].header["MJD-AVG"], format="mjd", scale="utc")
        gaia_rows = catalogs["gaia"]["rows"]
        wise_rows = catalogs["allwise"]["rows"]
        gaia_positions = SkyCoord([float(r["RA_ICRS"]) for r in gaia_rows],
                                  [float(r["DE_ICRS"]) for r in gaia_rows], unit="deg")
        wise_positions = SkyCoord([float(r["RAJ2000"]) for r in wise_rows],
                                  [float(r["DEJ2000"]) for r in wise_rows], unit="deg")
        motions = np.asarray([[float(r[k] or 0) for k in ("pmRA", "pmDE")] for r in gaia_rows])
        gaia_epoch = gaia_positions.spherical_offsets_by(
            motions[:, 0] * (epoch.jyear - 2016) * u.mas, motions[:, 1] * (epoch.jyear - 2016) * u.mas)
        gaia_xy = np.asarray(wcs.world_to_pixel(gaia_epoch)).T
        wise_xy = np.asarray(wcs.world_to_pixel(wise_positions)).T
        yy, xx = np.indices(exp.image.shape)
        patches = []
        considered = 0
        for y in range(6, exp.image.shape[0] - 6, 10):
            for x in range(6, exp.image.shape[1] - 6, 10):
                xy = (x + .5, y + .5)
                if any(np.any(np.linalg.norm(coords - xy, axis=1) <= 5.5) for coords in (gaia_xy, wise_xy)):
                    continue
                if exp.source[np.hypot(xx - xy[0], yy - xy[1]) <= FIT_RADIUS].any():
                    continue
                considered += 1
                summary, result = describe(exp, xy)
                if result is not None:
                    patches.append(dict(summary, injections=injection_trials(exp, xy)))

        matched, sky_sep, _ = gaia_positions.match_to_catalog_sky(wise_positions)
        positions = []
        h, w = exp.image.shape
        for index, (g, match, separation) in enumerate(zip(gaia_rows, matched, sky_sep)):
            w2 = wise_rows[match]
            x, y = gaia_xy[index]
            if (separation.arcsec > 1 or not g["pmRA"] or not g["pmDE"] or not w2["e_W2mag"]
                    or float(w2["e_W2mag"]) > .15 or not (0 <= x < w and 0 <= y < h)):
                continue
            other_gaia = np.linalg.norm(gaia_xy - (x, y), axis=1)
            other_wise = np.linalg.norm(wise_xy - (x, y), axis=1)
            other_gaia[index] = np.inf
            other_wise[match] = np.inf
            if min(other_gaia.min(), other_wise.min()) < 3.3:
                continue
            summary, _ = describe(exp, (x, y))
            positions.append(dict(gaia_source=g["Source"], allwise_source=w2["AllWISE"],
                                  separation_arcsec=separation.arcsec, broad_w2_mag=float(w2["W2mag"]),
                                  **summary))
    return dict(observation=oid, sources={k: v.get("url") for k, v in catalogs.items()},
                considered=considered, patches=patches, stars=positions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--area", type=Path, default=WORK / "SAPM-D6-v3.fits")
    parser.add_argument("--catalogs", type=Path, default=WORK / "catalog_controls.json")
    parser.add_argument("--output", type=Path, default=WORK / "forced_fit_diagnostics.json")
    args = parser.parse_args()
    if hashlib.md5(args.area.read_bytes()).hexdigest() != AREA_MD5:
        raise ValueError("Unexpected public D6 SAPM checksum")
    with fits.open(args.area) as hdul:
        area = hdul["IMAGE"].data.copy()
        h = hdul["IMAGE"].header
        if area.shape != (2040, 2040) or h["DETECTOR"] != "6" or h["DETCOORD"] != "sky" or h["BUNIT"] != "arcsec2":
            raise ValueError("Unexpected D6 SAPM geometry or units")
    catalogs = json.loads(args.catalogs.read_text()) if args.catalogs.is_file() else {}
    manifest = json.loads((PREVIEW / "demo_dataset.json").read_text())
    ids = ["barnards_star", "epsilon_indi_b", "wise_0855", "rw_aurigae", "r_draconis"]
    names = ["Barnard's Star", "Epsilon Indi B", "WISE 0855", "RW Aurigae", "R Draconis"]
    results = {"scope": "experimental diagnostics; scene association and flux calibration unvalidated",
               "area_calibration": {"version": "cal-sapm-v3-2026-191", "md5": AREA_MD5,
                                    "exposure_specific_match_verified": False},
               "named_exposures": [], "background_controls": [], "gaia_candidates": []}
    for entry in manifest:
        path = PREVIEW / (hashlib.sha256(entry["cutout_url"].encode()).hexdigest() + ".fits")
        with fits.open(path) as hdul:
            exposure = load_exposure(hdul, area)
            hdr = hdul["IMAGE"].header
            wcs = extract_astropy_wcs(hdr)
            midpoint = Time(hdr["MJD-AVG"], format="mjd", scale="utc")
            target_id = ids[names.index(entry["target_name"])]
            predicted = footprint_pixel(wcs, exposure.image.shape, predict(REFERENCES[target_id], midpoint))
            if not predicted or not predicted["inside"]:
                raise ValueError("Expected staged prediction inside the cutout")
            xy = (predicted["x"], predicted["y"])
            oid = entry["obs_id"]
            summary, _ = describe(exposure, xy)
            nearest = (round(xy[1]), round(xy[0]))
            results["named_exposures"].append(dict(observation=oid, target=entry["target_name"],
                                                  pixel_area_arcsec2=float(exposure.area_factor[nearest] / (ARCSEC2_TO_SR * 1e12)),
                                                  association="unconfirmed", eligible_target_measurement=False,
                                                  unresolved_system=target_id in {"epsilon_indi_b", "rw_aurigae"}, **summary))
            candidates = gaia_candidates(exposure, catalogs.get(oid, {}).get("rows", []), midpoint, wcs, xy)
            results["gaia_candidates"].extend(dict(observation=oid, **item) for item in candidates)
            # Separated corner trials. SOURCE only screens the immediate core.
            for corner in ((4.75, 4.75), (4.75, 14.75), (14.75, 4.75), (14.75, 14.75)):
                yy, xx = np.indices(exposure.image.shape)
                if (np.hypot(corner[0] - xy[0], corner[1] - xy[1]) < 6
                        or exposure.source[np.hypot(xx - corner[0], yy - corner[1]) < 3.3].any()):
                    continue
                summary, candidate = describe(exposure, corner)
                if candidate is not None:
                    results["background_controls"].append(dict(observation=oid, **summary,
                                                                injections=injection_trials(exposure, corner)))
    results["catalog_queries"] = {key: dict(source=value.get("url"), rows=len(value["rows"]), status=value.get("status"))
                                  for key, value in catalogs.items()}
    screen = args.catalogs.with_name("patch_catalog_screen.json")
    if screen.is_file():
        patch_queries = json.loads(screen.read_text())
        results["patch_catalog_screen"] = {
            k: dict(url=v.get("url"), status=v.get("status"), rows=len(v["rows"])) for k, v in patch_queries.items()
        }
    results["wide_controls"] = wide_controls(args.catalogs.parent, area)
    args.output.write_text(json.dumps(results, indent=2, allow_nan=False), encoding="utf-8")
    for row in results["named_exposures"]:
        print(row["target"], row["observation"], row["core"], row["annulus"], row["status"],
              row.get("formal_snr"), row.get("reduced_chi2"))
    print(f'{len(results["background_controls"])} SOURCE-screened patch candidates, '
          f'{len(results["gaia_candidates"])} Gaia candidates')
    print(f"Diagnostics written to {args.output}")


if __name__ == "__main__":
    main()
