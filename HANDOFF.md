# Agent Handoff Document

## 1. Last Completed Work
- Verified live NASA/IPAC IRSA SIA2 queries across DR1 and QR3 for all 5 official competition targets.
- Downloaded, parsed, and verified 22 real multi-extension FITS cutouts (40.4 MB) cached in `data/cache/`.
- Implemented complete FastAPI backend (`backend/app/`) with endpoints for health, observations, cutouts, differencing, and demo presets.
- Implemented complete React 18 / TypeScript frontend (`frontend/src/`) featuring:
  - Interactive HTML5 Canvas viewer with pan, zoom, crosshair, and contrast stretch engines (`asinh`, `zscale`, `linear`, `inferno`).
  - Multi-epoch chronological timeline player with play/pause, variable FPS, and 2-frame Blink Comparator mode.
  - Scientific metadata and quality bitmask telemetry dock with direct NASA IRSA provenance links.
  - Differential image engine ($I_2 - I_1$) with RMS difference flux metrics.
  - About & Science page explaining the SPHEREx mission and LVF detector design.
- Implemented 23 pytest tests across unit, science, and end-to-end integration flows (100% passing).
- Verified production build (`npm run build`) with zero TypeScript errors.

## 2. Current Working State
- **Backend:** Starts cleanly with `python -m uvicorn app.main:app --port 8000`. All 23 tests pass in 9.3s.
- **Frontend:** Builds cleanly with `npm run build`. Dev server runs with `npm run dev`.
- **Demo Mode:** Instantaneous local caching of 22 real FITS cutouts enables immediate offline presentation.

## 3. Current Blocker
- None. The system is functional end-to-end.

## 4. Next Three Tasks
1. **P2-001: Gaia DR3 Star Catalog Overlay:** Add a button to query nearby Gaia DR3 stars and render vector markers with proper-motion vectors directly on the canvas.
2. **P2-002: Photometric Light Curve Chart:** Add a simple SVG or Canvas flux-over-time plot for variable star observations (such as RW Aurigae and R Draconis).
3. **P2-003: Shareable URL State:** Sync active target preset, coordinates, FOV, and stretch mode to URL search params for seamless sharing.

## 5. Files to Inspect
- `backend/app/science/fits_processing.py`: Scientific FITS extraction and asinh contrast algorithms.
- `backend/app/services/cutout_service.py`: On-demand IBE cutout fetching and local caching.
- `backend/app/science/comparison.py`: Frame comparison eligibility and difference image generation.
- `frontend/src/App.tsx`: Central frontend application orchestration.
- `frontend/src/components/viewer/CanvasViewer.tsx`: Canvas rendering, crosshair, and pan/zoom handlers.
- `frontend/src/components/timeline/TimelinePlayer.tsx`: Playback loop, FPS control, and blink toggle.

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

# 3. Backend Test Suite
cd backend
python -m pytest -v

# 4. Frontend Typecheck & Production Build
cd frontend
npm run build
```

## 8. Latest Git Commit & Uncommitted Work
- Commit: `c6298af11b41193030c2fc0fd236414c01c164ef`
- Clean working directory, 0 uncommitted changes.
