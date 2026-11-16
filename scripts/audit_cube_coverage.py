"""Audit four coordinate conventions per challenge target through the cube API."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import httpx
import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from fastapi.testclient import TestClient
from cube_audit_ranges import ArchiveTile, prime_tiles

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app
from app.services import cube_service
from app.services.demo_service import OFFICIAL_PRESETS


# Earlier DR1 exposure-midpoint comparison positions from docs/TARGET_VALIDATION.md.
EXPOSURE_REFERENCE = {
    "barnards_star": (269.4463524, 4.7671159, 60902.86687298),
    "epsilon_indi_b": (331.0953024, -56.8001865, 60794.06547892),
    "wise_0855": (133.7612618, -7.2423054, 60800.70218691),
    "rw_aurigae": (76.9565859, 30.4012930, 60935.92409930),
    "r_draconis": (248.1672422, 66.7550228, 60811.95649533),
}
STATUSES = ("measured", "no_coverage", "flagged", "blank_channel", "missing_wavelength")


def archive_url(tile):
    return ("https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/hips5_cube/hips_20261026/"
            f"Norder5/Dir{tile // 10000 * 10000}/Npix{tile}_cube.fits")


def verify_sample(cube, result, position):
    image = cube["IMAGE"]
    coords = WCS(image.header, fobj=cube, naxis=[1, 2])
    px, py = coords.all_world2pix(position.ra.deg, position.dec.deg, 0)
    x, y = int(np.floor(px + .5)), int(np.floor(py + .5))
    assert (result["ra"], result["dec"]) == (position.ra.deg, position.dec.deg)
    assert (x, y) == (result["pixel"]["x"], result["pixel"]["y"])
    np.testing.assert_allclose(coords.all_pix2world(x, y, 0),
                               [result["pixel"]["ra"], result["pixel"]["dec"]], atol=1e-9, rtol=0)
    table = cube["SPECTRAL_CHANNELS"]
    statuses = Counter()
    assert [row["channel"] for row in result["channels"]] == list(range(1, 103))
    for index, channel in enumerate(result["channels"]):
        row = table.data[index]
        detector, subchannel = int(row["DETECTOR"]), int(row["SUBCHAN"])
        assert (detector - 1) * 17 + subchannel == channel["channel"]
        assert (detector, subchannel) == (channel["detector"], channel["subchannel"])
        for source, target in (
            ("WAVELENGTH", "wavelength_um"), ("WL_MIN", "wavelength_min_um"),
            ("WL_MAX", "wavelength_max_um"), ("BANDWIDTH", "bandwidth_um"),
        ):
            value = float(row[source])
            expected = value * u.Unit(table.columns[source].unit).to(u.um) if np.isfinite(value) else None
            assert channel[target] == expected
        raw = float(image.section[index, y, x])
        value = raw if np.isfinite(raw) else None
        n = int(cube["NHITS"].section[index, y, x])
        bits = int(cube["FLAGS"].section[index, y, x]) & 0xFFFFFFFF
        assert (channel["archive_brightness_mjy_sr"], channel["hits"], channel["flags"]) == (value, n, bits)
        if index + 1 in (51, 52):
            status = "blank_channel"
        elif value is None or n <= 0:
            status = "no_coverage"
        elif bits & 0xFFDFFFFF:
            status = "flagged"
        elif channel["wavelength_um"] is None:
            status = "missing_wavelength"
        else:
            status = "measured"
        assert channel["status"] == status
        assert channel["surface_brightness_mjy_sr"] == (value if status == "measured" else None)
        statuses[status] += 1
    channel_map = result["channel_map"]
    selected = result["channels"][channel_map["channel"] - 1]
    assert channel_map["pixels"][channel_map["center_y"]][channel_map["center_x"]] == selected["surface_brightness_mjy_sr"]
    return {status: statuses[status] for status in STATUSES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", default="http://127.0.0.1:15173")
    parser.add_argument("--cache", type=Path, default=ROOT / "data/cache/cube_coverage")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/verification/cube-coverage.json")
    parser.add_argument("--only", choices=EXPOSURE_REFERENCE)
    parser.add_argument("--archive-ranges", action="store_true",
                        help="Read exact native samples from the public mirror for missing local FITS tiles.")
    args = parser.parse_args()
    reference = json.loads((ROOT / "data/manifests/target_astrometry.json").read_text(encoding="utf-8"))
    presets = httpx.get(f"{args.preview}/api/demo", timeout=15).raise_for_status().json()
    requests = []
    for preset in presets:
        key = preset["id"]
        if args.only and args.only != key:
            continue
        original = next(row for row in OFFICIAL_PRESETS if row.id == key)
        ra, dec, mjd = EXPOSURE_REFERENCE[key]
        for label, coordinates, epoch in (
            ("preview_preset", (preset["ra"], preset["dec"]), "Latest covered preview position"),
            ("configured_default", (original.ra, original.dec), "Configured search coordinate"),
            ("catalog_j2000", (reference[key]["ra"], reference[key]["dec"]), "ICRS J2000"),
            ("dr1_exposure_prediction", (ra, dec), f"Dated FITS MJD-AVG {mjd:.8f}"),
        ):
            position = SkyCoord(*coordinates, unit="deg")
            tile = int(cube_service.HEALPIX.skycoord_to_healpix(position))
            requests.append(dict(target=preset["name"], id=key, kind=label, ra=coordinates[0],
                                 dec=coordinates[1], coordinate_reference=epoch, tile=tile))
    paths = {}
    sources = {}
    remote = {}
    positions = {}
    mirror = httpx.Client(timeout=25, limits=httpx.Limits(max_connections=24, max_keepalive_connections=24))
    for row in requests:
        positions.setdefault(row["tile"], []).append(SkyCoord(row["ra"], row["dec"], unit="deg"))
    for tile in sorted({row["tile"] for row in requests}):
        url = archive_url(tile)
        path = args.cache / "dr1_cube" / (hashlib.sha256(url.encode()).hexdigest() + ".fits")
        if not path.is_file() and args.archive_ranges:
            remote[tile] = ArchiveTile(mirror, url)
            with fits.open(remote[tile].reader(), memmap=False) as cube:
                sources[tile] = dict(url=url, mirror=remote[tile].url, bytes=remote[tile].length,
                                     etag=remote[tile].etag, retrieval="verified HTTP ranges",
                                     date_beg=cube[0].header["DATE-BEG"], date_end=cube[0].header["DATE-END"])
            continue
        with path.open("rb") as handle:
            checksum = hashlib.file_digest(handle, "sha256").hexdigest()
        with fits.open(path, memmap=True) as cube:
            sources[tile] = dict(url=url, sha256=checksum, bytes=path.stat().st_size,
                                 date_beg=cube[0].header["DATE-BEG"], date_end=cube[0].header["DATE-END"])
        paths[tile] = path
    prime_tiles(remote, positions)

    def query(row, channel=3):
        with TestClient(app) as client:
            return client.get("/api/cube/spectrum", params={"ra": row["ra"], "dec": row["dec"], "channel": channel})

    class VerifiedTileLookup(BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlsplit(self.path).query)
            assert params["COLLECTION"] == ["spherex_dr1_cube"]
            _, ra, dec, _ = params["POS"][0].split()
            tile = int(cube_service.HEALPIX.skycoord_to_healpix(SkyCoord(float(ra), float(dec), unit="deg")))
            if tile not in sources:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.end_headers()
            self.wfile.write(f"access_url\n{sources[tile]['url']}\n".encode())

        def log_message(self, *_args):
            pass

    original_cache = cube_service._cache_tile

    def audit_cache(client, url, directory):
        tile = next(index for index, source in sources.items() if source["url"] == url)
        if tile in remote:
            return remote[tile].reader()
        return original_cache(client, url, directory)

    with ExitStack() as checks:
        checks.enter_context(patch.object(cube_service, "CACHE_DIR", args.cache))
        if remote:
            checks.enter_context(patch.object(cube_service, "_cache_tile", audit_cache))
        pool = checks.enter_context(ThreadPoolExecutor(max_workers=5))
        direct = list(pool.map(query, requests))
        with ThreadingHTTPServer(("127.0.0.1", 0), VerifiedTileLookup) as metadata:
            server = Thread(target=metadata.serve_forever, daemon=True)
            server.start()
            try:
                with patch.object(cube_service, "IRSA_SIA_BASE_URL", f"http://127.0.0.1:{metadata.server_port}"):
                    results = [response if response.is_success else query(row)
                               for row, response in zip(requests, direct, strict=True)]
                    channel_one = {row["id"]: query(row, 1).json()
                                   for row in requests if row["kind"] == "preview_preset"}
            finally:
                metadata.shutdown()
                server.join()
    for row, live, response in zip(requests, direct, results, strict=True):
        row["live_http_status"] = live.status_code
        row["live_error"] = None if live.is_success else live.json()["detail"]
        row["api_lookup"] = "live SIA" if live.is_success else "locally supplied verified archive tile URL"
        assert response.is_success, response.text
        result = response.json()
        assert result["tile"] == row["tile"] and result["fits_url"] == sources[row["tile"]]["url"]
        tile = row["tile"]
        with fits.open(remote[tile].reader() if tile in remote else paths[tile], memmap=tile not in remote) as cube:
            row["counts"] = verify_sample(cube, result, SkyCoord(row["ra"], row["dec"], unit="deg"))
            if row["kind"] == "preview_preset":
                row["api_channel_1"] = channel_one[row["id"]]
                assert verify_sample(cube, row["api_channel_1"], SkyCoord(row["ra"], row["dec"], unit="deg")) == row["counts"]
        row["api"] = result
        print(row["id"], row["kind"], row["tile"], result["pixel"]["x"], result["pixel"]["y"],
              row["counts"], "live", row["live_http_status"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"tiles": sources, "samples": requests}, allow_nan=False, indent=2) + "\n",
                           encoding="utf-8")
    mirror.close()


if __name__ == "__main__":
    main()
