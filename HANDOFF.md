# Agent Handoff Document

## 1. Last Completed Work
- Verified live NASA/IPAC IRSA SIA2 queries across DR1 and QR3 for all 5 official competition targets.
- Downloaded, parsed, and verified 22 real multi-extension FITS cutouts (40.4 MB) cached in `data/cache/`.
- Implemented complete FastAPI backend (`backend/app/`) with endpoints for health, observations, cutouts, differencing, demo presets, and full demo manifest.
- Resolved cache miss issue on demo datasets: created `demo_service.py` to map base access URLs to cached cutouts, pre-populate `OBSERVATION_REGISTRY` at startup, and provide seamless offline fallback when IRSA SIA is slow or unreachable.
- Fixed spherical RA 0°/360° boundary wrapping in `check_comparison_eligibility`.
- Hardened `compute_difference_frame` against NaN/Inf values, ensuring valid finite differential telemetry and mid-gray masked pixels.
- Added 2D FFT sub-pixel image registration unit tests (`test_image_registration.py`).
- Added offline resilience unit tests with mock timeout (`test_demo_resilience.py`), expanding test suite to 36 passing tests.
- Enhanced `ComparisonView.tsx` with a 3-card side-by-side view (Epoch 1, Epoch 2, and Difference) including baseline $\Delta t$ in days.
- Optimized canvas rendering in `CanvasViewer.tsx` with cached image decoding for 60 FPS panning/zooming.
- Added in-memory client frame caching and prefetching in `api.ts` and `App.tsx` for zero-latency time-lapse playback.
- Added explicit synthetic fixture transparency (`is_synthetic` flag and UI warning badge).

## 2. Current Working State
- **Backend:** Starts cleanly with `python -m uvicorn app.main:app --port 8000`. All 36 tests pass in 6.08s.
- **Frontend:** Builds cleanly with `npm run build` in 2.13s (0 errors). Dev server runs with `npm run dev`.
- **Demo Mode:** Instantaneous local caching of 22 real FITS cutouts enables immediate offline presentation and judging.

## 3. Current Blocker
- None. The system is functional end-to-end and resilient against network outages.

## 4. Next Three Tasks
1. **P2-001: Gaia DR3 Star Catalog Overlay:** Add a button to query nearby Gaia DR3 stars and render vector markers with proper-motion vectors directly on the canvas.
2. **P2-002: Photometric Light Curve Chart:** Add a simple SVG or Canvas flux-over-time plot for variable star observations (such as RW Aurigae and R Draconis).
3. **P2-003: Shareable URL State:** Sync active target preset, coordinates, FOV, and stretch mode to URL search params for seamless sharing.

## 5. Files to Inspect
- `backend/app/services/demo_service.py`: Verified demonstration catalog, manifest loader, and cache index.
- `backend/app/services/cutout_service.py`: Cutout service with cache resolution and fallback handling.
- `backend/app/science/comparison.py`: Differential engine with 0/360 boundary wrapping & NaN robustness.
- `backend/app/science/image_registration.py`: 2D FFT sub-pixel shift estimator.
- `frontend/src/components/viewer/ComparisonView.tsx`: Side-by-side Epoch 1, Epoch 2, and Difference viewer.
- `frontend/src/components/viewer/CanvasViewer.tsx`: High-performance canvas viewer with cached image decoding.

## 6. Important Scientific Warnings
- **Linear Variable Filters (LVF):** SPHEREx detectors (D1–D6) have spatially varying bandpasses. Never compute pixel differences between images taken with different detectors or misaligned coordinate grids.
- **Display Stretches:** Visual contrast enhancements (asinh / zscale) must strictly remain preview-only; raw pixel measurements in `MJy/sr` must not be overwritten or clipped in telemetry.
- **Planet X Claims:** Never claim a moving object is "Planet X" unless validated against known solar system ephemerides (e.g. JPL Horizons).

## 7. Verification Commands
```bash
# 1. Environment & IRSA Connectivity
python scripts/verify_environment.py

# 2. Demonstration Assets Verification
python scripts/verify_demo.py

# 3. Backend Test Suite (36 tests)
cd backend
python -m pytest -v

# 4. Frontend Typecheck & Production Build
cd frontend
npm run build
```

## 8. Latest Git Commit & Uncommitted Work
- Commit: `69af8ee` ("fix: harden scientific differencing, offline demo resilience, and frontend rendering performance")
- Uncommitted work: None (working tree clean).
