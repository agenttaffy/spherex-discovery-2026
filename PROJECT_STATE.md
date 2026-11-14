# SPHEREx Discovery — Project State

**Last Updated:** 2026-11-14T15:00:00Z  
**Current Implementation Stage:** Phase 2 Complete (Hardened Scientific Differencing, Demo Dataset Offline Resilience, Zero-Latency Canvas/Timeline Caching, Multi-Epoch Comparison).

---

## 1. Verified Working Features
- **NASA/IPAC IRSA SIA2 Client:** Live programmatic queries against `spherex_dr1` and `spherex_qr3` collections.
- **Offline / Low-Latency Resilience:** Automatically uses verified demonstration observations from `data/manifests/demo_dataset.json` when IRSA times out or is unreachable, guaranteeing flawless judge demonstrations.
- **NASA/IPAC IRSA IBE Cutout Pipeline:** Live sub-array slicing using `?center=<ra>,<dec>&size=<deg>`, downloading ~4 MB FITS cutouts instead of 70 MB full frames.
- **Demo Manifest Cache Mapper:** Maps base access URLs to cached cutouts regardless of minor FOV differences (0.0350 vs 0.0400 deg), eliminating accidental cache misses.
- **Multi-Extension FITS Parser:** Astropy-based extraction of `IMAGE` (MJy/sr), `FLAGS` (int32 bitmask), `VARIANCE`, `ZODI`, and celestial `WCS`.
- **Display-Only Contrast Scaling:** `asinh` (arcsinh), `zscale`, and `linear` stretching engines with grayscale and `inferno` colormap generation.
- **Differential Image Engine:**
  - Robust against non-finite values (NaN/Inf) with finite stats calculation and mid-gray (128) baseline for missing pixels.
  - Spherical RA boundary wrapping across 0°/360° celestial seam.
  - Duplicate epoch self-comparison detection.
- **Astronomical Image Registration:** Sub-pixel relative translation estimator (`estimate_pixel_shift`) using 2D FFT cross-correlation, verified with dedicated unit tests.
- **Interactive Astronomical Web Explorer:**
  - Celestial coordinates input supporting decimal degrees, sexagesimal HMS/DMS, colon-separated, and space-separated formats, plus unicode challenge prompt coordinates (`08h55m10.831s, -07°14′42.53″`).
  - High-performance HTML5 Canvas viewer with cached image decoding for silky 60 FPS pan and zoom.
  - Multi-epoch chronological timeline player with play/pause, loop, variable speed (1x, 2x, 4x), in-memory frame caching, adjacent frame prefetching, and rapid 2-frame Blink Comparator.
  - Telemetry and data provenance panel with direct link to NASA IRSA FITS products and synthetic fixture transparency warnings (`is_synthetic`).
  - Side-by-side Differential Analysis view showing Epoch 1, Epoch 2, and Difference ($I_2 - I_1$) with time baseline $\Delta t$.
- **22 Verified Demonstration Cutouts:** Cached locally in `data/cache` covering all 5 official competition targets across DR1 and QR3.
- **Comprehensive Test Suite:** 36 passing pytest tests covering unit, science, offline resilience, and end-to-end integration flows.

## 2. Partially Working Features
- **External Catalog Overlays:** Gaia DR3 and WISE cross-matching hooks prepared in architecture, not yet rendered as interactive vector overlays on the canvas.

## 3. Broken Features
- None detected.

## 4. Architecture Summary
- **Backend:** FastAPI (Python 3.11) with endpoints `/api/health`, `/api/observations`, `/api/frames/{id}`, `/api/frames/diff`, `/api/demo`, and `/api/demo/manifest`.
- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS + HTML5 Canvas.
- **Data:** Direct NASA IRSA SIA2/IBE protocols with disk-backed cache in `data/cache/` and manifest in `data/manifests/`.

## 5. Most Important Files
- `backend/app/services/demo_service.py`: Verified demonstration catalog, manifest loader, and cache index.
- `backend/app/services/irsa_client.py`: NASA IRSA SIA2 observation discovery with offline demo fallback.
- `backend/app/services/cutout_service.py`: On-demand IBE FITS cutout retrieval & caching with base URL mapping.
- `backend/app/science/comparison.py`: Frame eligibility with spherical 0/360 RA wrapping & finite difference analysis.
- `backend/app/science/image_registration.py`: 2D FFT sub-pixel shift estimator.
- `frontend/src/components/viewer/ComparisonView.tsx`: 3-card side-by-side Epoch 1 / Epoch 2 / Difference viewer.
- `frontend/src/components/viewer/CanvasViewer.tsx`: High-performance cached image canvas.

## 6. Verified Live API Connections
- `https://irsa.ipac.caltech.edu/SIA`: Status 200 OK (verified across all 5 official targets).
- `https://irsa.ipac.caltech.edu/ibe/data/spherex/...`: Status 200 OK (verified with 22 downloaded cutouts).

## 7. Dataset Availability
- 22 real FITS cutouts (40.4 MB) cached in `data/cache/` for offline/low-latency judging.
- Target manifest verified at `data/manifests/demo_dataset.json`.

## 8. Latest Build & Test Status
- **Backend pytest:** 36 passed in 6.08s (0 warnings, 0 failures).
- **Frontend build:** `npm run build` succeeded (1,492 modules transformed, zero type errors).

## 9. Next Recommended Action
- Implement interactive Gaia DR3 star catalog overlay toggle on the canvas viewer.
- Add client-side photometric light curve chart for variable stars (e.g. RW Aurigae, R Draconis).
