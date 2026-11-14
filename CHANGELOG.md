# Changelog

All notable changes to the SPHEREx Discovery project will be documented in this file.

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
