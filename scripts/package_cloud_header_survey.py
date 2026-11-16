"""Package an attributed, locally verified S3 header survey (not a sky search)."""
import gzip
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from datetime import timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.cloud_cutout import cloud_url_from_irsa, expected_image_identity

if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != "wise"):
    raise SystemExit("Usage: python scripts/package_cloud_header_survey.py SURVEY.json [wise]")
index_name = "cloud_header_index_wise" if len(sys.argv) == 3 else "cloud_header_index"
raw = Path(sys.argv[1]).read_bytes()
survey = json.loads(raw)
verified_at = datetime.fromisoformat(survey["utc_checked"])
if verified_at.tzinfo is None or survey["list_endpoint"] != "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/":
    raise ValueError("Cloud survey timestamp or source is invalid")
ra, dec = map(float, survey["position"])
if not (math.isfinite(ra) and math.isfinite(dec) and 0 <= ra < 360 and -90 <= dec <= 90):
    raise ValueError("Invalid surveyed position")
selected = []
for record in survey["records"]:
    if not record.get("inside"):
        continue
    key, name, detector = record["key"], record["obs_id"], record["detector"]
    url = "https://irsa.ipac.caltech.edu/ibe/data/spherex/" + key
    if expected_image_identity(url) != (name, detector) or cloud_url_from_irsa(url) != survey["list_endpoint"].rstrip("/") + "/" + key:
        raise ValueError("Cloud path and FITS observation identity do not match")
    x, y = record["pixel"]
    height, width = record["shape"]
    residual = float(record["inverse_roundtrip_arcsec"])
    if not all(map(math.isfinite, (x, y, record["mjd"], residual))) or not (0 <= residual <= .01 and 5 < x < width - 6 and 5 < y < height - 6):
        raise ValueError("Cloud footprint has insufficient verified edge margin")
    if not isinstance(record.get("etag"), str) or not record["etag"]:
        raise ValueError("Cloud object identity is missing")
    selected.append({key: record[key] for key in ("key", "obs_id", "detector", "mjd", "pixel", "shape", "etag", "inverse_roundtrip_arcsec")})
if not selected:
    raise ValueError("No verified covering observations")
selected.sort(key=lambda row: (row["mjd"], row["detector"], row["obs_id"]))
payload = {"source": survey.get("source_description", "NASA IRSA public SPHEREx S3 object listings and FITS headers"),
           "verified_at_utc": survey["utc_checked"], "saved_date_utc": verified_at.astimezone(timezone.utc).date().isoformat(),
           "position": [ra, dec], "list_endpoint": survey["list_endpoint"],
           "prefixes": survey["prefixes"], "objects_checked": len(survey["records"]),
           "checks_failed": sum("error" in row for row in survey["records"]),
           "note": "Partial targeted survey, not a complete search or proof of target identity. Parent-image WCS covers the indexed sky coordinate; cutout availability is separate.",
           "records": selected}
compressed = gzip.compress(json.dumps(payload, separators=(",", ":"), allow_nan=False).encode(), mtime=0)
dest = ROOT / "data/manifests"
(dest / f"{index_name}.json.gz").write_bytes(compressed)
(dest / f"{index_name}_evidence.json.gz").write_bytes(gzip.compress(raw, mtime=0))
(dest / f"{index_name}_sources.json").write_text(json.dumps({
    "sha256": hashlib.sha256(compressed).hexdigest(), "evidence_sha256": hashlib.sha256(raw).hexdigest(),
    "verified_at_utc": survey["utc_checked"], "records": len(selected),
    "source": payload["source"], "note": payload["note"]}, indent=2) + "\n", encoding="utf-8")
print(f"Packaged {len(selected)} verified parent-image footprints; this is a partial survey.")
