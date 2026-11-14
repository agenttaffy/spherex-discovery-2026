# SPHEREx Discovery — Time-Domain Astronomical Observatory

[![NASA Space Apps Challenge 2026](https://img.shields.io/badge/NASA%20Space%20Apps-2026-blue.svg)](https://www.spaceappschallenge.org/2026/)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11+-cyan.svg)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/React-18-indigo.svg)](https://react.dev/)
[![Tests: 23 Passed](https://img.shields.io/badge/Tests-23%20Passed-emerald.svg)](TEST_RESULTS.md)

**SPHEREx Discovery** is a publication-grade astronomical web observatory built for the **NASA Space Apps Challenge 2026** ("Planet X and SPHEREx").

The application enables citizen scientists, educators, and professional astronomers to explore multi-epoch infrared sky images collected by NASA's **SPHEREx** mission across 102 spectral channels (0.75 – 5.0 µm), visually detect moving celestial bodies (such as brown dwarfs and high-proper-motion stars), analyze variable stars, and conduct sub-pixel image differencing.

---

## Key Features

1. **Direct NASA/IPAC IRSA Integration:**
   - Spatial and temporal querying against **DR1** (Surveys 1 & 2) and **QR3** (Surveys 3 & 4) via the IRSA SIA2 protocol.
   - Dynamic sub-array slicing using the NASA IRSA IBE Cutout protocol, reducing bandwidth by 18x (~4 MB cutouts vs 70 MB full frames).

2. **Interactive Multi-Epoch Blink Comparator:**
   - Recreating Clyde Tombaugh's classic discovery workflow with high-frequency alternate epoch toggling.
   - Chronological video-like time-lapse playback with variable frame rates (1x, 2x, 4x) and looping.

3. **Differential Image Engine ($I_2 - I_1$):**
   - Sub-pixel celestial differencing to isolate astrometric and photometric transients.
   - Telemetry measuring RMS difference flux, peak positive arrival flux, and peak negative departure flux in calibrated units ($\text{MJy/sr}$).

4. **Rigorous Scientific Calibration:**
   - Multi-extension FITS parsing: `IMAGE` (calibrated surface brightness), `FLAGS` (per-pixel data quality bitmasks), `VARIANCE`, `ZODI` (zodiacal model), and celestial `WCS`.
   - Display-only contrast stretching (`asinh`, `zscale`, `linear`) preserving underlying scientific floating-point data arrays.

5. **Tested on All 5 Official Competition Targets:**
   - **Barnard's Star:** Highest proper motion star (10.3″/yr) with a 1.0-year baseline between DR1 and QR3 showing a 1.66-pixel astrometric shift.
   - **RW Aurigae:** Classical T Tauri star with circumstellar dust obscuration showing ~200 MJy/sr infrared flux reduction.
   - **WISE 0855:** Coldest known brown dwarf (~250 K) visible in mid-IR channels D4–D6.
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
