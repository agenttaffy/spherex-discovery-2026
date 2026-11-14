# SPHEREx Discovery — Prioritized Backlog

## P0: Core Challenge & Eligibility (ALL COMPLETED)
- [x] `P0-001` | COMPLETED | Live NASA IRSA SIA2 observation search integration (`irsa_client.py`)
- [x] `P0-002` | COMPLETED | Multi-extension FITS cutout pipeline & parsing (`cutout_service.py`, `fits_processing.py`)
- [x] `P0-003` | COMPLETED | Celestial coordinate validation (decimal & sexagesimal) (`coordinates.py`)
- [x] `P0-004` | COMPLETED | Interactive astronomical explorer frontend with HTML5 Canvas (`CanvasViewer.tsx`, `App.tsx`)
- [x] `P0-005` | COMPLETED | Multi-epoch chronological timeline player & Blink Comparator (`TimelinePlayer.tsx`)
- [x] `P0-006` | COMPLETED | Verification against all 5 official test targets (`probe_results.json`, `demo_dataset.json`)

## P1: Scientific Validity & High Judging Impact (ALL COMPLETED & HARDENED)
- [x] `P1-001` | COMPLETED | Calibrated differential image engine ($I_2 - I_1$) (`comparison.py`, `ComparisonView.tsx`)
- [x] `P1-002` | COMPLETED | Display contrast scaling engines (`asinh`, `zscale`, `linear`)
- [x] `P1-003` | COMPLETED | Data quality flag bitmask evaluation (`flags_processing.py`, `MetadataPanel.tsx`)
- [x] `P1-004` | COMPLETED | Local caching of 22 verified real FITS cutouts for judging demo reliability (`data/cache`)
- [x] `P1-005` | COMPLETED | Full automated test suite (52 pytest tests passing)
- [x] `P1-006` | COMPLETED | Offline / archive downtime resilience with automatic demo manifest fallback (`demo_service.py`, `irsa_client.py`)
- [x] `P1-007` | COMPLETED | Spherical RA 0°/360° boundary wrapping and NaN-safe differencing (`comparison.py`)
- [x] `P1-008` | COMPLETED | Sub-pixel 2D FFT image translation estimator (`image_registration.py`)
- [x] `P1-009` | COMPLETED | Side-by-side Epoch 1, Epoch 2, and Difference inspection cards with baseline $\Delta t$ (`ComparisonView.tsx`)
- [x] `P1-010` | COMPLETED | In-memory frame caching and adjacent prefetching for stutter-free playback (`api.ts`, `App.tsx`)

## P2: Advanced Astronomy & Technical Differentiation (ALL COMPLETED)
- [x] `P2-001` | COMPLETED | Gaia DR3 celestial source overlay with proper motion vectors (`catalog_service.py`, `CanvasViewer.tsx`)
- [x] `P2-002` | COMPLETED | Multi-epoch circular aperture photometric light curve dock with variability classification (`photometry.py`, `LightCurveChart.tsx`)
- [x] `P2-003` | COMPLETED | Shareable deep-link URL state encoder (`/?ra=...&dec=...&fov=...&target=...`) with clipboard feedback
- [x] `P2-004` | COMPLETED | Candidate astrometric motion detection & proper motion vector engine (`motion.py`, `/api/science/motion`)
- [x] `P2-005` | COMPLETED | Exportable scientific discovery report in Markdown and structured JSON with IRSA DOI 10.26131/IRSA678 citations (`report.py`, `DiscoveryReportModal.tsx`)
- [x] `P2-006` | COMPLETED | Guided educational exploration tour modal (`GuidedTourModal.tsx`)
- [x] `P2-007` | COMPLETED | Comprehensive documentation suite in `docs/` (10 technical documents)
- [x] `P2-008` | COMPLETED | Multi-container Dockerization and CI/CD workflows (`Dockerfile`, `docker-compose.yml`, `render.yaml`, `vercel.json`, `ci.yml`)

## P3: Architecture & Astronomy Viewer Enhancements (ALL COMPLETED)
- [x] `P3-001` | COMPLETED | Aladin Lite v3 Sky Context integration with survey switching (2MASS, AllWISE, DSS2, Pan-STARRS) (`AladinViewer.tsx`)
- [x] `P3-002` | COMPLETED | Interactive SPHEREx celestial footprint overlay box synced to RA/Dec/FOV (`AladinViewer.tsx`, `CanvasViewer.tsx`)
- [x] `P3-003` | COMPLETED | Dual-mode viewer switcher pill tabs (SPHEREx Canvas vs Aladin Lite Sky Context) (`CanvasViewer.tsx`)
- [x] `P3-004` | COMPLETED | Scientific WCS reprojection using `reproject_interp` with FFT shift fallback (`comparison.py`, `frames.py`)
- [x] `P3-005` | COMPLETED | WebP image encoding in `fits_processing.py` and API endpoints (`?format=webp`)
- [x] `P3-006` | COMPLETED | Added `reproject`, `pyvo`, and `astroquery` to `backend/requirements.txt`
- [x] `P3-007` | COMPLETED | Polished shadcn/ui-inspired glassmorphic cards, telemetry pills, and alignment method indicators
- [x] `P3-008` | COMPLETED | Fixed CanvasViewer unmount/remount blank redraw bug (`viewerMode` dependency), Aladin Lite overlay layer reuse/memory leak prevention, 0°/360° RA seam crossing handling, and 3D spectral WCS celestial extraction in reprojection

## P4: Potential Considerations & Advanced Science Discoveries (ALL COMPLETED)
- [x] `P4-001` | COMPLETED | On-the-fly spectra generation endpoint (`GET /api/science/spectrum`) gathering aperture fluxes across the 6 SPHEREx detector arrays (D1: 0.75–1.12 µm, D2: 1.12–1.68 µm, D3: 1.68–2.42 µm, D4: 2.42–3.82 µm, D5: 3.82–4.42 µm, D6: 4.42–5.00 µm) (`spectrum.py`)
- [x] `P4-002` | COMPLETED | Interactive 102-channel spectrophotometric SED chart (`SpectrumChart.tsx`) with detector band color-coding, smooth continuum modeling, and physical classification (Brown Dwarfs, M-Dwarfs, IR Excess) integrated into `MetadataPanel.tsx` telemetry tabs
- [x] `P4-003` | COMPLETED | Astronomical image co-addition & stacking endpoint (`POST /api/frames/stack`) supporting `mean`, `median`, and `sum` with celestial WCS registration via `reproject_interp` (`stacking.py`, `frames.py`)
- [x] `P4-004` | COMPLETED | Operation mode switcher in `ComparisonView.tsx`: "Difference ($I_2 - I_1$)" (reveals moving sources/dipoles and transients) vs "Co-Add Stack ($I_1 + I_2$)" (reveals faint static infrared sources and brown dwarfs) with $\sim\sqrt{N}$ SNR gain badge and noise suppression telemetry
- [x] `P4-005` | COMPLETED | Comprehensive automated test suite expansion with 12 new tests in `test_stacking_and_spectrum.py`, bringing total passing backend tests to 64 (0 failures)
