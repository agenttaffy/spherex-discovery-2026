# Changelog

All notable changes to the SPHEREx Discovery project will be documented in this file.

## [1.4.1] - 2026-11-14
### Added & Hardened (Skeptical Review & Visual Acceptance Round)
- **Perceptually Balanced Diverging Colormap for Difference Images:** Added `apply_diverging_colormap` in `fits_processing.py` (Cool-Warm: Blue -> Light Neutral -> Crimson Red) strictly centered at 128 (zero net flux residual) per NASA Data Visualization guidance. Exposed via `/api/frames/diff` (`colormapped_base64`) with interactive palette toggle and colorbar legend in `ComparisonView.tsx`.
- **102-Channel Spectrophotometric Model Accessible Data Table:** Enhanced `SpectrumChart.tsx`'s accessible data table disclosure with an accessible tab switcher (`role="tablist"` / `role="tab"` for `Observed Bands` vs `102-Channel Continuum Model`), enabling screen-reader and keyboard users to inspect all 102 synthesized channels with channel number, detector, wavelength, and modeled flux.
- **Strict HTML/ARIA Table Compliance:** Corrected table semantics in `LightCurveChart.tsx` by eliminating invalid `role="button"` on `<tr>` elements and encapsulating selection actions in semantic `<button type="button">` elements inside `<td className="...">`.
- **Dynamic Speech Announcement Feedback:** Enhanced `CanvasViewer.tsx` keyboard navigation to include dynamic coordinates in announcement strings (`Offset: X=..., Y=...`), preventing screen reader speech silence on consecutive arrow keypresses, and added zoom boundary limit vocalization (800% max, 40% min).
- **Proactive Incompatibility Alert & Smart Compatible Epoch Pairing:** In `ComparisonView.tsx`, added proactive warnings for incompatible detector bands and auto-paired compatible detector epochs upon mounting or target selection.
- **Multi-Epoch Survey Selection & Deep-Link State Synchronization:** Added `ALL (Multi-Epoch)` survey selection in `SearchControls.tsx` and updated `demo_service.py` to support multi-epoch matching. Synchronized active observation (`obs`) and tab (`tab`) with URL deep links.
- **Visual Acceptance Verification:** Captured real headless Chrome screenshots at desktop (1280x800) and mobile (320x640) viewports in `docs/screenshots/`. Expanded automated accessibility test suite to 41 passing checks; expanded backend pytest test suite to 82 passing tests.

## [1.4.0] - 2026-11-14
### Added & Enhanced — UI/UX Refinement, NASA/USWDS Accessibility & WCAG 2.2 AA Compliance
- **Accessible Tabular Data Tables:** Implemented `<details><summary>View Accessible Data Table</summary>...` alongside SVG charts in `SpectrumChart.tsx` and `LightCurveChart.tsx` with semantic `role="table"`, `<caption className="sr-only">`, and `<th scope="col">` column headers for screen-reader and keyboard users.
- **Canvas Keyboard Controls:** Added arrow key panning (ArrowUp, ArrowDown, ArrowLeft, ArrowRight), zoom controls (`+`/`-`), and view reset (`0`) with `tabIndex={0}`, high-visibility focus indicators, and screen-reader announcements via `aria-live="polite"`. Added visual keyboard shortcut indicator pill in `CanvasViewer.tsx`.
- **WCAG 2.2 AA Color Contrast:** Elevated typography, telemetry labels, and chart axis text to meet or exceed 4.5:1 contrast ratio against deep space-navy backgrounds.
- **High-Visibility Keyboard Focus Indicators:** Standardized global `:focus-visible` styling (`outline: 2px solid #22d3ee; outline-offset: 2px;`) in `index.css` and explicit `focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none` on all interactive buttons, selects, inputs, and modal controls.
- **ARIA Navigation & Modal Roles:** Structured main navigation, telemetry switcher, comparison mode switcher, viewer switcher, and mobile tabs with `role="tablist"` and `role="tab"` (`aria-selected`, `aria-controls`); assigned `role="dialog"` with `aria-modal="true"` to `GuidedTourModal.tsx` and `DiscoveryReportModal.tsx`.
- **320px Responsive Viewport Reflow:** Added deliberate mobile workspace panel switcher tabs (`[Canvas] [Target] [SED & Telemetry]`), responsive flex wrapping on headers and timeline player, and `min-width: 320px` safety preventing horizontal page overflow down to 320 CSS pixels.
- **Automated Verification:** Added `scripts/verify_accessibility_and_responsive.mjs` verifying all 34 accessibility and responsive constraints; 81 backend pytest tests passing; clean frontend build (`tsc && vite build`).

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
