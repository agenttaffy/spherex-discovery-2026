# Agent Handoff Document

## 2026-11-14 — Sky context and exploration update

- Multi-release search queries the configured SPHEREx collections explicitly and shares the result limit across them; demo fallback respects the requested search radius. `SPHEREX_SEARCH_COLLECTIONS` defaults to DR1 and QR3 and is configurable. The full working-tree backend suite passed 110 tests with two Astropy FITSFixedWarnings, and the frontend build passed with the known large Aladin chunk warning.
- Follow-up: the observation timeline uses one native range control rather than a keyboard stop for every epoch. Browser testing moved from epoch 1 to 2 with the right-arrow key and inspected the native canvas and metadata at 375px width. The initial archive connectivity badge now reports a check, not the provenance of the displayed observation. The panel no longer presents a fixed pixel scale as measured, a pixel standard deviation as noise, or non-archive fixtures as NASA links. The target controls explain FOV and detector choices.
- Aladin Lite is loaded lazily from the installed v3 package, after `A.init`. It centers on the last successful search coordinates and overlays a distinct target marker and the actual pixel-edge celestial WCS footprint. A missing or simulated cutout has no fabricated footprint. The catalog overlay uses the cutout's inverse WCS and does not extrapolate proper motion.
- The native canvas identifies live, cached, demo, simulated, and local-fixture image provenance. Search and analysis panels can be collapsed, expensive analysis is loaded when opened, and viewer controls no longer float over the image. Search field edits do not change the active coordinates or cutout size until a search succeeds.
- 2MASS and DSS2 context imagery is served by IRSA's HiPS mirror; credits and survey-specific terms are shown in the app. See RESEARCH.md for sources and service observations.
- Full backend tests passed: 110 tests with two Astropy FITSFixedWarnings. The frontend production build and 41 source-based accessibility checks passed; Aladin's lazily loaded package triggers a large-chunk warning. Desktop and narrow mobile views, a live sky, cached demonstration frames, an injected survey failure/retry, a survey switch, a seam coordinate, and limited keyboard navigation were inspected. See TEST_RESULTS.md for scope and caveats.
- A browser resource inventory confirmed requests for individual 2MASS sky tiles and the image visibly rendered, with no captured Chrome console warnings or errors; individual response status codes were not exposed. An isolated preview forced the reduced-motion CSS rule on and confirmed the resulting browser styles and keyboard timeline behavior; actual operating-system preference detection and physical screen-reader use remain untested. This is not WCAG conformance testing. Independently validate source identity and full accessibility before release.
- Difference and stack remain blocked pending validated per-pixel spectral compatibility. A calibration artifact was located and verified against its catalog MD5 in this session; the separate unintegrated spectral-calibration module and tests are unfinished work, not a reason to remove that guard.

## 2026-11-14 — Current session handoff

**Safety update:** Difference and co-addition endpoints return HTTP 422 until per-pixel spectral compatibility is validated using separate spectral WCS calibration files; blink remains available. The WCS-WAVE values are approximate visualization estimates. See RESEARCH.md and TODO.md. IRSA documents `CWAVE` and `CBAND` full-detector arrays and `CRPIX1A/CRPIX2A` cutout-to-detector mapping.

- Continued the existing documentation edits and preserved the working tree. Corrected unverified target claims and labeled the spectrum as at most six observed detector-band measurements plus an illustrative continuum.
- Added search-result provenance, kept quality-state metadata through the API, labeled estimated versus propagated uncertainty, prevented estimated errors from entering the temperature fit, and changed variability claims to a heuristic. Search and frame responses now guard against stale results; shared coordinates take precedence over a preset.
- Verified 99 backend tests with two Astropy FITSFixedWarnings, frontend production build, 41 source-based accessibility checks, and 22 demo assets. The backend suite and IRSA HTTP 200 check required normal networking; restricted execution stalled at the first TestClient request. A desktop browser was inspected against an already-running backend that lacked the new provenance field; it displayed the safe unknown state. A separate preview with the updated backend displayed an IRSA search result and was visually inspected at desktop and 375px widths; the mobile science panel was opened. Physical screen-reader audio was not tested.
- Photometry now refuses clipped or masked apertures and empty source-free annuli instead of scaling missing light or using contaminated background. This can produce zero observed bands for cached targets; that is an unavailable-data state, not a non-detection.
- Release selection: spectrum and photometry now return results only for the selected release rather than silently widening to all releases on empty results.
- Follow-up cache correction: live cutouts now use `cutout-v2` keys including center and size, excluding older potentially mislabeled cache entries. Demo cutouts remain fixed-coverage and are labeled. Further live/offline coverage checks are open.
- Open scientific work: validate actual wavelength overlap within detector arrays, aperture edge/mask correction and uncertainty propagation, epoch provenance through every analysis and report, and target-object detections using independent evidence. Current background errors can be estimates and are not accepted by the temperature fit. Live search/cutout operation and visual states need end-to-end verification against the newly started backend.


