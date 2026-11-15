# SPHEREx Discovery — Time-Domain Astronomical Observatory

[![NASA Space Apps Challenge 2026](https://img.shields.io/badge/NASA%20Space%20Apps-2026-blue.svg)](https://www.spaceappschallenge.org/2026/)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11+-cyan.svg)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/React-18-indigo.svg)](https://react.dev/)
[Test results](TEST_RESULTS.md)

**SPHEREx Discovery** is a experimental astronomical exploration tool built for the **NASA Space Apps Challenge 2026** ("Planet X and SPHEREx").

The application enables citizen scientists, educators, and professional astronomers to explore multi-epoch infrared sky images collected by NASA's **SPHEREx** mission across its 6 detector arrays (0.75 – 5.0 µm), visually detect moving celestial bodies (such as brown dwarfs and high-proper-motion stars), analyze variable stars, and conduct sub-pixel image differencing.

> [!NOTE]
> **Spectrophotometry Truthfulness & Scope:**
> On-the-fly SED analysis measures aperture photometry across up to six detector-band points (D1–D6) with approximate WCS-WAVE wavelengths and propagated `VARIANCE` uncertainties where available; otherwise wavelength or uncertainty estimates are labeled, accompanied by an illustrative/interpolated 102-point continuum. This is **not 102 observed resolved SPHEREx channels**. The API reports `continuum_shape` as a neutral broadband descriptor (e.g. "flux rises toward longer measured bands"); `spectral_class` was removed from the API to avoid false impressions of spectral typing. Any fitted temperature is strictly an optional constrained single-temperature blackbody continuum fit (requiring $\ge 3$ distinct measured bands with valid propagated uncertainties, $\text{dof} \ge 1$), not an object's known physical temperature.

---

## Key Features

1. **Direct NASA/IPAC IRSA Integration:**
   - Spatial and temporal querying against **DR1** (Surveys 1 & 2) and **QR3** (Surveys 3 & 4) via the IRSA SIA2 protocol.
   - Dynamic sub-array slicing using the NASA IRSA IBE Cutout protocol, reducing bandwidth by 18x (~4 MB cutouts vs 70 MB full frames).

2. **Interactive Multi-Epoch Blink Comparator:**
   - Recreating Clyde Tombaugh's classic discovery workflow with high-frequency alternate epoch toggling.
   - Chronological video-like time-lapse playback with variable frame rates (1x, 2x, 4x) and looping.

3. **Difference and co-addition (temporarily unavailable):**
   - The endpoints are guarded until per-pixel wavelength compatibility can be validated with separate spectral WCS products. Use blink playback for visual comparisons.
   - Historical implementation:
   - Sub-pixel celestial differencing to isolate astrometric and photometric transients.
   - Telemetry measuring RMS difference flux, peak positive arrival flux, and peak negative departure flux in calibrated units ($\text{MJy/sr}$).

4. **Rigorous Scientific Calibration:**
   - Multi-extension FITS parsing: `IMAGE` (calibrated surface brightness), `FLAGS` (per-pixel data quality bitmasks), `VARIANCE`, `ZODI` (zodiacal model), and celestial `WCS`.
   - Display-only contrast stretching (`asinh`, `zscale`, `linear`) preserving underlying scientific floating-point data arrays.

5. **Challenge target presets:**
   - Cached cutouts cover the five named targets, but target detection, motion and variability have not been independently validated in this session.
   - **Barnard's Star:** Highest proper motion star (10.3″/yr).
   - **RW Aurigae:** Classical T Tauri star with circumstellar dust obscuration.
   - **WISE 0855:** Coldest known brown dwarf (astrophysical literature $T_{\text{eff}} \approx 250\text{ K}$); the app does not infer spectral type from broadband shape.
   - **Epsilon Indi B:** Binary brown dwarf system with 4.7″/yr proper motion.
   - **R Draconis:** Mira-type pulsating red giant with large infrared amplitude swings.

---

## Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Git

### 1. Verify Environment & IRSA Connectivity
```bash
python scripts/verify_environment.py
```

### 2. Run Backend & Tests
```bash
cd backend
python -m pytest -v
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation available at: `http://localhost:8000/docs`

### 3. Run Frontend
```bash
cd frontend
npm install
npm run build
npm run dev
```
Open browser to `http://localhost:5173`

---

## Multi-Agent Architecture
This project is engineered to persist across AI model transitions. The authoritative instructions and project state are tracked in:
- `AGENTS.md`: Mandatory instructions for AI agents.
- `PROJECT_STATE.md`: Real-time implementation status & metrics.
- `TODO.md`: Prioritized backlog (P0–P3).
- `RESEARCH.md`: Verified astronomical and API findings.
- `TEST_RESULTS.md`: Detailed test run records.
- `DECISIONS.md`: Architecture Decision Records (ADRs).
- `HANDOFF.md`: Immediate transition document for incoming agents.

---

## Data Provenance & Attribution
- NASA/IPAC Infrared Science Archive (IRSA), Jet Propulsion Laboratory, California Institute of Technology.
- SPHEREx DR1 Spectral Images DOI: `10.26131/IRSA678`
- SPHEREx DR1 All-Sky Cube DOI: `10.26131/IRSA679`
- NASA Space Apps Challenge 2026: "Planet X and SPHEREx"
