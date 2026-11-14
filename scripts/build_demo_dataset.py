#!/usr/bin/env python3
"""
scripts/build_demo_dataset.py
Reads data/manifests/probe_results.json and downloads verified FITS cutouts
for the official targets, handling retries and saving them to data/cache and data/manifests/demo_dataset.json.
"""
import os
import sys
import json
import ssl
import time
import certifi
import urllib.request
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.science.fits_processing import load_fits_cutout, extract_primary_image, calculate_pixel_stats
from app.services.cache_service import cache_service

def download_with_retry(url: str, max_retries: int = 3, delay: float = 2.0):
    ctx = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(url, headers={"User-Agent": "SPHEREx-Discovery-Builder/1.0"})
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                if resp.status == 200:
                    return resp.read()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay * (2 ** attempt))
            else:
                print(f"    Failed after {max_retries} attempts: {e}")
    return None

def build_demo_dataset():
    print("=" * 70)
    print("BUILDING VERIFIED DEMONSTRATION DATASET FROM REAL SPHEREx CUTOUTS")
    print("=" * 70)

    probe_path = Path(__file__).resolve().parent.parent / "data" / "manifests" / "probe_results.json"
    if not probe_path.exists():
        print("[ERROR] probe_results.json not found. Run scripts/probe_irsa.py first.")
        return

    with open(probe_path) as f:
        probe_data = json.load(f)

    manifest = []
    
    # Process targets
    for target_name, tinfo in probe_data.items():
        ra = tinfo["ra"]
        dec = tinfo["dec"]
        print(f"\nProcessing Target: {target_name} ({ra:.4f}, {dec:.4f})")
        
        for coll_name, cinfo in tinfo["collections"].items():
            samples = cinfo.get("sample_observations", [])
            # Try up to 2 successful cutouts per collection
            successes = 0
            for obs in samples[:4]:
                if successes >= 2:
                    break
                access_url = obs.get("access_url")
                if not access_url:
                    continue
                
                cutout_url = f"{access_url}?center={ra:.6f},{dec:.6f}&size=0.0350"
                obs_id = obs.get("obs_id")
                detector = obs.get("detector")
                utc_date = obs.get("utc_date")
                
                # Check cache
                cached_data = cache_service.get(cutout_url)
                if not cached_data:
                    print(f"  Fetching: {coll_name} | {obs_id} | {detector}...")
                    cached_data = download_with_retry(cutout_url)
                    if cached_data:
                        cache_service.set(cutout_url, cached_data)
                        print(f"    [OK] Cached {len(cached_data)} bytes")
                    else:
                        continue
                else:
                    print(f"  [OK] Cache hit for {coll_name} | {obs_id} | {detector}")

                try:
                    hdul = load_fits_cutout(cached_data)
                    data, header = extract_primary_image(hdul)
                    stats = calculate_pixel_stats(data)
                    
                    manifest.append({
                        "target_name": target_name,
                        "ra": ra,
                        "dec": dec,
                        "collection": coll_name,
                        "obs_id": obs_id,
                        "detector": detector,
                        "utc_date": utc_date,
                        "cutout_url": cutout_url,
                        "dimensions": list(data.shape),
                        "pixel_stats": stats,
                    })
                    successes += 1
                except Exception as e:
                    print(f"    [ERROR] Parsing failed: {e}")

    out_file = Path(__file__).resolve().parent.parent / "data" / "manifests" / "demo_dataset.json"
    with open(out_file, "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 70)
    print(f"[SUCCESS] Demonstration manifest written: {out_file}")
    print(f"Total verified real FITS frames in demo dataset: {len(manifest)}")
    print("=" * 70)

if __name__ == "__main__":
    build_demo_dataset()
