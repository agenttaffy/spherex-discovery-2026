# Changelog

All notable changes to the SPHEREx Discovery project will be documented in this file.

## [1.1.0] - 2026-11-14
### Fixed & Hardened
- **Demo Manifest Cache Mapper & Offline Resilience:** Fixed cache miss issue where FOV mismatch (0.0350 vs 0.0400 deg) caused fallback to synthetic star fixtures. Implemented `demo_service.py` to pre-populate `OBSERVATION_REGISTRY` with all 22 verified demonstration entries and provide offline fallback when IRSA SIA is unreachable.
- **Spherical RA 0°/360° Boundary Wrapping:** Fixed `check_comparison_eligibility` rejecting observations across the 0°/360° seam (e.g. 0.01° and 359.99°). Wrapped delta RA to `[-180, +180]`.
- **NaN / Inf Robustness in Differencing Engine:** Fixed `compute_difference_frame` crashing or emitting `nan` stats when processing raw cutouts with non-finite pixels. Added finite pixel masks and mid-gray (128) default for masked data.
- **Space-Separated & Unicode Coordinate Parsing:** Fixed `parse_coordinates` treating space-separated sexagesimal notation (`12 30 00`) as degrees instead of hours. Added support for unicode prime/double-prime characters directly from the NASA Space Apps challenge prompt.
- **Synthetic Fixture Transparency:** Added `is_synthetic` boolean to `FrameResponse` and UI warning badge in `CanvasViewer.tsx` to strictly prevent simulated data from masquerading as real observations.
- **Canvas Rendering Optimization:** Cached decoded `HTMLImageElement` in React state, eliminating async image decoding thrashing on mouse drag and wheel zoom events.
- **Client Frame Caching & Prefetching:** Added in-memory frame cache (`Map<string, FrameResponse>`) and adjacent frame prefetching in `api.ts` and `App.tsx` for zero-latency time-lapse playback.
- **Enhanced Side-by-Side Comparison View:** Updated `ComparisonView.tsx` with 3-panel side-by-side view (Epoch 1, Epoch 2, Difference frame) with time separation baseline $\Delta t$.
- **Automated Test Suite Expansion:** Added `test_demo_resilience.py` and `test_image_registration.py`, expanding test coverage from 23 to 36 passing tests.

## [1.0.0] - 2026-11-14
### Added
- **Repository Setup:** Initialized multi-agent architecture with `AGENTS.md`, `PROJECT_STATE.md`, `TODO.md`, `RESEARCH.md`, `TEST_RESULTS.md`, `DECISIONS.md`, and `HANDOFF.md`.
- **NASA IRSA SIA2 Integration:** Query module in `irsa_client.py` supporting `spherex_dr1` and `spherex_qr3` collections.
- **NASA IRSA IBE Cutout Pipeline:** Sub-array slicing service downloading real Level 2 FITS cutouts on demand.
- **Scientific FITS Processing Engine:** Multi-extension parsing (`IMAGE`, `FLAGS`, `VARIANCE`, `ZODI`, `WCS`), `asinh` and `zscale` display stretching, and PNG rendering in `fits_processing.py`.
- **Differential Image Analysis:** Sub-pixel celestial differencing ($I_2 - I_1$) with RMS difference flux in `comparison.py`.
- **Astronomical Web Frontend:**
  - Responsive dark-sky dashboard built with React 18, TypeScript, Vite, and Tailwind CSS.
  - Interactive HTML5 Canvas viewer with pan, zoom, celestial crosshair, and colormap options (`grayscale`, `inferno`).
  - Multi-epoch chronological timeline player with play/pause, loop, variable FPS, and 2-frame Blink Comparator.
  - Scientific telemetry and provenance panel with direct links to NASA IRSA archive products.
  - Dedicated About & Science documentation page.
- **Demonstration Assets:** Curated 22 verified real FITS cutouts for all 5 official competition targets (Barnard's Star, WISE 0855, RW Aurigae, R Draconis, Epsilon Indi B) cached locally in `data/cache/`.
- **Automated Test Suite:** 23 passing pytest tests covering coordinate validation, FITS parsing, stretch functions, API endpoints, and end-to-end integration flows.
