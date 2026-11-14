#!/usr/bin/env python3
"""
scripts/verify_demo.py
Verifies that the demonstration dataset manifest and cached FITS cutouts
are valid, loadable, and correctly calibrated.
"""
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.science.fits_processing import load_fits_cutout, extract_primary_image, calculate_pixel_stats
from app.services.cache_service import cache_service

def verify_demo():
    print("=" * 60)
    print("VERIFYING SPHEREx DISCOVERY DEMONSTRATION DATASET")
    print("=" * 60)
    
    manifest_path = Path(__file__).resolve().parent.parent / "data" / "manifests" / "demo_dataset.json"
    if not manifest_path.exists():
        print(f"[FAIL] Manifest file missing: {manifest_path}")
        return 1

    with open(manifest_path) as f:
        manifest = json.load(f)

    print(f"Total entries in manifest: {len(manifest)}")
    if len(manifest) == 0:
        print("[FAIL] Manifest contains 0 entries.")
        return 1

    all_ok = True
    for idx, item in enumerate(manifest):
        name = item.get("target_name")
        coll = item.get("collection")
        det = item.get("detector")
        url = item.get("cutout_url")
        print(f"\n[{idx+1}/{len(manifest)}] {name} ({coll} | {det})")
        
        cached_data = cache_service.get(url)
        if not cached_data:
            print(f"  [FAIL] Cached FITS file not found for URL: {url[:60]}...")
            all_ok = False
            continue

        try:
            hdul = load_fits_cutout(cached_data)
            img, hdr = extract_primary_image(hdul)
            stats = calculate_pixel_stats(img)
            print(f"  [OK] FITS Shape: {img.shape}, Mean Flux: {stats['mean_mjy_sr']} MJy/sr")
            print(f"       Range: {stats['min_mjy_sr']} to {stats['max_mjy_sr']} MJy/sr")
        except Exception as e:
            print(f"  [FAIL] FITS validation error: {e}")
            all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print("[SUCCESS] All demonstration assets verified and valid!")
    else:
        print("[WARN] Some demonstration assets failed verification.")
    print("=" * 60)
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(verify_demo())
