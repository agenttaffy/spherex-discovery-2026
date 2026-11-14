# SPHEREx Discovery — Project State

**Last Updated:** 2026-11-14T14:30:00Z  
**Current Implementation Stage:** Phase 1 Complete (Foundational Architecture, Live NASA IRSA Integration, Scientific FITS Pipeline, Interactive Web Explorer & Blink Timeline).

---

## 1. Verified Working Features
- **NASA/IPAC IRSA SIA2 Client:** Live programmatic queries against `spherex_dr1` and `spherex_qr3` collections.
- **NASA/IPAC IRSA IBE Cutout Pipeline:** Live sub-array slicing using `?center=<ra>,<dec>&size=<deg>`, downloading ~4 MB FITS cutouts instead of 70 MB full frames.
- **Multi-Extension FITS Parser:** Astropy-based extraction of `IMAGE` (MJy/sr), `FLAGS` (int32 bitmask), `VARIANCE`, `ZODI`, and celestial `WCS`.
- **Display-Only Contrast Scaling:** `asinh` (arcsinh), `zscale`, and `linear` stretching engines with grayscale and `inferno` colormap generation.
- **Differential Image Engine:** Sub-pixel celestial differencing ($I_2 - I_1$) with RMS difference flux and positive/negative residual diagnostics.
- **Interactive Astronomical Web Explorer:**
  - Celestial coordinates input supporting decimal degrees (`269.45208, 4.69339`) and sexagesimal string formats (`08h55m10.831s, -07d14m42.53s`).
  - Interactive HTML5 Canvas viewer with panning, zooming, and celestial crosshair.
  - Multi-epoch chronological timeline player with play/pause, loop, variable speed (1x, 2x, 4x), and rapid 2-frame Blink Comparator.
  - Telemetry and data provenance panel with direct link to NASA IRSA FITS products.
- **22 Verified Demonstration Cutouts:** Cached locally in `data/cache` covering all 5 official competition targets across DR1 and QR3.
- **Comprehensive Test Suite:** 23 passing pytest tests covering unit, science, and end-to-end integration flows.

## 2. Partially Working Features
- **External Catalog Overlays:** Gaia DR3 and WISE cross-matching hooks prepared in architecture, not yet rendered as interactive vector overlays on the canvas.

## 3. Broken Features
- None detected.

## 4. Architecture Summary
- **Backend:** FastAPI (Python 3.11) with endpoints `/api/health`, `/api/observations`, `/api/frames/{id}`, `/api/frames/diff`, and `/api/demo`.
- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS + HTML5 Canvas.
- **Data:** Direct NASA IRSA SIA2/IBE protocols with disk-backed cache in `data/cache/`.

## 5. Most Important Files
- `backend/app/services/irsa_client.py`: NASA IRSA SIA2 observation discovery.
- `backend/app/services/cutout_service.py`: On-demand IBE FITS cutout retrieval & caching.
- `backend/app/science/fits_processing.py`: Calibrated multi-extension parsing & asinh rendering.
- `backend/app/science/comparison.py`: Frame eligibility & differential analysis ($I_2 - I_1$).
- `frontend/src/App.tsx`: Main React application & state orchestration.
- `frontend/src/components/viewer/CanvasViewer.tsx`: High-performance astronomical canvas.
- `frontend/src/components/timeline/TimelinePlayer.tsx`: Time-lapse playback & blink comparator.

## 6. Verified Live API Connections
- `https://irsa.ipac.caltech.edu/SIA`: Status 200 OK (verified across all 5 official targets).
- `https://irsa.ipac.caltech.edu/ibe/data/spherex/...`: Status 200 OK (verified with 22 downloaded cutouts).

## 7. Dataset Availability
- 22 real FITS cutouts (40.4 MB) cached in `data/cache/` for offline/low-latency judging.
- Target manifest verified at `data/manifests/demo_dataset.json`.

## 8. Latest Build & Test Status
- **Backend pytest:** 23 passed in 9.31s (0 warnings, 0 failures).
- **Frontend build:** `npm run build` succeeded (1,492 modules transformed, zero type errors).

## 9. Next Recommended Action
- Implement interactive Gaia DR3 star catalog overlay toggle on the canvas viewer.
- Add client-side photometric light curve chart for variable stars (e.g. RW Aurigae, R Draconis).
