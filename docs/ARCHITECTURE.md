# SPHEREx Discovery — System Architecture & Data Flow

```text
+--------------------------------------------------------------------------------------------------+
|                                    CLIENT (React 18 + TypeScript + Vite)                         |
|                                                                                                  |
|  +-----------------------+  +------------------------------------+  +-------------------------+  |
|  |     SearchControls    |  |            CanvasViewer            |  |      MetadataPanel      |  |
|  | - RA / Dec (deg / sex)|  | - HTML5 Canvas 60 FPS pan/zoom     |  | - UTC Obs Time & Obs ID |  |
|  | - FOV radius selector |  | - Nearest-neighbor pixel rendering |  | - Calibrated MJy/sr     |  |
|  | - 5 Official Presets  |  | - Gaia DR3 Vector Overlay (Stars)  |  | - Bitmask Quality Flags |  |
|  | - DR1 / QR3 selection |  | - Crosshair & Astrometry HUD       |  | - LightCurveChart (SVG) |  |
|  | - Wavelength filter   |  | - Asinh / ZScale / Linear Stretches|  | - "Export Report" Action|  |
|  +-----------------------+  +------------------------------------+  +-------------------------+  |
|                                                  ^                                               |
|                                                  |                                               |
|  +-----------------------------------------------+--------------------------------------------+  |
|  |                    TimelinePlayer, Blink Comparator & ComparisonView                      |  |
|  | - Chronological Epoch Slider   - Frame In-Memory Cache & Adjacent Prefetcher                  |  |
|  | - Variable Playback (1-10 FPS) - 3-Card Differencing (Epoch 1, Epoch 2, Difference I2 - I1)  |  |
|  | - Automated Dipole Vector      - Astrometric Proper Motion & Position Angle Telemetry         |  |
|  +--------------------------------------------------------------------------------------------+  |
|                                                  |                                               |
|  +-----------------------------------------------+--------------------------------------------+  |
|  |                             Modals & Collaborative Tools                                   |  |
|  | - GuidedTourModal (Educational Tour)          - DiscoveryReportModal (Download MD / JSON)     |  |
|  | - URL Deep Linking Engine (Shareable State)   - Clipboard Synchronization                     |  |
|  +--------------------------------------------------------------------------------------------+  |
+--------------------------------------------------------------------------------------------------+
                                                   |
                                                   | HTTP REST API (/api/...)
                                                   v
+--------------------------------------------------------------------------------------------------+
|                                  BACKEND (FastAPI / Python 3.11)                                 |
|                                                                                                  |
|  +------------------+  +---------------------+  +---------------------+  +--------------------+  |
|  |   /api/health    |  |  /api/observations  |  | /api/frames/{id}    |  | /api/frames/diff   |  |
|  | Health & IRSA SIA|  | IRSA query with     |  | Calibrated cutout   |  | Calibrated diff    |  |
|  | connectivity probe| fallback registry     |  | & Astropy celestial |  | with NaN mid-gray   |  |
|  +------------------+  +---------------------+  +---------------------+  +--------------------+  |
|                                                  |                                               |
|  +------------------+  +---------------------+  +---------------------+  +--------------------+  |
|  | /science/catalogs|  | /science/photometry |  | /science/motion     |  | /science/report    |  |
|  | Gaia DR3 / SIMBAD|  | Circular aperture   |  | Sub-pixel centroid &|  | Formal Space Apps  |  |
|  | reference stars  |  | flux time series    |  | 2D FFT proper motion|  | Discovery Reports  |  |
|  +------------------+  +---------------------+  +---------------------+  +--------------------+  |
|                                                  |                                               |
|  +---------------------+-------------------------+----------------------+---------------------+  |
|  v                     v                         v                      v                     v  |
| +----------------+   +-------------------+   +--------------------+   +-------------------+      |
| | irsa_client.py |   | cutout_service.py |   | fits_processing.py |   | demo_service.py   |      |
| | IRSA SIA2 HTTP |   | IBE Cutouts with  |   | Astropy celestial  |   | 22 cached real    |      |
| | client & cache |   | disk cache        |   | WCS, quality masks |   | FITS for offline  |      |
| +----------------+   +-------------------+   +--------------------+   +-------------------+      |
+--------------------------------------------------------------------------------------------------+
                                                   |
                                                   | HTTPS (ADQL / CSV / FITS Cutouts)
                                                   v
+--------------------------------------------------------------------------------------------------+
|                                    EXTERNAL ARCHIVES & SERVICES                                  |
|  - NASA/IPAC IRSA SIA2 Endpoint: /SIA?COLLECTION=spherex_dr1...                                  |
|  - NASA/IPAC IRSA IBE Cutout Service: /ibe/data/spherex/...fits?center=...&size=...              |
|  - ESA Gaia Archive TAP Service: gaiadr3.gaia_source queries                                     |
|  - Verified Archival DOI: 10.26131/IRSA678                                                       |
+--------------------------------------------------------------------------------------------------+
```

---

## Component Details

### 1. Backend Architecture
- **Framework:** FastAPI with asynchronous ASGI endpoints running on Uvicorn.
- **Astronomy Stack:** Astropy (`astropy.io.fits`, `astropy.wcs`, `astropy.coordinates`, `astropy.time`), NumPy, SciPy, Pillow.
- **Resilience Engine:** Dual-mode architecture. When NASA IRSA is available, live SIA2 queries and cutouts are retrieved; if IRSA experiences network latency or 502/503 errors, the backend seamlessly falls back to 22 verified demonstration FITS cutouts covering all 5 challenge targets.
- **Scientific Image Processing:**
  - Celestial coordinates parsed into ICRS celestial frame with $0^\circ / 360^\circ$ meridian wrapping.
  - Multi-extension FITS reading extracting calibrated science image (ext 0), variance (ext 1), and quality flags (ext 2).
  - Physical surface brightness retained strictly in calibrated units of $\text{MJy/sr}$.
  - Preview displays use `asinh` and `zscale` stretches with linear mapping to 8-bit visual buffers.
  - Sub-pixel image registration via 2D Fourier phase cross-correlation.
  - Calibrated differencing with finite floating-point masking and mid-gray mapping (value 128 = 0.0 residual change).

### 2. Frontend Architecture
- **Framework:** React 18, TypeScript, Tailwind CSS, Lucide icons, Vite.
- **Canvas Engine:** HTML5 Canvas with nearest-neighbor image interpolation (`imageSmoothingEnabled = false`), pan, zoom, celestial crosshair, and vector overlays.
- **Timeline Engine:** Multi-epoch chronological slider with play/pause, variable FPS, and adjacent frame prefetching.
- **Difference Engine:** 3-card synchronized comparison showing Epoch 1, Epoch 2, and Difference ($I_2 - I_1$) alongside baseline $\Delta t$ and proper motion vector metrics.
- **Telemetry Dock:** Real-time aperture photometry light curve chart, quality flag breakdown, WCS parameters, and one-click Discovery Report generator.
- **State Synchronization:** Bidirectional URL deep-linking syncing coordinates, presets, FOV, and stretch modes.
