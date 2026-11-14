import csv
import io
import ssl
import time
import certifi
import httpx
from typing import List, Dict, Any, Optional
from astropy.time import Time
from app.config import IRSA_SIA_BASE_URL
from app.models.schemas import ObservationRecord

# In-memory registry of queried observations so /api/frames/{frame_id} can resolve them
OBSERVATION_REGISTRY: Dict[str, Dict[str, Any]] = {}

class IRSAClient:
    def __init__(self, sia_base_url: str = IRSA_SIA_BASE_URL):
        self.sia_base_url = sia_base_url
        self._offline_until = 0.0

    def _mjd_to_utc(self, mjd_str: Optional[str]) -> Optional[str]:
        if not mjd_str:
            return None
        try:
            val = float(mjd_str)
            t = Time(val, format="mjd")
            return t.utc.isot
        except Exception:
            return None

    async def query_observations(
        self,
        ra: float,
        dec: float,
        radius_deg: float = 0.05,
        collection: Optional[str] = "spherex_dr1",
        detector: Optional[str] = None,
        limit: int = 50,
    ) -> List[ObservationRecord]:
        """
        Queries NASA IRSA SIA2 service for SPHEREx observations.
        Includes circuit breaker for remote outages and instant offline demo fallback.
        """
        now = time.time()
        if now < self._offline_until:
            from app.services.demo_service import demo_service
            fallback = demo_service.find_matching_observations(
                ra=ra,
                dec=dec,
                radius_deg=max(radius_deg, 0.15),
                collection=collection,
                detector=detector,
            )
            if fallback:
                return fallback[:limit]

        params = {
            "POS": f"circle {ra:.6f} {dec:.6f} {radius_deg:.4f}",
            "RESPONSEFORMAT": "CSV",
        }
        if collection and collection != "ALL":
            params["COLLECTION"] = collection

        records: List[ObservationRecord] = []
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())

        try:
            async with httpx.AsyncClient(verify=ssl_ctx, timeout=3.5) as client:
                resp = await client.get(self.sia_base_url, params=params)
                if resp.status_code == 200:
                    reader = csv.DictReader(io.StringIO(resp.text))
                    for row in reader:
                        obs_id = row.get("obs_id", "unknown")
                        band = row.get("energy_bandpassname", "SPHEREx")
                        access_url = row.get("access_url", "")
                        mjd_raw = row.get("t_min")
                        mjd_float = float(mjd_raw) if mjd_raw else None
                        utc_date = self._mjd_to_utc(mjd_raw)

                        # Optional detector filtering
                        if detector and detector.lower() not in band.lower():
                            continue

                        # Generate stable unique ID
                        coll_name = collection or row.get("obs_collection") or row.get("collection") or "spherex_dr1"
                        clean_band = band.replace("-", "_").replace(" ", "_")
                        record_id = f"{coll_name}_{obs_id}_{clean_band}".replace("/", "_")

                        record_dict = {
                            "id": record_id,
                            "obs_id": obs_id,
                            "collection": coll_name,
                            "detector": band,
                            "mjd": mjd_float,
                            "utc_date": utc_date,
                            "em_min": float(row["em_min"]) if row.get("em_min") else None,
                            "em_max": float(row["em_max"]) if row.get("em_max") else None,
                            "access_url": access_url,
                            "ra": ra,
                            "dec": dec,
                            "pointing_ra": float(row["s_ra"]) if row.get("s_ra") else ra,
                            "pointing_dec": float(row["s_dec"]) if row.get("s_dec") else dec,
                        }

                        # Store in registry for frame fetching
                        OBSERVATION_REGISTRY[record_id] = record_dict

                        records.append(ObservationRecord(**record_dict))

                        if len(records) >= limit:
                            break
                else:
                    self._offline_until = time.time() + 30.0
                    print(f"[IRSAClient] IRSA SIA returned status {resp.status_code}")
        except Exception as e:
            self._offline_until = time.time() + 30.0
            print(f"[IRSAClient] Error querying IRSA SIA: {e}")

        # If archive is offline or query returned no records, check verified demonstration dataset
        if not records:
            from app.services.demo_service import demo_service
            fallback = demo_service.find_matching_observations(
                ra=ra,
                dec=dec,
                radius_deg=max(radius_deg, 0.15),
                collection=collection,
                detector=detector,
            )
            if fallback:
                print(f"[IRSAClient] Using {len(fallback)} verified demonstration observations for ({ra:.4f}, {dec:.4f})")
                return fallback[:limit]

        # Sort chronologically by UTC / MJD
        records.sort(key=lambda x: x.mjd or 0.0)
        return records

    async def check_connectivity(self) -> bool:
        """
        Quick probe to check if IRSA SIA is responding.
        """
        try:
            params = {
                "COLLECTION": "spherex_dr1",
                "POS": "circle 127.69444 -39.17760 0.01",
                "RESPONSEFORMAT": "CSV",
            }
            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
            async with httpx.AsyncClient(verify=ssl_ctx, timeout=3.0) as client:
                resp = await client.get(self.sia_base_url, params=params)
                return resp.status_code == 200
        except Exception:
            return False

irsa_client = IRSAClient()
