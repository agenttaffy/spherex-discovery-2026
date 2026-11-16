"""Check two archived science cutouts without enabling public image arithmetic."""

import argparse
import json
import ssl
import sys
from pathlib import Path

import certifi
import httpx
from astropy.io import fits

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.science.calibrated_comparison import compare_calibrated_pair, prepare_calibrated_exposure
from app.services.spectral_calibration_service import find_calibration_artifact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("comparison", type=Path)
    parser.add_argument("--reference-release", required=True, choices=("dr1", "qr3", "qr2"))
    parser.add_argument("--comparison-release", required=True, choices=("dr1", "qr3", "qr2"))
    parser.add_argument("--minimum-overlap", type=float, required=True)
    args = parser.parse_args()

    ssl_context = ssl.create_default_context(cafile=certifi.where())
    exposures, provenance = [], []
    downloads = {}
    with httpx.Client(verify=ssl_context, timeout=httpx.Timeout(90, connect=10)) as client:
        for path, release in (
            (args.reference, args.reference_release),
            (args.comparison, args.comparison_release),
        ):
            with fits.open(path, memmap=False) as science:
                header = science["IMAGE"].header
                observation = header.get("OBSID")
                if not observation or any(item["observation"] == observation for item in provenance):
                    parser.error("Two distinct observation IDs are required")
                artifact = find_calibration_artifact(client, science, release)
                if artifact.url not in downloads:
                    response = client.get(artifact.url)
                    response.raise_for_status()
                    downloads[artifact.url] = response.content
                exposures.append(prepare_calibrated_exposure(
                    science, downloads[artifact.url],
                    plane_id=artifact.plane_id, checksum=artifact.checksum,
                ))
                provenance.append({
                    "file": str(path),
                    "observation": observation,
                    "calibration_plane": artifact.plane_id,
                    "calibration_url": artifact.url,
                    "calibration_md5": artifact.checksum,
                })

    try:
        result = compare_calibrated_pair(*exposures, minimum_passband_overlap=args.minimum_overlap)
    except ValueError as error:
        print(json.dumps({"accepted": False, "reason": str(error), "inputs": provenance}, indent=2))
        sys.exit(1)

    metrics = {key: value for key, value in result.items()
               if key not in {"difference", "difference_variance", "mean", "mean_variance"}}
    print(json.dumps({"accepted": True, **metrics, "inputs": provenance}, indent=2))


if __name__ == "__main__":
    main()
