import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from astropy.time import Time
from app.config import DEMO_DATASET_FILE, DEFAULT_COLLECTION, DEMO_CACHE_ONLY, MANIFESTS_DIR
from app.models.schemas import ObservationRecord, DemoPreset
from app.services.cache_service import cache_service
from app.services.irsa_client import OBSERVATION_REGISTRY

# Starting positions are the epoch-dependent predictions in the packaged,
# audited demo-preview manifest. They are search centers, not confirmations
# that the target was detected. Keeping them independent of the local FITS
# cache also makes a fresh checkout use the same vetted sky positions.
OFFICIAL_PRESETS: List[DemoPreset] = [
    DemoPreset(
        id="barnards_star",
        name="Barnard's Star",
        ra=269.4461286205729,
        dec=4.769998359667445,
        description="Nearby star with high catalog proper motion. Check the epoch and footprint before measuring the source.",
        target_type="High Proper Motion Star",
        default_collection=DEFAULT_COLLECTION,
        notable_feature="Epoch-dependent sky position",
    ),
    DemoPreset(
        id="wise_0855",
        name="WISE 0855",
        ra=133.75896227492004,
        dec=-7.242116064321349,
        description="Nearby Y dwarf with high catalog proper motion and very faint optical emission.",
        target_type="Y-type Sub-stellar Brown Dwarf",
        default_collection=DEFAULT_COLLECTION,
        notable_feature="Infrared brown dwarf",
    ),
    DemoPreset(
        id="rw_aurigae",
        name="RW Aurigae",
        ra=76.95658820303035,
        dec=30.401287398865755,
        description="Classical T Tauri binary system with circumstellar disk disruption causing dramatic photometric dimming.",
        target_type="Young Stellar Object / Variable Star",
        default_collection=DEFAULT_COLLECTION,
        notable_feature="Variable young binary with unresolved components in SPHEREx",
    ),
    DemoPreset(
        id="r_draconis",
        name="R Draconis",
        ra=248.16722768733652,
        dec=66.75502445923215,
        description="Mira-type pulsating red giant. SPHEREx variability requires suitable comparable data.",
        target_type="Pulsating Asymptotic Giant Branch Star",
        default_collection=DEFAULT_COLLECTION,
        notable_feature="Pulsating variable",
    ),
    DemoPreset(
        id="epsilon_indi_b",
        name="Epsilon Indi B",
        ra=331.09813086506205,
        dec=-56.801144263858404,
        description="Nearby binary brown dwarf system with prominent orbital and proper motion (4.7 arcsec/yr).",
        target_type="Binary Brown Dwarf System",
        default_collection=DEFAULT_COLLECTION,
        notable_feature="High proper motion and brown dwarf spectral signature",
    ),
]

