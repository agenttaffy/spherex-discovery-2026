import csv
import io
import math
import ssl
import time
import asyncio
import certifi
import httpx
from typing import List, Dict, Any, Optional
from astropy.time import Time
from app.config import DEMO_CACHE_ONLY, IRSA_SIA_BASE_URL, SEARCH_COLLECTIONS
from app.models.schemas import ObservationRecord

# In-memory registry of queried observations so /api/frames/{frame_id} can resolve them
OBSERVATION_REGISTRY: Dict[str, Dict[str, Any]] = {}
SIA_REQUIRED_FIELDS = {"obs_id", "energy_bandpassname", "access_url", "t_min"}
# Deliberate opt-in; the default multi-release search remains the wide survey.
DEEP_COLLECTIONS = ("spherex_dr1_deep", "spherex_qr3_deep")


def _finite_number(value: Any) -> Optional[float]:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


class IRSAClient:
    def __init__(self, sia_base_url: str = IRSA_SIA_BASE_URL):
        self.sia_base_url = sia_base_url
        self._offline_until = 0.0
        self._offline_by_collection: Dict[str, float] = {}

    def _mjd_to_utc(self, mjd_str: Optional[str]) -> Optional[str]:
        if not mjd_str:
            return None
        try:
            val = float(mjd_str)
            t = Time(val, format="mjd")
            return t.utc.isot
        except Exception:
            return None

    def _offline_observations(self, ra: float, dec: float, radius_deg: float,
                              collection: str, detector: Optional[str], limit: int) -> List[ObservationRecord]:
        """Use attributed historical metadata; merge demo frames with cloud survey only."""
        from app.services.demo_service import demo_service
        from app.services.saved_observation_search import saved_observations, cloud_header_observations
        demo = demo_service.find_matching_observations(ra=ra, dec=dec, radius_deg=radius_deg,
                                                       collection=collection, detector=detector)
        demo = [record for record in demo if record.collection == collection]
        if DEMO_CACHE_ONLY:
            return demo[:limit]
        saved = saved_observations(ra, dec, radius_deg, collection, detector, limit)
        cloud = cloud_header_observations(ra, dec, collection, detector, limit)
        saved = [record for record in saved if record.collection == collection]
        cloud = [record for record in cloud if record.collection == collection]
        if not cloud:
            return saved or demo[:limit]
        # Preserve cached demo records when available: they carry verified file
        # identity and fixed-cutout provenance. Deduplicate detector exposures.
        merged = {}
        for record in [*cloud, *saved, *demo]:
            merged[(record.collection, record.obs_id, record.detector)] = record
        ordered = sorted(merged.values(), key=lambda row: (row.mjd is None, row.mjd or 0.0))
        if len(ordered) > limit:
            verified_demo = [row for row in ordered if row.search_provenance == "cached_demo"]
            other = [row for row in ordered if row.search_provenance != "cached_demo"]
            # Keep cached demonstrations readily playable when the archive is
            # unreliable, then sample the remaining metadata across time.
            kept_demo = verified_demo[:limit]
            available = limit - len(kept_demo)
            if available >= len(other):
                sampled = other
            elif available > 1:
                sampled = [other[round(i * (len(other) - 1) / (available - 1))] for i in range(available)]
            elif available == 1:
                sampled = other[:1]
            else:
                sampled = []
            ordered = sorted([*kept_demo, *sampled], key=lambda row: (row.mjd is None, row.mjd or 0.0))
        return ordered

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
        if collection is None or collection.upper() in {"ALL", "DEEP"}:
            # SIA without COLLECTION is not a SPHEREx-only search. Query each
            # selected collection explicitly so release provenance is retained.
            selected_collections = (DEEP_COLLECTIONS if collection and collection.upper() == "DEEP"
                                    else SEARCH_COLLECTIONS)
            groups = await asyncio.gather(*(
                self.query_observations(ra, dec, radius_deg, name, detector, limit)
                for name in selected_collections
            ))
            # Share the result limit between collections before sorting by time;
            # otherwise older rows can hide later releases.
            merged = []
            for index in range(max((len(group) for group in groups), default=0)):
                for group in groups:
                    if index < len(group) and len(merged) < limit:
                        merged.append(group[index])
                if len(merged) >= limit:
                    break
            merged.sort(key=lambda record: (record.mjd is None, record.mjd or 0.0))
            return merged

        now = time.time()
        if DEMO_CACHE_ONLY or now < self._offline_until or now < self._offline_by_collection.get(collection, 0.0):
            # During the cooldown, don't keep retrying a failing archive just
            # because this particular sky position has no saved results.
            return self._offline_observations(ra, dec, radius_deg, collection, detector, limit)

        params = {
            "POS": f"circle {ra:.6f} {dec:.6f} {radius_deg:.4f}",
            "RESPONSEFORMAT": "CSV",
        }
        if collection and collection != "ALL":
            params["COLLECTION"] = collection

        records: List[ObservationRecord] = []
        candidate_metadata: Dict[str, Dict[str, Any]] = {}
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())

        search_failed = False
        try:
            # Bound each of the two search attempts so an outage does not leave
            # the interactive viewer waiting for a minute before fallback.
            async with httpx.AsyncClient(verify=ssl_ctx, timeout=8.0) as client:
                for attempt in range(2):
                    try:
                        resp = await client.get(self.sia_base_url, params=params)
                        if resp.status_code not in (429, 502, 503, 504) or attempt == 1:
                            break
                    except (httpx.TimeoutException, httpx.NetworkError):
                        if attempt == 1:
                            raise
                    await asyncio.sleep(0.5)
                if resp.status_code == 200:
                    reader = csv.DictReader(io.StringIO(resp.text))
                    if not reader.fieldnames or not SIA_REQUIRED_FIELDS.issubset(reader.fieldnames):
                        raise ValueError("IRSA search returned an unexpected response instead of an observation table")
                    for row in reader:
                        obs_id = (row.get("obs_id") or "").strip()
                        band = (row.get("energy_bandpassname") or "").strip()
                        access_url = (row.get("access_url") or "").strip()
                        if not obs_id or not band or not access_url:
                            continue
                        mjd_raw = row.get("t_min")
                        mjd_float = _finite_number(mjd_raw)
                        utc_date = self._mjd_to_utc(str(mjd_float)) if mjd_float is not None else None

                        # Optional detector filtering
                        if detector and detector.upper() != "ALL" and detector.lower() not in band.lower():
                            continue

                        # Generate stable unique ID
                        coll_name = collection or row.get("obs_collection") or row.get("collection") or "spherex_dr1"
                        clean_band = band.replace("-", "_").replace(" ", "_")
                        # A single exposure can be searched at many sky positions.
                        # Include the cutout center to avoid one user's query
                        # overwriting another user's coordinates in the registry.
                        record_id = f"{coll_name}_{obs_id}_{clean_band}__at_{ra:.6f}_{dec:.6f}".replace("/", "_")
                        pointing_ra = _finite_number(row.get("s_ra"))
                        pointing_dec = _finite_number(row.get("s_dec"))

                        record_dict = {
                            "id": record_id,
                            "obs_id": obs_id,
                            "collection": coll_name,
                            "detector": band,
                            "mjd": mjd_float,
                            "utc_date": utc_date,
                            "em_min": _finite_number(row.get("em_min")),
                            "em_max": _finite_number(row.get("em_max")),
                            "access_url": access_url,
                            "ra": ra,
                            "dec": dec,
                            "pointing_ra": pointing_ra if pointing_ra is not None else ra,
                            "pointing_dec": pointing_dec if pointing_dec is not None else dec,
                            "search_provenance": "irsa_query",
                        }

                        if record_id not in candidate_metadata:
                            candidate_metadata[record_id] = record_dict
                            records.append(ObservationRecord(**record_dict))

                else:
                    search_failed = True
                    self._offline_by_collection[collection] = time.time() + 30.0
                    print(f"[IRSAClient] IRSA SIA returned status {resp.status_code}")
        except Exception as e:
            search_failed = True
            self._offline_by_collection[collection] = time.time() + 30.0
            print(f"[IRSAClient] Error querying IRSA SIA: {e}")

        if search_failed:
            fallback = self._offline_observations(ra, dec, radius_deg, collection, detector, limit)
            if fallback:
                print(f"[IRSAClient] Using {len(fallback)} attributed offline observations for ({ra:.4f}, {dec:.4f})")
                return fallback
        # If archive is offline or query returned no records, check verified demonstration dataset
        if not records:
            from app.services.demo_service import demo_service
            fallback = demo_service.find_matching_observations(
                ra=ra,
                dec=dec,
                radius_deg=radius_deg,
                collection=collection,
                detector=detector,
            )
            fallback = [record for record in fallback if record.collection == collection]
            if fallback:
                print(f"[IRSAClient] Using {len(fallback)} verified demonstration observations for ({ra:.4f}, {dec:.4f})")
                return fallback[:limit]

        # Sort chronologically by UTC / MJD
        records.sort(key=lambda x: (x.mjd is None, x.mjd or 0.0))
        if len(records) > limit:
            # Preserve the time span rather than taking an arbitrary prefix of
            # the archive's response, which can hide later observations.
            if limit == 1:
                records = records[:1]
            else:
                records = [records[round(i * (len(records) - 1) / (limit - 1))] for i in range(limit)]
        OBSERVATION_REGISTRY.update({record.id: candidate_metadata[record.id] for record in records})
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
                if resp.status_code != 200:
                    return False
                fields = csv.DictReader(io.StringIO(resp.text)).fieldnames
                return bool(fields and SIA_REQUIRED_FIELDS.issubset(fields))
        except Exception:
            return False

irsa_client = IRSAClient()
