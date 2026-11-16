"""Package an attributed historical IRSA SIA search snapshot; never downloads data."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "data" / "manifests"


def validate_request(request: str) -> str:
    parsed = urlparse(request)
    if parsed.scheme != "https" or parsed.hostname != "irsa.ipac.caltech.edu" or parsed.path != "/SIA":
        raise ValueError("Each job must contain its original HTTPS IRSA SIA request")
    query = parse_qs(parsed.query)
    collection = query.get("COLLECTION", [""])[0]
    position = query.get("POS", [""])[0].split()
    if collection not in {"spherex_dr1", "spherex_qr3"} or len(position) != 4 or position[0].lower() != "circle":
        raise ValueError("The original request must identify a supported collection and circle position")
    try:
        ra, dec, radius = map(float, position[1:])
    except ValueError as exc:
        raise ValueError("Invalid circle coordinates in original request") from exc
    if not all(map(math.isfinite, (ra, dec, radius))) or not (0 <= ra < 360 and -90 <= dec <= 90 and 0 < radius <= 180):
        raise ValueError("Invalid circle coordinates in original request")
    return collection


def usable_row(row) -> bool:
    if not isinstance(row, dict):
        return False
    try:
        valid_time = math.isfinite(float(row.get("t_min", "")))
    except (TypeError, ValueError):
        return False
    return bool(isinstance(row.get("obs_id"), str) and row["obs_id"].strip()
                and isinstance(row.get("energy_bandpassname"), str) and row["energy_bandpassname"].strip() and valid_time
                and isinstance(row.get("access_url"), str)
                and row["access_url"].startswith("https://irsa.ipac.caltech.edu/ibe/data/spherex/"))


def csv_search(raw: bytes, request: str) -> list:
    """Wrap an IRSA SIA CSV with its original query; it contains no image data."""
    collection = validate_request(request)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    fields = {"obs_id", "energy_bandpassname", "t_min", "access_url"}
    if not reader.fieldnames or not fields.issubset(reader.fieldnames):
        raise ValueError("CSV must contain obs_id, energy_bandpassname, t_min and access_url")
    rows = list(reader)
    if not rows:
        raise ValueError("The CSV has no observation rows; existing snapshots were not changed")
    if not any(usable_row(row) for row in rows):
        raise ValueError("No CSV rows have usable IRSA image URLs and observation metadata; nothing was changed")
    return [{"job": ["csv_import", collection], "request": request, "rows": rows}]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="JSON array of SIA jobs, or an IRSA SIA CSV when --csv-request is supplied")
    parser.add_argument("--saved-date", required=True, help="Date the source snapshot was saved (YYYY-MM-DD)")
    parser.add_argument("--csv-request", help="Original HTTPS IRSA SIA request URL for this CSV, including COLLECTION and POS")
    parser.add_argument("--append", action="store_true", help="Preserve the verified existing snapshot and add the new searches")
    args = parser.parse_args()
    date.fromisoformat(args.saved_date)
    raw = args.source.read_bytes()
    searches = csv_search(raw, args.csv_request) if args.csv_request else json.loads(raw)
    if not isinstance(searches, list) or not searches:
        raise ValueError("Expected a non-empty array of search jobs")
    compact = []
    skipped_rows = 0
    for search in searches:
        request = search.get("request", "")
        collection = validate_request(request)
        job, rows = search.get("job"), search.get("rows")
        if not isinstance(job, list) or len(job) < 2 or job[1] != collection or not isinstance(rows, list):
            raise ValueError("Each job needs a collection matching its request and a list of results")
        if not all(isinstance(row, dict) for row in rows):
            raise ValueError("Every result row must be a JSON object")
        fields = ("obs_id", "energy_bandpassname", "t_min", "access_url")
        accepted_rows = [row for row in rows if usable_row(row)]
        skipped_rows += len(rows) - len(accepted_rows)
        compact.append({"job": job, "request": request, "saved_date_local": args.saved_date,
                        "rows": [{key: row.get(key) for key in fields} for row in accepted_rows]})
    if not any(usable_row(row) for search in compact for row in search["rows"]):
        raise ValueError("No usable observation rows; existing snapshots were not changed")
    prior_hash = None
    if args.append:
        old_bytes = (DEST / "observation_search_snapshot.json.gz").read_bytes()
        old_metadata = json.loads((DEST / "observation_search_snapshot_sources.json").read_text(encoding="utf-8"))
        prior_hash = hashlib.sha256(old_bytes).hexdigest()
        if prior_hash != old_metadata.get("snapshot_sha256"):
            raise ValueError("Existing snapshot checksum does not match its metadata; nothing was changed")
        old_searches = json.loads(gzip.decompress(old_bytes))
        if not isinstance(old_searches, list):
            raise ValueError("Existing snapshot is invalid; nothing was changed")
        for search in old_searches:
            search.setdefault("saved_date_local", old_metadata.get("saved_date_local"))
        compact = old_searches + compact
    payload = json.dumps(compact, separators=(",", ":")).encode("utf-8")
    compressed = gzip.compress(payload, mtime=0)
    metadata = {"saved_date_local": args.saved_date, "date_basis": "user-supplied snapshot save date; individual query timestamps may be unavailable", "source_file_sha256": hashlib.sha256(raw).hexdigest(), "snapshot_sha256": hashlib.sha256(compressed).hexdigest(), "searches": len(compact), "rows_before_deduplication": sum(len(job["rows"]) for job in compact), "note": "Historical IRSA SIA search metadata only; not FITS images. Coverage, availability and completeness require separate checks."}
    metadata["incoming_rows_skipped"] = skipped_rows
    if prior_hash:
        metadata["previous_snapshot_sha256"] = prior_hash
        metadata["date_basis"] = "user-supplied date of newest added snapshot; earlier searches may be older"
        metadata["sources"] = old_metadata.get("sources", [{
            "source_file_sha256": old_metadata.get("source_file_sha256"),
            "saved_date_local": old_metadata.get("saved_date_local"),
            "date_basis": old_metadata.get("date_basis"),
        }]) + [{"source_file_sha256": hashlib.sha256(raw).hexdigest(),
               "saved_date_local": args.saved_date,
               "date_basis": "user-supplied date of this imported snapshot"}]
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "observation_search_snapshot.json.gz").write_bytes(compressed)
    (DEST / "observation_search_snapshot_sources.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Packaged {metadata['searches']} searches and {metadata['rows_before_deduplication']} result rows; skipped {skipped_rows} unusable incoming rows. Review provenance before distribution.")


if __name__ == "__main__":
    main()
