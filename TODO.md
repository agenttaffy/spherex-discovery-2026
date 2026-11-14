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
- [x] `P4-005` | COMPLETED | Comprehensive automated test suite expansion with tests in `test_stacking_and_spectrum.py`, bringing total passing backend tests to 69 (0 failures)
- [x] `P4-006` | COMPLETED | Robust sigma-clipped background noise isolation, non-overlapping celestial WCS footprint rejection, duplicate frame validation, multi-epoch stacking scope switcher, and detector array filter buttons in `SpectrumChart.tsx`

## P5: Scientific Correctness Audit & Codebase Hardening (ALL COMPLETED & VERIFIED)
- [x] `P5-001` | COMPLETED | Corrected SPHEREx FLAGS parsing using documented Level 2 FITS header metadata (`MSKN*`/`MSKM*`); non-zero pixels are not automatically bad; distinguished nominal astronomical `SOURCE` (bit 21, 2097152) and `FULLSAMPLE` (bit 12, 4096) from fatal quality defects (`NONFUNC` dead pixel = 64, `OVERFLOW` saturation = 2, `SUR_ERROR` fit failure = 4, `HOT` = 1024, `COLD` = 2048, `NONLINEAR` = 32768, `SNOWBALL` cosmic ray = 134217728, `TRANSIENT` = 1) (`fits_processing.py`)
- [x] `P5-002` | COMPLETED | Photometry and SED spectra measure requested celestial RA/Dec through each image WCS (`world_to_pixel`) rather than brightest pixel; read `VARIANCE` FITS extension to compute real photometric flux uncertainties ($\sigma_F = \sqrt{\sum \sigma_i^2}$); excluded fatal defect mask pixels (`photometry.py`, `spectrum.py`)
- [x] `P5-003` | COMPLETED | Labeled 102-channel continuum model explicitly as "Estimated Continuum Model (Interpolated)" and clearly separated it from observed SPHEREx channels in both backend and frontend (`spectrum.py`, `SpectrumChart.tsx`)
- [x] `P5-004` | COMPLETED | Astrometric motion tracks requested celestial target (RA, Dec) via WCS across epochs, locates subpixel centroid around expected coordinates, converts shifts through celestial WCS via `pixel_to_world`, and computes annual proper motion $\mu$ using true epoch baseline in years $\Delta t = |t_2 - t_1|$ (`motion.py`, `science.py`)
- [x] `P5-005` | COMPLETED | Differencing enforces LVF wavelength compatibility (`em_min`, `em_max`), preserves data quality masks as mid-gray (128), and returns clear descriptive errors on failed reprojection or non-overlapping celestial footprints (`comparison.py`, `frames.py`)
- [x] `P5-006` | COMPLETED | Stacking co-adds only compatible detector arrays, propagates variance ($\text{Var}_{\text{stack}} = \frac{1}{N^2} \sum \text{Var}_i$ for mean co-addition), propagates bitwise OR of fatal quality masks, and accurately reports measured SNR improvement (`stacking.py`, `frames.py`)
- [x] `P5-007` | COMPLETED | Disambiguated and explicitly labeled fallback catalog provenance: "Curated Reference Catalog (Demo)" vs "Live ESA Gaia TAP" (`catalogs.py`, `catalog_service.py`, `CanvasViewer.tsx`, `astronomy.ts`)
- [x] `P5-008` | COMPLETED | Created comprehensive regression test suite (`test_scientific_audit_regression.py`) covering all 6 priorities, bringing total passing backend tests to 77 (0 failures) with clean frontend build
- [x] `P5-009` | COMPLETED | Skeptical audit hardening: integrated official SPHEREx WCS-WAVE dispersion calibration, discrete geometric boundary aperture area coverage correction, masked-pixel variance propagation isolation in co-addition, equatorial vector proper motion components $(\Delta\alpha\cos\delta, \Delta\delta)$, and strict target coordinate anchoring in photometry and astrometry (81 passing tests, clean frontend build)