## 1. Last Completed Work
- **Scientific Truthfulness Follow-up Pass (Commits `8757e6b`, `208aa15`):**
  - **Neutral Broadband Continuum Shape Descriptions & API Cleanup:** Replaced broad-band slope inferred astrophysical classifications ("Brown Dwarf Candidate", "Cool Stellar Atmosphere", etc.) with neutral measured-shape descriptions ("flux rises toward longer measured bands", "flux falls toward longer measured bands", "peak among measured detector bands", "insufficient observed coverage"). Added `continuum_shape` field to summary. In commit `208aa15`, `spectral_class` was completely removed from the API schemas, backend models, and frontend types to avoid any false impression of spectral typing.
  - **Spectrophotometry Truthfulness:** Documented that SED analysis measures aperture photometry across up to six detector-band points (D1–D6) with an illustrative/interpolated 102-point continuum; this is explicitly **not 102 observed resolved SPHEREx channels**.
  - **Strict Temperature Fit Conditions:** In `fit_blackbody_continuum`, two-parameter fit requires at least 3 distinct measured detector bands with valid propagated photometric errors ($\text{dof} \ge 1$). Removed 10% error substitution. If inputs lack error, or bands $< 3$, or curvature is unconstrained, returns `status: "unavailable"` and no temperature. A temperature is strictly an optional constrained single-temperature continuum fit, not a known object's physical temperature.
  - **Zero-Observation Unavailable Metrics:** When zero archive bands exist, peak wavelength, peak detector, peak flux, estimated temperature, and integrated flux are set to `None`. No synthetic peaks are reported as measured.
  - **Frontend & Discovery Report Updates:** `SpectrumChart.tsx` displays "Continuum Shape:" and italic caveat; `report.py` clearly documents single-temperature continuum fit without presenting it as verified physical temperature.
  - **Regression Test Coverage:** Full backend suite passing **93 tests (with 2 Astropy FITSFixedWarnings)** in 10.11s; accessibility checks passing **41/41**; clean frontend build in 2.55s (1,497 modules); 22/22 demonstration cutouts verified; IRSA SIA endpoint verified (HTTP 200).

## 2. Current Working State
- **Backend:** Starts cleanly with `python -m uvicorn app.main:app --port 8000`. All 93 pytest tests pass (with 2 Astropy FITSFixedWarnings on 3D WCS dimension reduction tests).
- **Frontend:** Builds cleanly with `npm run build` (1,497 modules, 0 type errors, 0 warnings).
- **Accessibility & Responsive:** All 41 automated checks pass in `node scripts/verify_accessibility_and_responsive.mjs`.
- **Demo Mode:** Local caching of 22 verified FITS cutouts enables immediate offline presentation and judging with circuit breaker fallback on remote outages.
- **Environment & Connectivity:** `python scripts/verify_environment.py` passes outside restricted network with NASA/IPAC IRSA SIA returning HTTP 200.
- **Manual Verification Status:** Automated test suites verified; no manual physical visual inspection or physical screen-reader audio checks were performed.
- **Screenshots:** 4 visual acceptance screenshots preserved in `docs/screenshots/` (desktop and mobile 320px).

## 3. Current Blocker / Limitations
- None fatal.
- Live NASA/IPAC IRSA SIA service occasionally returns HTTP 502 Proxy Error during upstream maintenance; automatically safeguarded by backend circuit breaker and offline demo cutouts.
- Aladin Lite v3 context tiles require active internet connection to CDS servers; fallback to SPHEREx native HTML5 Canvas works 100% offline.
- Fractional-pixel polygon clipping is not implemented for apertures intersecting focal plane borders (marked unavailable).

## 4. Verification Commands
```bash
# 1. Environment & IRSA Connectivity
python scripts/verify_environment.py

# 2. Demonstration Assets Verification
python scripts/verify_demo.py

# 3. Backend Test Suite (93 tests, 2 Astropy FITSFixedWarnings)
$env:PYTHONPATH="backend"
python -m pytest -v

# 4. Frontend Typecheck & Production Build
cd frontend
npm run build

# 5. Accessibility & Responsive Verification (41 checks)
cd ..
node scripts/verify_accessibility_and_responsive.mjs
```
