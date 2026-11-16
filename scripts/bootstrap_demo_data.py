"""Install only the checksum-pinned FITS inputs for the ten-frame preview."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile
from urllib.parse import parse_qsl, urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = "irsa.ipac.caltech.edu"
ARCHIVE_PATH = "/ibe/data/spherex/"
MIRROR = "https://nasa-irsa-spherex.s3.amazonaws.com"


class BootstrapError(ValueError):
    pass


def file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify_file(path: Path, size: int, checksum: str) -> bool:
    if not path.exists():
        return False
    if not path.is_file() or path.stat().st_size != size or file_sha256(path) != checksum:
        raise BootstrapError("Existing bytes fail verification. Move the affected file aside before retrying.")
    return True


@dataclass(frozen=True)
class Asset:
    path: Path
    url: str
    size: int
    sha256: str
    legacy: Path | None = None
    secondary_url: str | None = None

    def present(self, root: Path) -> bool:
        return verify_file(root / self.path, self.size, self.sha256) or (
            self.legacy is not None and verify_file(root / self.legacy, self.size, self.sha256)
        )


def cutout_asset(row: dict, directory: Path) -> Asset:
    url = row["url"]
    name = hashlib.sha256(url.encode()).hexdigest() + ".fits"
    alternate = row.get("alternate_url")
    if alternate is not None:
        primary, secondary = urlsplit(url), urlsplit(alternate)
        if (secondary._replace(query="") != primary._replace(query="")
                or sorted(parse_qsl(primary.query)) != sorted(parse_qsl(secondary.query))):
            raise BootstrapError("Alternate cutout URL requests different archive data.")
    return Asset(directory / name, url, row["bytes"], row["sha256"], secondary_url=alternate)


def calibration_asset(row: dict) -> Asset:
    name = f"spectral-{row['md5']}.fits"
    directory = Path("data/cache")
    url = row["url"]
    return Asset(directory / "spectral-calibration" / name, url, row["bytes"], row["sha256"],
                 directory / name, f"{MIRROR}/{urlsplit(url).path.removeprefix(ARCHIVE_PATH)}")


def load_plan(root: Path, comparisons: bool) -> tuple[list[Asset], list[Asset], bytes]:
    manifests = root / "data/manifests"
    pin_file = manifests / "demo_preview_assets.json"
    if not pin_file.is_file():
        raise BootstrapError("Missing checkout file: data/manifests/demo_preview_assets.json. Restore the release copy.")
    pins = json.loads(pin_file.read_text(encoding="utf-8"))
    if pins["schema"] != 1:
        raise BootstrapError("Unsupported preview asset manifest schema.")
    for name, field in (
        ("demo_preview.json", "preview_manifest_sha256"),
        ("cube_preview.json.gz", "cube_sha256"),
        ("cube_preview_sources.json", "cube_sources_sha256"),
    ):
        if not (manifests / name).is_file() or file_sha256(manifests / name) != pins[field]:
            raise BootstrapError(f"Missing or invalid checkout file: data/manifests/{name}. Restore the release copy.")
    manifest_bytes = (manifests / "demo_preview.json").read_bytes()
    rows = json.loads(manifest_bytes.decode("utf-8-sig"))
    if len(rows) != 10 or [row["cutout_url"] for row in rows] != [row["url"] for row in pins["preview"]]:
        raise BootstrapError("The ten-frame preview and its download pins disagree.")

    base = [cutout_asset(row, Path("data/cache/demo_multiepoch")) for row in pins["preview"]]
    extension = []
    if comparisons:
        pair = json.loads((manifests / "d5_comparison.json").read_text(encoding="utf-8"))
        if [(r["cutout_url"], r["sha256"]) for r in pair] != [(r["url"], r["sha256"]) for r in pins["d5_cutouts"]]:
            raise BootstrapError("The D5 pair and its download pins disagree.")
        extension = [cutout_asset(row, Path("data/cache/demo-comparison")) for row in pins["d5_cutouts"]]
        extension.extend(calibration_asset(row) for row in pins["calibration"].values())
    for asset in base + extension:
        url = urlsplit(asset.url)
        if (url.scheme, url.netloc) != ("https", ARCHIVE) or not url.path.startswith(ARCHIVE_PATH):
            raise BootstrapError("A download pin points outside the public IRSA archive.")
    return base, extension, manifest_bytes


def install_verified(temporary: Path, destination: Path, size: int, checksum: str) -> None:
    if not verify_file(temporary, size, checksum):
        raise BootstrapError("Verified candidate is missing.")
    try:
        os.link(temporary, destination)
    except FileExistsError:
        if not verify_file(destination, size, checksum):
            raise BootstrapError("Another process changed the destination during installation.")


def fetch_asset(root: Path, asset: Asset, client: httpx.Client) -> str:
    try:
        if asset.present(root):
            return "cached"
    except BootstrapError as exc:
        raise BootstrapError(f"{asset.path.as_posix()}: {exc}") from exc
    destination = root / asset.path
    destination.parent.mkdir(parents=True, exist_ok=True)
    failures = []
    for url in (asset.url, asset.secondary_url or asset.url, asset.url):
        temporary = None
        try:
            with NamedTemporaryFile(dir=destination.parent, suffix=".pending", delete=False) as handle:
                temporary = Path(handle.name)
                total = 0
                with client.stream("GET", url, headers={"Accept-Encoding": "identity"}) as response:
                    response.raise_for_status()
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > asset.size:
                            raise BootstrapError("archive response exceeded its pinned size")
                        handle.write(chunk)
            try:
                install_verified(temporary, destination, asset.size, asset.sha256)
            except BootstrapError as exc:
                raise BootstrapError("archive bytes did not match the pinned size or SHA-256") from exc
            return "downloaded"
        except httpx.HTTPStatusError as exc:
            failures.append(f"HTTP {exc.response.status_code}")
        except (httpx.RequestError, BootstrapError) as exc:
            failures.append(str(exc) if isinstance(exc, BootstrapError) else type(exc).__name__)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    raise BootstrapError(
        f"{asset.path.as_posix()}: public archive download failed ({', '.join(failures)}). "
        "Connect to the Internet or retry when IRSA is available. Already verified files were retained."
    )


def seed_manifest(root: Path, content: bytes, check_only: bool) -> bool:
    path = root / "data/cache/demo_multiepoch/demo_dataset.json"
    sha256 = hashlib.sha256(content).hexdigest()
    try:
        if verify_file(path, len(content), sha256):
            return True
    except BootstrapError as exc:
        raise BootstrapError(f"data/cache/demo_multiepoch/demo_dataset.json: {exc}") from exc
    if check_only:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(dir=path.parent, suffix=".pending", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        install_verified(temporary, path, len(content), sha256)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-comparisons", action="store_true", help="Also stage the D5 pair and pinned D5/D6 maps.")
    parser.add_argument("--check-only", action="store_true", help="Verify files without downloading or writing.")
    args = parser.parse_args()
    try:
        base, extension, manifest_bytes = load_plan(ROOT, args.with_comparisons)
        if args.check_only:
            missing = []
            if not seed_manifest(ROOT, manifest_bytes, True):
                missing.append("data/cache/demo_multiepoch/demo_dataset.json")
            for asset in base + extension:
                try:
                    if not asset.present(ROOT):
                        missing.append(asset.path.as_posix())
                except BootstrapError as exc:
                    raise BootstrapError(f"{asset.path.as_posix()}: {exc}") from exc
            if missing:
                print("Missing preview inputs:\n" + "\n".join(missing), file=sys.stderr)
                command = "python scripts/bootstrap_demo_data.py"
                if args.with_comparisons:
                    command += " --with-comparisons"
                print(f"Run {command} with network access to stage the exact bytes.", file=sys.stderr)
                return 1
        else:
            # Refuse conflicting local manifest bytes before starting downloads.
            seed_manifest(ROOT, manifest_bytes, True)
            with httpx.Client(timeout=httpx.Timeout(35, connect=8), follow_redirects=False) as client:
                with ThreadPoolExecutor(max_workers=4) as pool:
                    for assets in (base, extension):
                        for asset, result in zip(assets, pool.map(lambda item: fetch_asset(ROOT, item, client), assets), strict=True):
                            print(f"{result}: {asset.path.as_posix()}")
                        if assets is base:
                            seed_manifest(ROOT, manifest_bytes, False)
    except (OSError, ValueError, KeyError) as exc:
        detail = exc.strerror if isinstance(exc, OSError) else str(exc)
        print(f"Demo bootstrap failed: {detail or type(exc).__name__}", file=sys.stderr)
        return 1
    print(f"Verified ten-frame preview, compact cube provenance, and {len(extension)} comparison assets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
