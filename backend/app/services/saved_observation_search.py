"""Use an earlier IRSA search only near its recorded position during an outage."""
import gzip
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from astropy.time import Time

from app.config import MANIFESTS_DIR
from app.models.schemas import ObservationRecord
from app.services.irsa_client import OBSERVATION_REGISTRY

SNAPSHOT = MANIFESTS_DIR / "observation_search_snapshot.json.gz"
SNAPSHOT_SOURCES = MANIFESTS_DIR / "observation_search_snapshot_sources.json"
CLOUD_INDEX = MANIFESTS_DIR / "cloud_header_index.json.gz"
CLOUD_INDEX_SOURCES = MANIFESTS_DIR / "cloud_header_index_sources.json"
WISE_CLOUD_INDEX = MANIFESTS_DIR / "cloud_header_index_wise.json.gz"
WISE_CLOUD_INDEX_SOURCES = MANIFESTS_DIR / "cloud_header_index_wise_sources.json"


def cloud_header_observations(ra: float, dec: float, collection: str,
                              detector: str | None, limit: int) -> list[ObservationRecord]:
    """Use only a checksummed, explicitly partial survey at its indexed coordinate."""
    for path, sources in ((CLOUD_INDEX, CLOUD_INDEX_SOURCES), (WISE_CLOUD_INDEX, WISE_CLOUD_INDEX_SOURCES)):
        records = _cloud_header_observations(path, sources, ra, dec, collection, detector, limit)
        if records:
            return records
    return []


def _cloud_header_observations(path: Path, sources: Path, ra: float, dec: float, collection: str,
                               detector: str | None, limit: int) -> list[ObservationRecord]:
    from app.services.cloud_cutout import expected_image_identity
    try:
        packed = path.read_bytes()
        provenance = json.loads(sources.read_text(encoding="utf-8"))
        if hashlib.sha256(packed).hexdigest() != provenance["sha256"]:
            return []
        index = json.loads(gzip.decompress(packed))
        source_ra, source_dec = map(float, index["position"])
        delta_ra = ((ra - source_ra + 180) % 360 - 180) * math.cos(math.radians(source_dec))
        if math.hypot(delta_ra, dec - source_dec) > .00015:
            return []
        records = []
        for row in index["records"]:
            key, obs_id, detector_id = row["key"], row["obs_id"], str(row["detector"])
            release = key.split("/", 1)[0]
            if collection != f"spherex_{release}":
                continue
            band = f"SPHEREx-D{detector_id}"
            if detector and detector.upper() != "ALL" and detector.lower() != band.lower():
                continue
            url = f"https://irsa.ipac.caltech.edu/ibe/data/spherex/{key}"
            if expected_image_identity(url) != (obs_id, detector_id):
                return []
            mjd = float(row["mjd"])
            if not math.isfinite(mjd):
                return []
            record_id = f"cloud_header_{release}_{obs_id}_D{detector_id}__at_{ra:.6f}_{dec:.6f}"
            record = ObservationRecord(id=record_id, obs_id=obs_id, collection=collection,
                detector=band, mjd=mjd, utc_date=Time(mjd, format="mjd").utc.isot,
                access_url=url, ra=ra, dec=dec, search_provenance="cloud_header_survey",
                search_snapshot_saved=index["saved_date_utc"])
            records.append(record)
        records.sort(key=lambda record: record.mjd)
        if len(records) > limit:
            records = ([records[round(i * (len(records) - 1) / (limit - 1))] for i in range(limit)]
                       if limit > 1 else records[:1])
        for record in records:
            OBSERVATION_REGISTRY[record.id] = record.model_dump()
        return records
    except (OSError, ValueError, TypeError, KeyError, IndexError, EOFError):
        return []


def saved_observations(ra: float, dec: float, radius: float, collection: str,
                       detector: str | None, limit: int) -> list[ObservationRecord]:
    try:
        if SNAPSHOT.suffix == ".gz":
            with gzip.open(SNAPSHOT, "rt", encoding="utf-8") as stream:
                searches = json.load(stream)
        else:
            searches = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, ValueError, EOFError):
        return []
    try:
        packaged = SNAPSHOT.parent == SNAPSHOT_SOURCES.parent
        metadata = json.loads(SNAPSHOT_SOURCES.read_text(encoding="utf-8")) if packaged else {}
        expected_hash = metadata.get("snapshot_sha256")
        if packaged and (not isinstance(expected_hash, str) or len(expected_hash) != 64
                         or hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() != expected_hash):
            return []
        snapshot_saved = metadata.get("saved_date_local")
    except (OSError, ValueError):
        return []
    rows = {}
    for search in searches:
        search_saved = search.get("saved_date_local") or snapshot_saved
        if search.get("job", [None, None])[1] != collection:
            continue
        pos = parse_qs(urlparse(search.get("request", "")).query).get("POS", [""])[0].split()
        if len(pos) != 4 or pos[0].lower() != "circle":
            continue
        try:
            old_ra, old_dec, old_radius = map(float, pos[1:])
            separation = math.hypot(((ra - old_ra + 180) % 360 - 180) * math.cos(math.radians(dec)), dec - old_dec)
        except ValueError:
            continue
        # This snapshot describes the tiny original search region, not arbitrary nearby skies.
        if separation > 0.00015 or radius < old_radius:
            continue
        for row in search.get("rows", []):
            obs_id, band, url = row.get("obs_id"), row.get("energy_bandpassname"), row.get("access_url")
            if not obs_id or not band or not url or not url.startswith("https://irsa.ipac.caltech.edu/ibe/data/spherex/"):
                continue
            if detector and detector.upper() != "ALL" and detector.lower() not in band.lower():
                continue
            try:
                mjd = float(row["t_min"])
                if not math.isfinite(mjd):
                    continue
            except (KeyError, TypeError, ValueError):
                continue
            record_id = f"saved_{collection}_{obs_id}_{band.replace('-', '_').replace(' ', '_')}__at_{ra:.6f}_{dec:.6f}".replace('/', '_')
            rows[record_id] = (record_id, obs_id, band, url, mjd, search_saved)
    selected = sorted(rows.values(), key=lambda row: row[4])
    if len(selected) > limit:
        selected = [selected[round(i * (len(selected) - 1) / (limit - 1))] for i in range(limit)] if limit > 1 else selected[:1]
    ordered = []
    for record_id, obs_id, band, url, mjd, saved_date in selected:
        record = ObservationRecord(id=record_id, obs_id=obs_id, collection=collection, detector=band,
                                   mjd=mjd, utc_date=Time(mjd, format="mjd").utc.isot,
                                   access_url=url, ra=ra, dec=dec, search_provenance="saved_irsa_search",
                                   search_snapshot_saved=saved_date)
        OBSERVATION_REGISTRY[record.id] = record.model_dump()
        ordered.append(record)
    return ordered