## P6: UI/UX Refinement, NASA/USWDS Accessibility & WCAG 2.2 AA Compliance (ALL COMPLETED & VERIFIED)
- [x] `P6-001` | COMPLETED | Implemented accessible tabular data views (`<details><summary>View Accessible Data Table</summary>...`) alongside SVG charts in `SpectrumChart.tsx` and `LightCurveChart.tsx` with semantic `role="table"`, `<caption className="sr-only">`, and `<th scope="col">`
- [x] `P6-002` | COMPLETED | Added full canvas keyboard navigation (Arrow keys for panning, `+`/`=` for zoom in, `-`/`_` for zoom out, `0` for reset view) with screen-reader live announcements (`aria-live="polite"`), `tabIndex={0}`, and visible keyboard hint badge in `CanvasViewer.tsx`
- [x] `P6-003` | COMPLETED | Upgraded interface text contrast to meet WCAG 2.2 AA (>= 4.5:1 ratio for normal text and >= 3:1 for essential controls) across all panels, labels, metrics, and chart axes
- [x] `P6-004` | COMPLETED | Standardized high-visibility focus rings (`focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none`) globally in `index.css` and on all interactive controls, buttons, selects, and inputs
- [x] `P6-005` | COMPLETED | Enhanced ARIA attributes throughout the application: `role="tablist"` and `role="tab"` with `aria-selected` and `aria-controls` for main navigation, telemetry switcher, comparison mode, viewer mode, and mobile tabs; `role="dialog"` with `aria-modal="true"` on modals
- [x] `P6-006` | COMPLETED | Responsive reflow down to 320px viewport without horizontal page overflow: added deliberate mobile panel switcher tabs (`[Canvas] [Target] [SED & Telemetry]`), responsive flex wrapping on headers and timeline player, and `min-width: 320px` safety
- [x] `P6-007` | COMPLETED | Created automated verification test suite (`scripts/verify_accessibility_and_responsive.mjs`) covering all 34 accessibility and responsive constraints; 81 backend tests passing; clean frontend build
- [x] `P6-008` | COMPLETED | Implemented perceptually balanced diverging colormap (`apply_diverging_colormap`, Cool-Warm centered at 128 / zero net flux residual) per NASA Data Visualization guidelines, with interactive palette toggle and colorbar legend in `ComparisonView.tsx`
- [x] `P6-009` | COMPLETED | Implemented 102-Channel spectrophotometric continuum model accessible data table in `SpectrumChart.tsx` with dataset switcher tablist (`Observed Bands` vs `102-Channel Continuum Model`), enabling screen-reader users to traverse all 102 synthesized spectrophotometric channels
- [x] `P6-010` | COMPLETED | Fixed table semantics and WCAG 2.2 compliance in `LightCurveChart.tsx` by replacing invalid `role="button"` on `<tr>` with semantic `<button type="button">` inside `<td className="...">`
- [x] `P6-011` | COMPLETED | Added proactive detector incompatibility notice and smart auto-pairing of compatible detector epochs in `ComparisonView.tsx`, plus accessible tabular view of comparison and proper motion metrics
- [x] `P6-012` | COMPLETED | Multi-Epoch Survey Release Selector (`ALL` surveys, multi-epoch DR1 + QR3) in `SearchControls.tsx` and `demo_service.py`, with deep-link URL state synchronization for active observation (`obs`) and tab (`tab`)
- [x] `P6-013` | COMPLETED | Visual acceptance verification via headless Chrome capturing real desktop (1280x800) and mobile (320x640) screenshots in `docs/screenshots/`; automated accessibility test suite expanded to 41 passing checks; backend pytest suite expanded to 82 passing tests
- [x] `P6-014` | COMPLETED | Scientific truthfulness audit & source-mask background exclusion: distinguished source masks from fatal defects in aperture photometry background subtraction; labeled 102-channel continuum model truthfully in UI and Discovery Reports; added regression tests bringing total verified backend pytest tests to 84 (0 failures) and accessibility checks to 41 (0 failures)
- [x] `P6-015` | COMPLETED | Pointing registration shift isolation & lightcurve source mask propagation: projected epoch 2 celestial position back into reference WCS grid to prevent telescope pointing registration offsets from falsely presenting as target proper motion; wired source-mask background exclusion across multi-epoch light curves and /science/photometry; added regression tests bringing verified backend pytest suite to 86 tests (0 failures) and accessibility checks to 41 (0 failures)
