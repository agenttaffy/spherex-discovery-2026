# SPHEREx Discovery — Project State

> **Current availability baseline.** Dated observation search, FITS viewing, timeline/blink, Gaia and WISE sky context have verification evidence. IRSA search remains intermittent. Newly requested image cutouts use the public cloud first and fall back to IRSA; the DR1 cube reads bounded cloud ranges and can use an explicitly dated release if search is unavailable. Candidate motion and target photometry still need independent source validation. Difference and co-add validate matched per-pixel calibrations; real two-image and three-image field comparisons have independent numerical checks. The former synthetic continuum and temperature estimate were removed. The inspector and 102 Bands view show a co-added sky-pixel sample, not a confirmed target spectrum. Historical milestones below describe earlier implementations and tests. See [the current traceability matrix](docs/CHALLENGE_REQUIREMENTS.md).


**Current documentation baseline:** 2026-11-15

Chrome verification covered direct 102 Bands links, timeline playback, the Gaia DR3 search, and the checked RW Aurigae difference and co-add. The comparison cards identify excluded pixels with a checkerboard. [Browser verification](TEST_RESULTS.md#browser-verification-2026-11-15)

Explorer distinguishes IRSA search outages from a valid empty result. When no dated images are available, Explorer can show a labeled DR1 channel map from the public cloud at the requested coordinates. The timeline and calibrated comparisons still require dated observations.

The observation snapshot maintenance commands can stage and import one DR1 or QR3 search, including deep collections, with its original query and UTC acquisition time. The import path is tested. A successful live capture still depends on IRSA availability. [Refresh instructions](README.md#cloud-access-and-archive-availability)

Difference & Stack can check up to twelve listed same-detector partners for the selected exposure using cached FITS cutouts and verified calibration bytes. The check reports unavailable inputs separately and reuses the calibrated comparison rules without issuing archive requests.

The main frontend now shares the orbital candidate’s blue-violet glass surfaces, local Geist and Instrument Serif fonts, and coral action accents. The Explorer frames the full FITS image at fit zoom with nearest-neighbor rendering. The existing research views and data sources remain in the same navigation. [Browser and science checks](TEST_RESULTS.md#glass-observatory-integration)
**Earlier implementation milestone:** Phase 8 Scientific Truthfulness Pass (Neutral Broadband Continuum Shape Descriptions Without Astrobiological/Stellar Class Inferences, Strict Temperature Fit Constraints Requiring >= 3 Distinct Bands with Propagated Uncertainties, Unavailable Zero-Observation Summary Metrics Without Synthetic Peak Claims, Explicit Unavailable Photometry State on Projection Failure, Missing Quality Mask State Without Guessing Bits, Uncensored SNR Improvement Estimator in Stacking, Preserved NaN/Inf Masks Without Fabricated Fill Values, Diverging Difference Palettes, 102-Channel Accessible Spectrophotometric Continuum Tables, 93 Passing Pytest Tests, 41 Passing Accessibility Checks, Clean Production Build).

---

> **Current verification note:** Claims below describe implemented features and historical results, not independently validated scientific performance or WCAG conformance. See HANDOFF.md and TEST_RESULTS.md for current evidence and limitations.

> **Comparison safety:** Difference and two-frame co-add require a checksum-verified calibration for each exposure and aligned, usable pixels with sufficient nominal passband overlap. Incompatible pairs return HTTP 422. The D5 field example retained 207 of 225 pixels, and the staged WISE pair was rejected. Blink remains available for visual inspection. [Calibration coverage and remaining gaps](docs/DETECTOR_CALIBRATION.md)

## 1. Implemented Features
- **Scientific Visualization & Accessibility Features (`SpectrumChart.tsx`, `LightCurveChart.tsx`, `CanvasViewer.tsx`, `ComparisonView.tsx`, `index.css`):**
  - **Diverging Colormap for Difference Imagery (`fits_processing.py`, `ComparisonView.tsx`):** Implemented `apply_diverging_colormap` (Cool-Warm: Blue -> Light Neutral -> Crimson Red) centered strictly at 128 (zero net flux residual) per NASA Data Visualization guidelines, complete with palette toggle and colorbar legend.
  - **102-Channel Spectrophotometric Continuum Accessible Table (`SpectrumChart.tsx`):** Added accessible dataset switcher tablist (`Observed Bands` vs `102-Channel Continuum Model`), enabling screen-reader and keyboard users to inspect all 102 synthesized spectrophotometric channels with channel index, detector, wavelength, and flux.
  - **HTML/ARIA Table Semantics (`LightCurveChart.tsx`):** Removed invalid `role="button"` from table rows (`<tr>`); encapsulated interactive selection in semantic `<button type="button">` inside `<td className="...">` with visible focus rings.
  - **Dynamic Canvas Speech Announcements (`CanvasViewer.tsx`):** Dynamic coordinates in announcement strings (`Offset: X=..., Y=...`) eliminate screen reader silence on consecutive pan keypresses, with clear announcements when zoom limits (800% max, 40% min) are reached.
  - **Accessible Tabular Data Alternatives:** Implemented `<details><summary>View Accessible Data Table</summary>...` alongside SVG charts and comparison metrics with semantic `role="table"`, `<caption className="sr-only">`, and `<th scope="col">` column headers for full screen-reader accessibility.
  - **Canvas Keyboard Controls:** Added arrow key panning (ArrowUp, ArrowDown, ArrowLeft, ArrowRight), zoom (`+`/`-`), and reset (`0`/`Home`) with `tabIndex={0}`, visible focus indicators, and screen-reader announcements via `aria-live="polite"`.
  - **WCAG 2.2 AA Color Contrast:** Standardized typography and metadata text across the application to meet or exceed 4.5:1 contrast against dark space-navy backgrounds.
  - **High-Visibility Focus Indicators:** Standardized global `focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none` in `index.css` and on all interactive controls.
  - **ARIA Role Hierarchy:** Equipped all primary navigation tabs, telemetry modes, viewer modes, and comparison modes with `role="tablist"` and `role="tab"` (`aria-selected`, `aria-controls`), and modal dialogs with `role="dialog"` (`aria-modal="true"`).
  - **320px Responsive Viewport Reflow:** Added deliberate mobile workspace panel switcher tabs (`[Canvas] [Target] [SED & Telemetry]`), responsive wrapping on headers and timeline player, and `min-width: 320px` safety preventing horizontal page overflow.
  - **Multi-Epoch Survey Search & Deep-Link Synchronization (`SearchControls.tsx`, `App.tsx`, `demo_service.py`):** Added `ALL (Multi-Epoch)` survey release button; synchronized active observation (`obs`) and tab (`tab`) with URL deep links.
- **SPHEREx Level 2 FLAGS Bit Definitions & Source Mask Distinction (`fits_processing.py`):**
  - Parses documented `MSKN*`/`MSKM*` FITS header cards dynamically.
  - Distinguishes nominal astronomical source detections (`SOURCE`, bit 21 = 2,097,152; `FULLSAMPLE`, bit 12 = 4,096) from fatal detector defects (`NONFUNC` dead pixel = 64, `OVERFLOW` saturation = 2, `SUR_ERROR` ramp fit error = 4, `HOT` = 1,024, `COLD` = 2,048, `NONLINEAR` = 32,768, `SNOWBALL` cosmic ray = 134,217,728, `TRANSIENT` = 1).
  - Eliminates the previous bug where all 100% of pixels in cutouts with real astronomical sources were flagged as bad pixels.
  - Functions `extract_fatal_quality_mask` and `extract_variance_data` provided for downstream science modules.
- **WCS-Transformed Aperture Photometry & VARIANCE Propagation (`photometry.py`):**
  - Transforms requested celestial `(RA, Dec)` directly to pixel coordinates `(x, y)` using Astropy celestial WCS (`world_to_pixel`) rather than wandering off to arbitrary maximum-pixel coordinates.
  - Reads the `VARIANCE` FITS extension to compute true photometric flux uncertainties ($\sigma_F = \sqrt{\sum \sigma_i^2 + \frac{N_{ap}^2}{N_{ann}} \sigma_{ann}^2}$) rather than uncalibrated proxies.
  - Excludes fatal quality mask pixels from aperture and background calculations.
- **SED Spectra Generation & Estimated Continuum Model Separation (`spectrum.py`, `SpectrumChart.tsx`):**
  - Measures target `(RA, Dec)` through each cutout's celestial WCS and propagates `VARIANCE` error bars.
  - Keeps 6 detector bands strictly separated.
  - Does NOT call interpolated curves "102 observed channels"; presents actual observed detector array measurements with error bars, and explicitly labels the 102-point interpolated profile as "Estimated Continuum Model (Interpolated)".
- **WCS Celestial Target Tracking & True Epoch Baselines (`motion.py`):**
  - Tracks requested celestial target `(RA, Dec)` across epochs via WCS, locating subpixel centroids in a local window around expected position rather than locking onto unrelated brighter field stars.
  - Converts subpixel centroid shifts $(\Delta x, \Delta y)$ to celestial equatorial shifts $(\Delta\alpha \cos\delta, \Delta\delta)$ via WCS `pixel_to_world`.
  - Computes annual proper motion $\mu$ using true epoch baseline in years $\Delta t = |t_2 - t_1|$.
- **Calibrated pair differencing** (`frames.py`, `calibrated_comparison.py`): Uses exact checksum-verified spectral WCS maps and native celestial WCS. Accepted pairs must have aligned, usable pixels with at least 90% nominal passband overlap. The response preserves the valid-pixel mask and supplies calibration provenance.
- **Compatible pair co-addition:** The same native-grid and passband checks gate two-exposure co-addition. The app propagates input variance under an independent-noise assumption.
- **Reference Catalog Provenance Disambiguation (`catalogs.py`, `catalog_service.py`, `CanvasViewer.tsx`):**
  - Explicitly labels fallback catalog sources as "Curated Reference Catalog (Demo)" vs "Live ESA Gaia TAP".
  - Shows provenance distinction in CanvasViewer overlay labels and toggle buttons.
- **On-The-Fly Spectra Generation (`/api/science/spectrum`, `spectrum.py`, `SpectrumChart.tsx`):**
  - Instantaneous calibrated Spectral Energy Distribution (SED: Flux vs. Wavelength $\lambda$) across SPHEREx's 0.75 µm to 5.00 µm range.
  - Queries and aggregates multi-epoch circular aperture photometry across up to 6 SPHEREx detector arrays (D1: 0.75–1.12 µm, D2: 1.12–1.68 µm, D3: 1.68–2.42 µm, D4: 2.42–3.82 µm, D5: 3.82–4.42 µm, D6: 4.42–5.00 µm).
  - Synthesizes up to six measured detector-band points (D1–D6) with approximate WCS-WAVE effective wavelengths and `VARIANCE` error bars where available, accompanied by an illustrative/interpolated 102-point continuum (17 channels per detector array).
  - **Truthfulness Boundary:** This is explicitly **not 102 observed resolved SPHEREx channels**. The 102 channels represent an interpolated continuum curve.
  - Neutral broadband shape descriptor (`continuum_shape`) describing empirical trends ("flux rises toward longer measured bands", "flux falls toward longer measured bands", "peak among measured detector bands", or "insufficient observed coverage"). Inferred astrophysical classifications were removed from the API (`spectral_class` removed).
  - Constrained single-temperature blackbody continuum fit ($B_\nu(T)$): Requires $\ge 3$ distinct measured detector bands with valid propagated photometric uncertainties to guarantee positive residual degrees of freedom ($\text{dof} \ge 1$). Unsupported 10% error substitutions are disallowed. The temperature is strictly an optional single-temperature continuum fit, not an object's known physical temperature.
  - When zero archive bands exist, peak wavelength, peak detector, peak flux, estimated temperature, and integrated flux are set to `None` (`unavailable`), with `peak_is_measured: False`.
  - Telemetry dock tab switcher in `MetadataPanel.tsx` toggling between "Observed Bands · Continuum (Interpolated)" and "Light Curve".
- **Comparison View** (`/api/frames/stack`, `ComparisonView.tsx`): Offers mean and sum for a selected calibrated pair. Larger stacks are unsupported. Empirical SNR gain is unavailable for the current comparison response.
- **Aladin Lite v3 Sky Context:** The bundled viewer initializes on demand and centers on the selected coordinates. Remote 2MASS and DSS2 HiPS tiles provide contextual imagery. The viewer overlays a cutout footprint when valid celestial WCS is available. The prepared native SPHEREx canvas remains available when the context service fails.
- **Historical reprojection tools:** Reprojection and FFT alignment code remain in the science modules. The current calibrated difference and co-add endpoints use neighboring native samples within the celestial WCS alignment gate.
- **WebP Image Output Engine (`backend/app/science/fits_processing.py`):**
  - Added `render_image_to_base64` supporting `format: Literal["png", "webp"] = "png"`.
  - Smaller payload footprints for rapid multi-epoch timeline scrubbing and Blink comparator playback.
  - Query parameter support (`/api/frames/{id}?format=webp`) and diff body formatting (`format: "webp"`).
- **NASA/IPAC IRSA SIA2 Client & Resilient Offline Demo Architecture:**
  - Live programmatic queries against `spherex_dr1` and `spherex_qr3` collections.
  - The default manifest lists 22 files. Only its four RW Aurigae cutouts cover a preset’s exposure-epoch prediction. The optional ten-file stage covers all five presets at two epochs. See the [target validation report](docs/TARGET_VALIDATION.md).
  - Automatic circuit breaker fallback on remote archive latency or HTTP 502/503.
- **Display-Only Contrast Scaling:** `asinh` (arcsinh), `zscale`, and `linear` stretching engines with grayscale and `inferno` colormaps.
- **Differential Image Engine:**
  - Robust against non-finite values (NaN/Inf) with finite stats calculation and mid-gray (128) baseline for missing pixels.
  - Spherical RA boundary wrapping across 0°/360° celestial seam.
  - Duplicate epoch self-comparison prevention.
- **Astrometric Proper Motion Vector Engine (`/api/science/motion`):**
  - Sub-pixel 2D FFT phase cross-correlation + local $5 \times 5$ centroid tracker.
  - Computes angular displacement ($\Delta\theta$ in arcseconds), annual proper motion ($\mu$ in arcsec/year and mas/year), position angle ($\theta_{PA}$), and candidate classification ("High Proper Motion Candidate").
  - Target-object motion has not been independently verified in this session.
- **Multi-Epoch Photometric Light Curve Dock (`/api/science/photometry`, `LightCurveChart.tsx`):**
  - Circular aperture flux integration with local background annulus subtraction.
  - Time-series flux plotting in calibrated MJy/sr with a heuristic variation flag, not a confirmation of variability or stability.
  - Target-object variability has not been independently verified in this session.
- **External Celestial Catalog Overlay (`/api/science/catalogs`):**
  - Gaia DR3 & SIMBAD reference star queries overlaying diamond markers, G-magnitudes, and proper-motion vectors onto the HTML5 Canvas viewer.
- **Shareable URL Deep Linking:**
  - Bidirectional URL parameter syncing (`/?ra=...&dec=...&fov=...&target=...&stretch=...&colormap=...`).
  - "Share URL" button with instant clipboard feedback.
- **Exportable Scientific Discovery Reports (`/api/science/report`, `DiscoveryReportModal.tsx`):**
  - Formatted J2000 sexagesimal target reports with astrometric vectors, light curve stats, and verified IRSA DOI 10.26131/IRSA678 citations.
- **Guided Educational Tour Modal (`GuidedTourModal.tsx`):**
  - 4-step interactive walkthrough explaining SPHEREx LVF optics, dipole vs monopole signatures, official targets, and judging criteria alignment.
- **Historical automated verification:** 93 passing pytest tests (with 2 Astropy FITSFixedWarnings) covering unit, science, 3D WCS reprojection, rotated WCS alignment, WebP, robust background co-addition/stacking, 102-channel SED, offline resilience, and scientific regression flows.

---

## 2. Architecture Summary
- **Backend:** FastAPI (Python 3.11) with Astropy, Reproject, NumPy, SciPy, Pillow, Astroquery, PyVO.
- **Endpoints:** `/api/health`, `/api/observations`, `/api/frames/{id}`, `/api/frames/diff`, `/api/frames/stack`, `/api/demo`, `/api/demo/manifest`, `/api/science/catalogs`, `/api/science/photometry`, `/api/science/spectrum`, `/api/science/motion`, `/api/science/report`.
- **Frontend:** Vite + React 18 + TypeScript + Tailwind CSS + Lucide Icons + Canvas + SVG.
- **Viewers:**
  - Canvas Viewer (sub-pixel photometric & astrometric inspection).
  - Aladin Lite v3 (HiPS full-sky context).
  - Comparison View (calibrated difference and two-exposure co-add).
- **Data:** Direct NASA IRSA SIA2/IBE protocols with disk-backed cache in `data/cache/` and manifest in `data/manifests/`.

---

After dependency installation and the one-time IRSA bootstrap, the Windows demo launcher verifies the local FITS stage, pins observation search to that cache, and manages both server processes. See [launch and stop commands](README.md#preview-a-refreshed-demo-cache).

## 3. Historical Build & Test Snapshot

See [TEST_RESULTS.md](TEST_RESULTS.md) for the latest suite and browser verification.
- **Backend pytest:** 93 passed, 2 Astropy FITSFixedWarnings in 10.11s (0 failures).
- **Frontend build:** `npm run build` succeeded in 2.55s (1,497 modules transformed, 0 type errors, 0 warnings).
- **Accessibility & Responsive:** 41 checks passed in `node scripts/verify_accessibility_and_responsive.mjs` (0 failures).
- **Demonstration dataset:** 22/22 assets verified valid in `python scripts/verify_demo.py`.
- **Environment & Network:** `python scripts/verify_environment.py` passed outside restricted network: NASA/IPAC IRSA SIA reachable with HTTP 200.
- **Manual Verification Status at this milestone:** Physical screen-reader audio checks were not performed.
