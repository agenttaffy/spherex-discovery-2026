"""Query an attributed, real Gaia DR3 catalog rather than invented demo rows."""
import csv
import io
import math
from typing import Any

import httpx

VIZIER_URL = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv"


class CatalogUnavailable(RuntimeError):
    """The catalog could not be queried or its response could not be verified."""


class CatalogService:
    async def query_catalog(self, ra: float, dec: float, radius_deg: float = 0.08,
                            catalog_name: str = "gaia_dr3") -> list[dict[str, Any]]:
        if catalog_name.lower() != "gaia_dr3":
            raise ValueError("Only Gaia DR3 is currently supported by the catalog overlay.")
        if not all(math.isfinite(x) for x in (ra, dec, radius_deg)) or not (0 <= ra < 360 and -90 <= dec <= 90 and 0 < radius_deg <= 1):
            raise ValueError("Invalid catalog search coordinates or radius.")
        params = {
            "-source": "I/355/gaiadr3", "-c": f"{ra:.8f} {dec:+.8f}",
            "-c.rs": f"{radius_deg * 3600:.3f}",
            "-out": "Source,RA_ICRS,DE_ICRS,pmRA,pmDE,Plx,Gmag",
            "-sort": "Gmag", "-out.max": "200",
        }
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.get(VIZIER_URL, params=params)
                response.raise_for_status()
            text = response.text
            if "#RESOURCE=yCat_1355" not in text or "#ERROR" in text:
                raise ValueError("Unexpected Gaia DR3 catalog response")
            lines = [line for line in text.splitlines() if line and not line.startswith("#")]
            if not lines:
                return []
            header = lines[0].split("\t")
            expected = ["Source", "RA_ICRS", "DE_ICRS", "pmRA", "pmDE", "Plx", "Gmag"]
            if header != expected or len(lines) < 3:
                raise ValueError("Gaia DR3 response columns did not match")
            reader = csv.DictReader(io.StringIO("\n".join([lines[0], *lines[3:]])), delimiter="\t")
            result = []
            for row in reader:
                source_id = row["Source"].strip()
                if not source_id.isdigit():
                    raise ValueError("Invalid Gaia source identifier")
                src_ra, src_dec = float(row["RA_ICRS"]), float(row["DE_ICRS"])
                if not (math.isfinite(src_ra) and math.isfinite(src_dec) and 0 <= src_ra < 360 and -90 <= src_dec <= 90):
                    raise ValueError("Invalid Gaia coordinates")
                def optional_float(key: str) -> float | None:
                    value = row[key].strip()
                    parsed = float(value) if value else None
                    return parsed if parsed is None or math.isfinite(parsed) else None
                dra = math.radians((src_ra - ra + 180) % 360 - 180)
                dec1, dec2 = math.radians(dec), math.radians(src_dec)
                a = math.sin((dec2-dec1)/2)**2 + math.cos(dec1)*math.cos(dec2)*math.sin(dra/2)**2
                separation = math.degrees(2*math.asin(math.sqrt(min(1.0, max(0.0, a))))) * 3600
                result.append({"source_id": f"Gaia DR3 {source_id}", "ra": src_ra, "dec": src_dec,
                    "g_mag": optional_float("Gmag"), "bp_rp": None, "pm_ra": optional_float("pmRA"),
                    "pm_dec": optional_float("pmDE"), "parallax_mas": optional_float("Plx"),
                    "designation": f"Gaia DR3 {source_id}", "catalog": "Gaia DR3", "star_type": "Gaia DR3 source",
                    "separation_arcsec": round(separation, 2), "provenance": "VizieR Gaia DR3 (J2016.0)",
                    "catalog_source": "VizieR Gaia DR3 (J2016.0)"})
            return result
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise CatalogUnavailable("Gaia DR3 is unavailable from the catalog service. Try again later.") from exc


catalog_service = CatalogService()
