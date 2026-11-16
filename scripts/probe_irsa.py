#!/usr/bin/env python3
"""
scripts/probe_irsa.py
Probes NASA IRSA SIA2 service for SPHEREx DR1 and QR3 observations.
Queries documented test positions and the 5 official competition targets.
Saves parsed metadata to data/manifests/probe_results.json.
"""
import ssl
import certifi
import urllib.request
import urllib.parse
import csv
import io
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from astropy.time import Time
from astropy.coordinates import SkyCoord
import astropy.units as u

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import IRSA_SIA_BASE_URL, SEARCH_COLLECTIONS

TEST_TARGETS = [
    {
        "name": "Documentation Example",
        "ra_deg": 127.69444,
        "dec_deg": -39.17760,
        "notes": "Verified API coordinate from IPAC documentation"
    },
    {
        "name": "WISE 0855",
        "ra_deg": 133.795129,
        "dec_deg": -7.245147,
        "notes": "Official target: RA 08h55m10.831s Dec -07d14m42.53s, coldest known brown dwarf"
    },
    {
        "name": "Barnard's Star",
        "ra_deg": 269.45208,
        "dec_deg": 4.69339,
        "notes": "Official target: Highest proper motion star (10.3 arcsec/yr)"
    },
    {
        "name": "Epsilon Indi B",
        "ra_deg": 330.840,
        "dec_deg": -56.786,
        "notes": "Official target: Nearby binary brown dwarf / exoplanet system"
    },
    {
        "name": "RW Aurigae",
        "ra_deg": 76.9542,
        "dec_deg": 30.4014,
        "notes": "Official target: Classical T Tauri variable star system"
    },
    {
        "name": "R Draconis",
        "ra_deg": 248.3375,
        "dec_deg": 66.7042,
        "notes": "Official target: Mira-type pulsating variable star"
    }
]

def query_sia(collection: str, ra: float, dec: float, radius_deg: float = 0.05, max_retries: int = 3):
    params = {
        "COLLECTION": collection,
        "POS": f"circle {ra:.6f} {dec:.6f} {radius_deg:.4f}",
        "RESPONSEFORMAT": "CSV"
    }
    url = f"{IRSA_SIA_BASE_URL}?{urllib.parse.urlencode(params)}"
    ctx = ssl.create_default_context(cafile=certifi.where())
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SPHEREx-Discovery/1.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                if resp.status == 200:
                    data = resp.read().decode("utf-8", errors="ignore")
                    reader = csv.DictReader(io.StringIO(data))
                    rows = list(reader)
                    return rows, url
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  [ERROR] Query failed for {collection} at ({ra}, {dec}): {e}")
                return [], url

def mjd_to_utc_iso(mjd_val):
    try:
        val = float(mjd_val)
        t = Time(val, format="mjd")
        return t.utc.isot
    except Exception:
        return None

def probe_all():
    results = {}
    print("=" * 70)
    print("PROBING NASA IRSA SIA2 FOR SPHEREx OBSERVATIONS")
    print("=" * 70)
    
    for target in TEST_TARGETS:
        name = target["name"]
        ra = target["ra_deg"]
        dec = target["dec_deg"]
        print(f"\nTarget: {name} (RA: {ra:.5f}, Dec: {dec:.5f})")
        print(f"Notes: {target['notes']}")
        
        target_results = {"ra": ra, "dec": dec, "collections": {}}
        
        for coll in SEARCH_COLLECTIONS:
            rows, query_url = query_sia(coll, ra, dec, radius_deg=0.05)
            print(f"  -> Collection '{coll}': {len(rows)} observations found")
            
            parsed_obs = []
            for r in rows[:10]: # Store top 10 for inspect
                mjd_start = r.get("t_min")
                utc_date = mjd_to_utc_iso(mjd_start) if mjd_start else None
                obs_id = r.get("obs_id")
                band = r.get("energy_bandpassname")
                access_url = r.get("access_url")
                
                parsed_obs.append({
                    "obs_id": obs_id,
                    "band": band,
                    "mjd_start": mjd_start,
                    "utc_date": utc_date,
                    "access_url": access_url,
                    "detector": band,
                    "em_min": r.get("em_min"),
                    "em_max": r.get("em_max")
                })
            
            target_results["collections"][coll] = {
                "count": len(rows),
                "query_url": query_url,
                "sample_observations": parsed_obs
            }
            
            if parsed_obs:
                dates = [o["utc_date"] for o in parsed_obs if o["utc_date"]]
                if dates:
                    print(f"     Date range sample: {min(dates)} to {max(dates)}")
        
        results[name] = target_results
        
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "manifests")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "probe_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Probe results saved to {out_path}")
    print("=" * 70)

if __name__ == "__main__":
    probe_all()
