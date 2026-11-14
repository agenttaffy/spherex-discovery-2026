# SPHEREx Discovery — Project State

**Last Updated:** 2026-11-14T18:15:00Z  
**Current Implementation Stage:** Phase 5 Fully Hardened & Verified (On-The-Fly Spectra Generation SED: Flux vs. Wavelength $\lambda$ across 6 Detector Arrays & 102 Channels with PCHIP Monotonic Interpolation, Astronomical Image Co-Addition & Stacking with Robust Sigma-Clipped Background Noise and $\sim\sqrt{N}$ SNR Improvement, Multi-Epoch Stacking Scope Switcher in ComparisonView, 69 Passing Pytest Tests, Clean Production Build).

---

## 1. Verified Working Features
- **On-The-Fly Spectra Generation (`/api/science/spectrum`, `spectrum.py`, `SpectrumChart.tsx`):**
  - Instantaneous calibrated Spectral Energy Distribution (SED: Flux vs. Wavelength $\lambda$) from 0.75 µm to 5.00 µm.
  - Queries and aggregates multi-epoch circular aperture photometry across all 6 SPHEREx detector arrays (D1: 0.75–1.12 µm, D2: 1.12–1.68 µm, D3: 1.68–2.42 µm, D4: 2.42–3.82 µm, D5: 3.82–4.42 µm, D6: 4.42–5.00 µm).
  - Synthesizes all 102 individual spectroscopic channels (17 channels per detector array) with color-coded band visualization.
  - Interactive SVG plotting with detector band boundary shading, photometric error bars, and smooth continuum curves.
  - Physical spectral classification engine detecting Cold Sub-stellar Brown Dwarfs (peaking in D5/D6, e.g. WISE 0855), Cool Stellar Atmospheres (M-Dwarfs, e.g. Barnard's Star), and Infrared Excesses (circumstellar dust disks, e.g. RW Aurigae).
  - Telemetry dock tab switcher in `MetadataPanel.tsx` toggling between "Infrared SED (102 Bands)" and "Light Curve".
- **Astronomical Image Co-Addition & Stacking (`/api/frames/stack`, `stacking.py`, `ComparisonView.tsx`):**
  - Multi-frame image stacking across observation epochs or detector arrays on a shared celestial grid.
  - Supports `mean` (maximum SNR), `median` (outlier & cosmic ray rejection), and `sum` (total flux integration) stacking methods.
  - Aligns frames using `reproject_interp` celestial WCS reprojection with sub-pixel 2D FFT shift fallback.
  - Automatically calculates single-frame vs stacked background noise ($\sigma_{ref}$, $\sigma_{stack}$), empirical SNR improvement factor, and theoretical $\sim\sqrt{N}$ SNR gain badge (+41.4% for 2 frames).
  - Operation mode switcher in `ComparisonView.tsx`: "Difference ($I_2 - I_1$)" (reveals moving sources, dipoles, and transients) vs "Co-Add Stack ($I_1 + I_2$)" (reveals faint static infrared sources, brown dwarfs, and deep background galaxies).
- **Aladin Lite v3 Sky Context Integration (`AladinViewer.tsx` & `CanvasViewer.tsx`):**
  - Seamless pill tab toggle between "SPHEREx Analysis Canvas" and "Aladin Lite Sky Context".
  - Embedded Aladin Lite v3 (HiPS WebGL) with dynamic CDN loading and official CDS API compatibility.
  - Automatic synchronization of pointing coordinates (RA, Dec) and FOV.
  - Dynamic overlay polygon footprint representing the exact SPHEREx observation coverage bounding box.
  - Multi-survey switcher: 2MASS Color (Near-IR JHK: 1.25–2.17 µm), AllWISE Color (Mid-IR W1-W4: 3.4–22 µm), DSS2 Color (Optical), Pan-STARRS DR1.
  - High-fidelity offline SVG celestial radar fallback if external CDNs or WebGL are unavailable.
- **Scientific WCS Reprojection (`reproject_interp`, `backend/app/science/comparison.py`):**
  - Automatic celestial grid reprojection between differing observation epochs using `reproject.reproject_interp`.
  - Aligns epochs with differing pixel scales, geometries, and orientations prior to difference image computation.
  - Graceful fallback to 2D Fourier phase cross-correlation (FFT shift) if celestial WCS is absent.
  - Differential alignment telemetry reporting (`wcs_reproject`, `fft_shift`, `direct`).
- **WebP Image Output Engine (`backend/app/science/fits_processing.py`):**
  - Added `render_image_to_base64` supporting `format: Literal["png", "webp"] = "png"`.
  - Smaller payload footprints for rapid multi-epoch timeline scrubbing and Blink comparator playback.
  - Query parameter support (`/api/frames/{id}?format=webp`) and diff body formatting (`format: "webp"`).
- **NASA/IPAC IRSA SIA2 Client & Resilient Offline Demo Architecture:**
  - Live programmatic queries against `spherex_dr1` and `spherex_qr3` collections.
  - 22 verified demonstration cutouts cached locally in `data/cache/` covering all 5 official competition targets across DR1 and QR3.
  - Automatic circuit breaker fallback on remote archive latency or HTTP 502/503.
- **Display-Only Contrast Scaling:** `asinh` (arcsinh), `zscale`, and `linear` stretching engines with grayscale and `inferno` colormaps.
- **Differential Image Engine:**
  - Robust against non-finite values (NaN/Inf) with finite stats calculation and mid-gray (128) baseline for missing pixels.
  - Spherical RA boundary wrapping across 0°/360° celestial seam.
  - Duplicate epoch self-comparison prevention.
- **Astrometric Proper Motion Vector Engine (`/api/science/motion`):**
  - Sub-pixel 2D FFT phase cross-correlation + local $5 \times 5$ centroid tracker.
  - Computes angular displacement ($\Delta\theta$ in arcseconds), annual proper motion ($\mu$ in arcsec/year and mas/year), position angle ($\theta_{PA}$), and candidate classification ("High Proper Motion Candidate").
  - Verified on Barnard's Star (10.3 arcsec/yr displacement between DR1 and QR3).
- **Multi-Epoch Photometric Light Curve Dock (`/api/science/photometry`, `LightCurveChart.tsx`):**
  - Circular aperture flux integration with local background annulus subtraction.
  - Time-series flux plotting in calibrated MJy/sr with automated variability classification ("CONFIRMED VARIABLE" vs "STABLE").
  - Verified on variable stars RW Aurigae and R Draconis.
- **External Celestial Catalog Overlay (`/api/science/catalogs`):**
  - Gaia DR3 & SIMBAD reference star queries overlaying diamond markers, G-magnitudes, and proper-motion vectors onto the HTML5 Canvas viewer.
- **Shareable URL Deep Linking:**
  - Bidirectional URL parameter syncing (`/?ra=...&dec=...&fov=...&target=...&stretch=...&colormap=...`).
  - "Share URL" button with instant clipboard feedback.
- **Exportable Scientific Discovery Reports (`/api/science/report`, `DiscoveryReportModal.tsx`):**
  - Formatted J2000 sexagesimal target reports with astrometric vectors, light curve stats, and verified IRSA DOI 10.26131/IRSA678 citations.
- **Guided Educational Tour Modal (`GuidedTourModal.tsx`):**
  - 4-step interactive walkthrough explaining SPHEREx LVF optics, dipole vs monopole signatures, official targets, and judging criteria alignment.
- **Comprehensive Automated Test Suite:** 69 passing pytest tests covering unit, science, 3D WCS reprojection, rotated WCS alignment, WebP, robust background co-addition/stacking, 102-channel SED, offline resilience, and integration flows.

---

## 2. Architecture Summary
- **Backend:** FastAPI (Python 3.11) with Astropy, Reproject, NumPy, SciPy, Pillow, Astroquery, PyVO.
- **Endpoints:** `/api/health`, `/api/observations`, `/api/frames/{id}`, `/api/frames/diff`, `/api/frames/stack`, `/api/demo`, `/api/demo/manifest`, `/api/science/catalogs`, `/api/science/photometry`, `/api/science/spectrum`, `/api/science/motion`, `/api/science/report`.
- **Frontend:** Vite + React 18 + TypeScript + Tailwind CSS + Lucide Icons + Canvas + SVG.
- **Viewers:**
  - Canvas Viewer (sub-pixel photometric & astrometric inspection).
  - Aladin Lite v3 (HiPS full-sky context).
  - Comparison View (Difference $I_2 - I_1$ vs Co-Add Stack $I_1 + I_2$ with Selected Pair and All Epochs scopes).
- **Data:** Direct NASA IRSA SIA2/IBE protocols with disk-backed cache in `data/cache/` and manifest in `data/manifests/`.

---

## 3. Latest Build & Test Status
- **Backend pytest:** 69 passed in 4.93s (0 failures).
- **Frontend build:** `npm run build` succeeded in 2.21s (0 type errors, 0 warnings).
