# NASA Space Apps Challenge 2026 — Submission Checklist

## 1. Project Overview & Metadata
- **Project Title:** SPHEREx Discovery — Time-Domain Astronomical Discovery Engine
- **Challenge Name:** Track the Sky: Time-Domain Astronomy with SPHEREx (Prompt 1)
- **Tagline:** Exploring the dynamic infrared cosmos through interactive time-domain differencing, proper motion tracking, and multi-epoch photometry.
- **Repository URL:** Public GitHub Repository (`main` branch)
- **Deployment URL:** Live web demo (Render backend + Vercel frontend)

---

## 2. Space Apps Submission Fields

### Short Description (Under 100 words)
> SPHEREx Discovery is an interactive astronomical exploration platform built for NASA's SPHEREx mission. By combining live NASA/IPAC IRSA SIA2 integration with calibrated Level 2 FITS processing, the platform empowers users to discover moving solar system bodies, brown dwarfs, and variable stars across 102 infrared bands (0.75–5.0 µm). Key features include sub-pixel 2D Fourier phase registration, calibrated temporal differencing ($I_2 - I_1$), automated astrometric proper motion vectors, multi-epoch circular aperture photometry light curves, Gaia DR3 catalog overlays, and publication-grade discovery report export with verified IRSA DOIs (10.26131/IRSA678).

### Detailed Solution Description
- **The Problem:** SPHEREx's Linear Variable Filters (LVFs) introduce complex optical geometries where bandpass shifts continuously across detector arrays. Traditional astronomical pipelines are inaccessible to citizen scientists, making time-domain temporal differencing across DR1 and QR3 difficult without specialized tools.
- **Our Solution:** A modern, cloud-native web application with hardware-accelerated 60 FPS HTML5 Canvas rendering, smart adjacent frame prefetching, rigid LVF detector-matching guards, and automated dipole/monopole candidate classification.
- **NASA Assets & Data Used:**
  - NASA/IPAC Infrared Science Archive (IRSA) Simple Image Access Protocol Version 2.0 (SIA2)
  - SPHEREx Data Release 1 (`spherex_dr1`) and Quick Release 3 (`spherex_qr3`) Level 2 Calibrated Images (DOI: 10.26131/IRSA678)
  - Astropy astronomical software library (WCS, FITS I/O, Coordinates, Time)

---

## 3. Technical Verification & Artifacts
- [x] **Backend Automated Tests:** 43 automated tests passing in under 5 seconds (`pytest -v`).
- [x] **Frontend Production Build:** Clean TypeScript & Vite build with 0 warnings/errors (`npm run build`).
- [x] **Verified Challenge Targets:** All 5 official competition targets verified with real FITS cutouts cached in `data/cache/`.
- [x] **Containerization:** Production Dockerfiles (`backend/Dockerfile`, `frontend/Dockerfile`) and `docker-compose.yml` verified.
- [x] **Cloud Configurations:** `render.yaml` for backend and `frontend/vercel.json` for frontend SPA routing.
- [x] **Open Source License:** MIT License included in repository.
- [x] **Documentation Suite:** Complete documentation in `docs/` covering requirements, architecture, scientific method, data provenance, APIs, UI design, targets, judging strategy, and demo script.
