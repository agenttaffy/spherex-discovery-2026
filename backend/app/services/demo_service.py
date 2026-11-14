import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from astropy.time import Time
from app.config import MANIFESTS_DIR
from app.models.schemas import ObservationRecord, DemoPreset
from app.services.cache_service import cache_service
from app.services.irsa_client import OBSERVATION_REGISTRY

DEMO_DATASET_FILE = MANIFESTS_DIR / "demo_dataset.json"

OFFICIAL_PRESETS: List[DemoPreset] = [
    DemoPreset(
        id="barnards_star",
        name="Barnard's Star",
        ra=269.45208,
        dec=4.69339,
        description="Highest proper motion star known (10.3 arcsec/yr). Visible 1.6-pixel displacement across 1-year baseline.",
        target_type="High Proper Motion Star",
        default_collection="spherex_dr1",
        notable_feature="Astrometric motion across DR1 (Aug 2025) and QR3 (Aug 2026)",
    ),
    DemoPreset(
        id="wise_0855",
        name="WISE 0855",
        ra=133.79513,
        dec=-7.24515,
        description="Coldest known brown dwarf (~250 K), 7.2 light-years distant. Emits almost purely in mid-infrared wavelengths.",
        target_type="Y-type Sub-stellar Brown Dwarf",
        default_collection="spherex_dr1",
        notable_feature="Strong infrared emission in D4/D5 bands; invisible in optical",
    ),
    DemoPreset(
        id="rw_aurigae",
        name="RW Aurigae",
        ra=76.95420,
        dec=30.40140,
        description="Classical T Tauri binary system with circumstellar disk disruption causing dramatic photometric dimming.",
        target_type="Young Stellar Object / Variable Star",
        default_collection="spherex_dr1",
        notable_feature="Multi-magnitude infrared brightness variations",
    ),
    DemoPreset(
        id="r_draconis",
        name="R Draconis",
        ra=248.33750,
        dec=66.70420,
        description="Mira-type pulsating red giant with a 245-day period and large infrared pulsation amplitude.",
        target_type="Pulsating Asymptotic Giant Branch Star",
        default_collection="spherex_dr1",
        notable_feature="Periodic flux pulsation visible in Level 2 time series",
    ),
    DemoPreset(
        id="epsilon_indi_b",
        name="Epsilon Indi B",
        ra=330.84000,
        dec=-56.78600,
        description="Nearby binary brown dwarf system with prominent orbital and proper motion (4.7 arcsec/yr).",
        target_type="Binary Brown Dwarf System",
        default_collection="spherex_dr1",
        notable_feature="High proper motion and brown dwarf spectral signature",
    ),
]

class DemoService:
    def __init__(self, dataset_path: Path = DEMO_DATASET_FILE):
        self.dataset_path = dataset_path
        self.raw_manifest: List[Dict[str, Any]] = []
        self.demo_records: List[ObservationRecord] = []
        self.base_url_to_cutout: Dict[str, str] = {}
        self.load_manifest()

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
            if collection and rec.collection != collection:
                continue
            if detector and detector != "ALL" and detector.lower() not in rec.detector.lower():
                continue

            delta_ra = (rec.ra - ra + 180.0) % 360.0 - 180.0
            dist_deg = float(np.hypot(delta_ra * np.cos(np.radians(dec)), rec.dec - dec))
            if dist_deg <= radius_deg:
                matches.append(rec)

        matches.sort(key=lambda x: x.mjd or 0.0)
        return matches

    def get_presets(self) -> List[DemoPreset]:
        return OFFICIAL_PRESETS

demo_service = DemoService()