class DemoService:
    def __init__(self, dataset_path: Path = DEMO_DATASET_FILE):
        self.dataset_path = dataset_path
        self.raw_manifest: List[Dict[str, Any]] = []
        self.demo_records: List[ObservationRecord] = []
        self.base_url_to_cutout: Dict[str, str] = {}
        self.preview_metadata: List[Dict[str, Any]] = []
        self.load_manifest()
        self.load_packaged_preview_metadata()

    def load_packaged_preview_metadata(self) -> None:
        """Use vetted metadata on a default checkout even before images are cached.

        Explicit custom manifests and offline-only mode retain their existing
        behavior. These entries describe archive images, not cached cutouts.
        """
        if DEMO_CACHE_ONLY or self.dataset_path.resolve() != (MANIFESTS_DIR / "demo_dataset.json").resolve():
            return
        from app.services.cloud_cutout import expected_image_identity
        try:
            raw = (MANIFESTS_DIR / "demo_preview.json").read_bytes()
            sources = json.loads((MANIFESTS_DIR / "demo_preview_assets.json").read_text(encoding="utf-8"))
            if hashlib.sha256(raw).hexdigest() != sources["preview_manifest_sha256"]:
                return
            entries = json.loads(raw)
            if not isinstance(entries, list):
                return
            for entry in entries:
                if entry.get("catalog_coverage") != "inside":
                    continue
                url = entry.get("cutout_url", "").split("?", 1)[0]
                detector = str(entry.get("detector", ""))
                if (not detector.startswith("SPHEREx-D") or
                        expected_image_identity(url) != (entry.get("obs_id"), detector.removeprefix("SPHEREx-D"))):
                    continue
                # Retain only complete coordinate/time records that can be
                # tied to the exact official image URL.
                try:
                    ra, dec = float(entry["ra"]), float(entry["dec"])
                    mjd = float(Time(entry["utc_date"], format="isot").mjd)
                except (KeyError, ValueError, TypeError):
                    continue
                if not np.isfinite([ra, dec, mjd]).all() or not (0 <= ra < 360 and -90 <= dec <= 90):
                    continue
                self.preview_metadata.append(entry)
        except (OSError, ValueError, TypeError, KeyError):
            return

    def load_manifest(self) -> None:
        """
        Loads verified demonstration cutouts and registers them in the global OBSERVATION_REGISTRY.
        """
        if not self.dataset_path.exists():
            return

        try:
            with open(self.dataset_path, "r", encoding="utf-8") as f:
                self.raw_manifest = json.load(f)

            for entry in self.raw_manifest:
                obs_id = entry.get("obs_id", "unknown")
                collection = entry.get("collection", "spherex_dr1")
                detector = entry.get("detector", "SPHEREx")
                cutout_url = entry.get("cutout_url", "")
                base_access_url = cutout_url.split("?")[0] if cutout_url else ""
                utc_date = entry.get("utc_date")
                ra = float(entry.get("ra", 0.0))
                dec = float(entry.get("dec", 0.0))
                coverage = entry.get("catalog_coverage")

                clean_band = detector.replace("-", "_").replace(" ", "_")
                record_id = f"{collection}_{obs_id}_{clean_band}".replace("/", "_")

                mjd_val = None
                if utc_date:
                    try:
                        mjd_val = float(Time(utc_date, format="isot").mjd)
                    except Exception:
                        pass

                record_dict = {
                    "id": record_id,
                    "obs_id": obs_id,
                    "collection": collection,
                    "detector": detector,
                    "mjd": mjd_val,
                    "utc_date": utc_date,
                    "em_min": None,
                    "em_max": None,
                    "access_url": base_access_url,
                    "cached_cutout_url": cutout_url,
                    "ra": ra,
                    "dec": dec,
                }

                # Register in OBSERVATION_REGISTRY
                OBSERVATION_REGISTRY[record_id] = record_dict
                if base_access_url:
                    self.base_url_to_cutout[base_access_url] = cutout_url

                rec = ObservationRecord(
                    id=record_id,
                    obs_id=obs_id,
                    collection=collection,
                    detector=detector,
                    mjd=mjd_val,
                    utc_date=utc_date,
                    em_min=None,
                    em_max=None,
                    access_url=base_access_url,
                    ra=ra,
                    dec=dec,
                    search_provenance="cached_demo",
                    catalog_coverage=coverage if coverage in ("inside", "outside") else None,
                )
                self.demo_records.append(rec)

        except Exception as e:
            print(f"[DemoService] Failed to load demo manifest: {e}")

    def get_cached_cutout_for_url(self, base_access_url: str) -> Optional[bytes]:
        """
        Retrieves verified FITS cutout bytes for a known base access URL.
        """
        cutout_url = self.base_url_to_cutout.get(base_access_url)
        if cutout_url:
            return cache_service.get(cutout_url)
        return None

    def find_matching_observations(
        self,
        ra: float,
        dec: float,
        radius_deg: float = 0.1,
        collection: Optional[str] = None,
        detector: Optional[str] = None,
    ) -> List[ObservationRecord]:
        """
        Finds cached verified demonstration observations within radius of given coordinates.
        """
        matches: List[ObservationRecord] = []
        for rec in self.demo_records:
            if collection and collection != "ALL" and rec.collection != collection:
                continue
            if detector and detector != "ALL" and detector.lower() not in rec.detector.lower():
                continue

            delta_ra = (rec.ra - ra + 180.0) % 360.0 - 180.0
            dist_deg = float(np.hypot(delta_ra * np.cos(np.radians(dec)), rec.dec - dec))
            if dist_deg <= radius_deg:
                matches.append(rec)

        preview_matches: List[ObservationRecord] = []
        for entry in self.preview_metadata:
            entry_collection, band = entry["collection"], entry["detector"]
            if collection and collection != "ALL" and collection != entry_collection:
                continue
            if detector and detector.upper() != "ALL" and detector.lower() != band.lower():
                continue
            delta_ra = (float(entry["ra"]) - ra + 180.0) % 360.0 - 180.0
            if np.hypot(delta_ra * np.cos(np.radians(dec)), float(entry["dec"]) - dec) > radius_deg:
                continue
            obs_id = entry["obs_id"]
            record_id = f"demo_metadata_{entry_collection}_{obs_id}_{band.replace('-', '_')}__at_{ra:.6f}_{dec:.6f}"
            url = entry["cutout_url"].split("?", 1)[0]
            record = ObservationRecord(id=record_id, obs_id=obs_id, collection=entry_collection,
                detector=band, mjd=float(Time(entry["utc_date"], format="isot").mjd),
                utc_date=entry["utc_date"], access_url=url, ra=ra, dec=dec,
                search_provenance="demo_metadata")
            OBSERVATION_REGISTRY[record_id] = record.model_dump()
            preview_matches.append(record)

        if preview_matches:
            # Older default entries explicitly marked outside the target
            # footprint are not useful demonstrations at the vetted position.
            matches = [record for record in matches if record.catalog_coverage != "outside"]
            # The curated version supersedes an older entry for the same image.
            unique = {(record.collection, record.obs_id, record.detector): record for record in matches}
            for record in preview_matches:
                unique[(record.collection, record.obs_id, record.detector)] = record
            matches = list(unique.values())

        matches.sort(key=lambda x: x.mjd or 0.0)
        return matches

    def get_presets(self) -> List[DemoPreset]:
        presets = []
        for preset in OFFICIAL_PRESETS:
            covered = [
                entry for entry in self.raw_manifest
                if entry.get("target_name") == preset.name
                and entry.get("catalog_coverage") == "inside"
                and entry.get("predicted_degrees") is not None
            ]
            if not covered:
                covered = [entry for entry in self.preview_metadata if entry.get("target_name") == preset.name
                           and entry.get("predicted_degrees") is not None]
            if not covered:
                presets.append(preset)
                continue
            latest = max(covered, key=lambda entry: entry["utc_date"])
            collections = {entry["collection"] for entry in covered}
            presets.append(preset.model_copy(update={
                "ra": latest["predicted_degrees"][0], "dec": latest["predicted_degrees"][1],
                "default_collection": latest["collection"] if len(collections) == 1 else "ALL",
            }))
        return presets

demo_service = DemoService()
