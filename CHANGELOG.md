# Changelog

All notable changes to the SPHEREx Discovery project will be documented in this file.

## [1.2.1] - 2026-11-14
### Fixed & Hardened (Review & Verification Round)
- **Fourier Phase Shift Vector Inversion:** Fixed mathematical sign error in `estimate_pixel_shift` (`f2 * np.conj(f1)` vs `f1 * np.conj(f2)`), aligning 2D cross-correlation displacement with primary centroid tracking. Fixed test fitting in `test_known_shift_recovery`.
- **Astrometric Dipole Overlay Threshold & Sub-Pixel Alignment:** Lowered displacement threshold from `> 0.4` to `>= 0.1` px in `ComparisonView.tsx` so the dipole vector correctly displays on Barnard's Star (0.238 px / 1.48″ shift). Replaced arbitrary `viewBox="-20 -20 40 40"` scaling with true image dimensions and exact sub-pixel centroid coordinates (`centroid_1`, `centroid_2`).
- **Aperture Photometry Centroiding & Spectral Band Segregation:** In `photometry.py`, added auto-detection of source peak centroid to prevent aperture truncation on off-center stars. Updated `build_lightcurve_series` to evaluate variability within consistent detector bands, eliminating false variability classifications on stable stars (e.g. Barnard's Star) caused by spectral energy differences across bands.
- **Circuit Breaker & Fast Fallback for NASA IRSA SIA2:** Replaced 25s HTTP timeout with 3.5s timeout and 30-second circuit breaker cooldown in `irsa_client.py` when remote IRSA returns 502/Proxy Error, ensuring instantaneous zero-latency offline demo serving. Fixed boresight pointing center overwriting target cutout coordinates in `OBSERVATION_REGISTRY`.
- **RA Boundary Wrapping on Gaia DR3 Markers:** In `CanvasViewer.tsx`, wrapped RA differences to `[-180, +180]` to prevent markers from flying off-canvas near 0°/360° celestial boundary.
- **Discovery Report Astrometric Motion Integration:** Wired `computeMotion` into `handleExportDiscoveryReport` in `App.tsx` so exported reports contain both Astrometric Motion and Photometric Light Curve analyses.
- **Guided Tour Modal Completeness:** Added missing Target 5 (Epsilon Indi B) to step 3 in `GuidedTourModal.tsx`.
- **Automated Test Suite Expansion:** Added `test_photometry_preset_differentiation`, bringing test suite to 44 passing tests in 1.87s.

## [1.2.0] - 2026-11-14
### Added — Section 13 Technical Differentiation & Production Hardening
- **Astrometric Proper Motion Vector Engine (`/api/science/motion`):** Implemented sub-pixel centroid displacement and 2D Fourier phase cross-correlation in `motion.py`. Computes angular shift, proper motion ($\mu$ in arcsec/yr and mas/yr), position angle ($\theta_{PA}$), and candidate classification ("High Proper Motion Candidate"), with dynamic dipole vector overlay on the difference image in `ComparisonView.tsx`.
- **Multi-Epoch Photometric Light Curve Dock (`/api/science/photometry`, `LightCurveChart.tsx`):** Circular aperture photometry with local background annulus subtraction in `photometry.py`. Computes automated variability index ($\sigma_F / \bar{F}$), flagging variable stars ("CONFIRMED VARIABLE") like RW Aurigae and R Draconis. Rendered as interactive SVG chart embedded in `MetadataPanel.tsx`.
- **Gaia DR3 & SIMBAD Celestial Catalog Overlay (`/api/science/catalogs`):** Cross-matching engine in `catalog_service.py` querying reference stars with proper motions, parallaxes, and G-magnitudes. Renders interactive diamond markers, proper-motion vectors, and magnitude labels directly onto the HTML5 Canvas in `CanvasViewer.tsx`.
- **Shareable URL Deep Linking:** Added bidirectional URL parameter synchronization (`/?ra=...&dec=...&fov=...&target=...&stretch=...&colormap=...`) and "Share URL" clipboard feedback button in `Header.tsx`.
- **Exportable Scientific Discovery Reports (`/api/science/report`, `DiscoveryReportModal.tsx`):** Automated report generator exporting structured JSON and publication-grade Markdown discovery reports with J2000 sexagesimal formatting and verified IRSA DOI 10.26131/IRSA678 citations.
- **Guided Educational Tour Modal (`GuidedTourModal.tsx`):** 4-step interactive educational walkthrough explaining SPHEREx LVF optics, dipole vs monopole signatures, official targets, and judging criteria alignment.
- **Multi-Container Docker & CI/CD Deployment:**
  - `backend/Dockerfile` with Python 3.11-slim.
  - `frontend/Dockerfile` with multi-stage Node 20 build and Nginx production serve.
  - `docker-compose.yml` for unified one-command local reproduction.
  - `render.yaml` for backend deployment and `frontend/vercel.json` for frontend SPA routing.
  - `.github/workflows/ci.yml` running pytest and frontend build.
- **Automated Test Suite Expansion:** Added `tests/test_science.py`, bringing total passing backend tests to 43.
- **IRSA HTTP 502/503 Fallback Hardening:** Fixed `irsa_client.py` returning empty list on non-200 responses; now automatically routes to verified demonstration dataset on remote server errors.
- **Documentation Suite:** Populated all 10 technical documents in `docs/` covering requirements, architecture, scientific method, data provenance, APIs, UI design, targets, judging strategy, and demo script.

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
