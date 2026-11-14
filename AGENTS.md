# AGENTS.md — SPHEREx Discovery Agent Instructions

## Mission & Scientific Objective
SPHEREx Discovery is a production-grade scientific web application built for the **NASA Space Apps Challenge 2026** ("Planet X and SPHEREx").
The objective is to display calibrated infrared images of the sky obtained by NASA's SPHEREx mission (0.75–5.0 µm, 102 spectral channels) across time, enabling users, students, and professional astronomers to visually inspect, animate, and discover moving or variable astronomical objects.

**Competition Dates:** November 14–15, 2026  
**Primary Goal:** Local event first place and global nomination through rigorous scientific validity, working real NASA data integration, and outstanding user experience.

---

## Permanent Multi-Agent Rules of Engagement
This project transitions between coding agents (Google Antigravity, OpenAI GPT, and other models). This repository is the **single source of truth and persistent memory**.

### Mandatory Rules for Every Agent:
1. **Context & Continuation Rule:**
   > "Before making any changes, read AGENTS.md, PROJECT_STATE.md, TODO.md, RESEARCH.md, TEST_RESULTS.md, DECISIONS.md, and HANDOFF.md. Inspect Git status and recent commits. Continue from the existing repository rather than generating a replacement project."

2. **Session Completion & Handoff Rule:**
   > "After completing meaningful work, update state documentation and tests. Before the session ends, create a complete handoff for the next agent."

3. **Never build purely mock or decorative astronomical tools.** Every observation displayed must be backed by real NASA/IPAC IRSA Level 2 data products or explicitly labeled verified fixtures.

4. **Never delete working functionality** or replace an existing codebase with a fresh scaffold unless explicitly instructed by the user.

5. **Scientific accuracy requirements:**
   - Visual display contrast stretching (asinh / ZScale / percentile) must NOT alter underlying raw scientific pixel measurements (MJy/sr).
   - SPHEREx uses Linear Variable Filters (LVF); effective wavelength varies spatially across the focal plane. Never perform naive image subtraction across incompatible wavelengths or non-registered celestial grids.
   - Never claim to have discovered "Planet X" or an anomaly unless rigorously measured.

6. **Git Hygiene:** Every major implementation milestone should produce a clean, descriptive Git commit. Track empty directories with `.gitkeep` when necessary.

---

## Repository Architecture & Structure
```text
spherex-discovery-2026/
├── AGENTS.md              # Authoritative instructions for all AI agents
├── README.md              # Project overview, architecture, quickstart
├── PROJECT_STATE.md       # Exact current implementation status & metrics
├── TODO.md                # Prioritized backlog (P0-P3)
├── RESEARCH.md            # Verified scientific & API research summary
├── TEST_RESULTS.md        # Real verification test runs and outcomes
├── DECISIONS.md           # Architecture Decision Records (ADR)
├── HANDOFF.md             # Immediate handoff for incoming agents
├── CHANGELOG.md           # Log of notable changes
├── .gitignore
├── .env.example
├── backend/               # FastAPI Python backend
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/          # /health, /observations, /frames, /demo
│   │   ├── services/     # irsa_client, cutout_service, cache_service
│   │   ├── science/      # fits_processing, coordinates, image_registration, comparison
│   │   └── models/       # schemas.py
│   └── tests/            # pytest suite
├── frontend/              # React 18+ / TypeScript / Vite / Tailwind
│   ├── src/
│   │   ├── components/   # layout, viewer, controls, timeline, metadata
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   └── utils/
├── scripts/               # probe_irsa.py, verify_environment.py, build_demo_dataset.py
├── data/                  # manifests, cache, test fixtures
└── docs/                  # In-depth technical & judging documentation
```

---

## Approved Technology Stack & Coding Conventions
- **Backend:** Python 3.11+, FastAPI, Uvicorn, Astropy 8+, NumPy 2+, SciPy, Pillow, HTTPX, Certifi. Type hints on all functions (`pydantic.BaseModel`).
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Lucide icons, HTML5 Canvas for high-performance astronomical rendering.
- **Data Integration:** NASA/IPAC IRSA SIA2 (Simple Image Access v2) for spatial/temporal querying, IRSA IBE Cutout Service for on-demand sub-image FITS extraction.
- **Linting & Testing:** pytest for backend, npm run build / TypeScript compiler for frontend.

---

## How to Install, Run & Verify
```bash
# 1. Environment verification
python scripts/verify_environment.py

# 2. Run backend tests
cd backend
python -m pytest -v

# 3. Start backend server (port 8000)
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 4. Start frontend server (port 5173)
cd frontend
npm install
npm run build
npm run dev
```
