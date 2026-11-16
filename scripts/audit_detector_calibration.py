"""Produce the detector/release calibration audit from the preserved motion inputs."""
from collections import defaultdict
from contextlib import ExitStack
import csv
import hashlib
import json

from astropy.io import fits
import numpy as np

from study_motion_multidetector import DETECTORS, WORK, inspect
from study_motion_preflight import ROOT, WAVE_ID, WAVE_MD5
from app.science.calibrated_comparison import compare_calibrated_pair, prepare_calibrated_exposure

CONTROL = {
    "2025W18_1B_0242_2": "7a8fce4b3cc373bac5a2fbdd797179081659328c73d2fd6ccf9070f9fa9a0a40",
    "2025W18_1B_0252_2": "2e2bee0c50abb4b0afdb5a856fd03dc773beeb70a8f6d45f103e54f2bb03c3c6",
}


def alignment_counts(a, b):
    yy, xx = np.indices(a.image.shape)
    px, py = b.wcs.world_to_pixel(a.wcs.pixel_to_world(xx, yy))
    h, w = b.image.shape
    common = (px >= -.5) & (px < w - .5) & (py >= -.5) & (py < h - .5)
    ix = np.floor(px[common] + .5).astype(int)
    iy = np.floor(py[common] + .5).astype(int)
    nearest = np.hypot(px[common] - ix, py[common] - iy) <= .5
    valid = a.usable()[common] & b.usable()[iy, ix]
    c1, c2 = a.wavelength[common], b.wavelength[iy, ix]
    w1, w2 = a.bandwidth[common], b.bandwidth[iy, ix]
    overlap = (np.minimum(c1 + w1 / 2, c2 + w2 / 2) - np.maximum(c1 - w1 / 2, c2 - w2 / 2)) / np.maximum(w1, w2)
    try:
        result = compare_calibrated_pair(a, b, minimum_passband_overlap=.9)
        accepted = result["retained_pixels"]
        failure = None
    except ValueError as exc:
        accepted, failure = 0, str(exc)
    return dict(reference_pixels=a.image.size, common=int(common.sum()),
                within_half_pixel=int(nearest.sum()), usable_within_half_pixel=int((nearest & valid).sum()),
                meeting_overlap_before_duplicate_gate=int((nearest & valid & (overlap >= .9 - 1e-12)).sum()),
                accepted=accepted, excluded_reference_pixels=a.image.size - accepted, reason=failure)


def check_control(maps):
    paths = {key: ROOT / f"data/cache/{value}.fits" for key, value in CONTROL.items()}
    if not all(path.is_file() for path in paths.values()):
        return {"status": "cached D6 control unavailable"}
    with ExitStack() as stack:
        exposures = []
        for obs, path in paths.items():
            science = stack.enter_context(fits.open(path))
            if science["IMAGE"].header["OBSID"] != obs:
                raise ValueError("Unexpected observation in cached control")
            exposures.append(prepare_calibrated_exposure(science, maps, plane_id=WAVE_ID, checksum=WAVE_MD5))
        return dict(observations=list(paths), **alignment_counts(*exposures))


def main():
    artifact = ROOT / f"data/cache/spectral-{WAVE_MD5}.fits"
    maps = artifact.read_bytes()
    assert hashlib.md5(maps).hexdigest() == WAVE_MD5
    with fits.open(artifact) as hdul:
        shapes = {name: list(hdul[name].data.shape) for name in ("CWAVE", "CBAND")}
        detectors = {str(hdul[name].header["DETECTOR"]) for name in shapes}
        units = {name: hdul[name].header["BUNIT"] for name in shapes}
        assert detectors == {"6"} and all(shape == [2040, 2040] for shape in shapes.values())
    cutouts = json.loads((WORK / "cutouts.json").read_text())
    catalog = json.loads((WORK / "catalog.json").read_text())
    artifacts = json.loads((WORK / "calibration_artifacts.json").read_text())
    trials = defaultdict(list)
    pairs = []
    for first, second in zip(cutouts[::2], cutouts[1::2]):
        (a, ex_a), (b, ex_b) = (inspect(row, catalog, None, artifacts) for row in (first, second))
        for summary in (a, b):
            trials[(summary["detector"], summary["release"])].append(summary)
        counts = alignment_counts(ex_a, ex_b) if ex_a is not None and ex_b is not None else None
        pairs.append(dict(source=first["target"], endpoints=[a, b], comparison_counts=counts))

    rows = []
    for detector in DETECTORS:
        for release in ("spherex_dr1", "spherex_qr3"):
            records = trials[detector, release]
            readable = [r for r in records if r.get("fits_sha256")]
            verified = [r for r in records if r.get("calibration_md5")]
            rows.append(dict(detector=detector, release=release, selected=len(records),
                             available_fits=len(readable),
                             calibrated=len(verified),
                             status="verified" if readable and len(verified) == len(readable) else "unresolved",
                             science_sample="readable subset" if readable else "no selected FITS returned",
                             plane_ids=" | ".join(sorted({r["plane_id"] for r in records if "plane_id" in r})),
                             checksums=" | ".join(sorted({r["calibration_md5"] for r in verified}))))
    with (WORK / "calibration_coverage.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (WORK / "calibration_coverage.json").write_text(json.dumps(dict(
        d6=dict(plane_id=WAVE_ID, md5=WAVE_MD5, bytes=artifact.stat().st_size, shapes=shapes, units=units),
        coverage=rows, pairs=pairs, d6_control=check_control(maps)), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
