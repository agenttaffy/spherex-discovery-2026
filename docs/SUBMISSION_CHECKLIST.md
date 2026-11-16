# NASA Space Apps Challenge 2026 — Submission Checklist

## 1. Project Overview & Metadata
- **Project Title:** SPHEREx Discovery — Time-Domain Astronomical Discovery Engine
- **Challenge Name:** Planet X and SPHEREx
- **Tagline:** Blink dated infrared images, check which pixels can be compared, and inspect DR1 sky-pixel brightness by wavelength.
- **Repository URL:** [Configured GitHub repository](https://github.com/agenttaffy/spherex-discovery-2026), `main` branch. An unauthenticated request loaded the repository page on 2026-11-15. The current demonstration build is in the local working tree.
- **Deployment URL:** Public deployment unverified. Both configured Render names returned HTTP 404 with `x-render-routing: no-server` on 2026-11-15. Use the [local judge walkthrough](DEMO_SCRIPT.md) for the verified build.

---

## 2. Space Apps Submission Fields

### Short Description (Under 100 words)
> SPHEREx Discovery lets users browse NASA/IPAC observations by position, inspect dated infrared images, and blink between exposures. It checks the calibrated passband at each aligned pixel before showing a difference or pair co-add. A separate DR1 cube view shows co-added sky-pixel brightness, channel coverage and flags. Catalog predictions, data provenance, and quality information help users decide what can support further investigation.

### Detailed Solution Description
- **The Problem:** SPHEREx's Linear Variable Filters (LVFs) introduce complex optical geometries where bandpass shifts continuously across detector arrays. Traditional astronomical pipelines are inaccessible to citizen scientists, making time-domain temporal differencing across DR1 and QR3 difficult without specialized tools.
- **Our Solution:** A browser workspace with native-pixel rendering, time and wavelength views, and per-pixel validation for calibrated pairs.
- **NASA Assets & Data Used:**
  - NASA/IPAC Infrared Science Archive (IRSA) Simple Image Access Protocol Version 2.0 (SIA2)
  - SPHEREx DR1 and QR3 Level 2 calibrated images. DR1 Spectral Images DOI: 10.26131/IRSA678.
  - SPHEREx DR1 All-Sky Cube (DOI: 10.26131/IRSA679). The local preview covers five audited sky pixels and a native window per channel.
  - Astropy astronomical software library (WCS, FITS I/O, Coordinates, Time)

---

## 3. Technical Verification & Artifacts
- [x] **Backend Automated Tests:** See the current test counts and warnings in [TEST_RESULTS.md](../TEST_RESULTS.md).
- [x] **Frontend Production Build:** TypeScript and Vite build passed with a size warning for the lazy Aladin chunk.
- [x] **Challenge field coverage:** The optional preview passes the audit with ten FITS cutouts, two covered epochs per preset. Source identity, target flux, motion and variability remain unconfirmed.
- [x] **Calibrated comparison and cube:** DR1 D5 difference and co-add retained 207/225 pixels near the predicted Epsilon Indi position. The D6 deep-field arithmetic control retained 378/400. The 2,708,179-byte cube cache preserves all 102 channel slots and native windows per preset. [Verification](../TEST_RESULTS.md)
- [ ] **Containerization:** Dockerfiles and Compose configuration are available. A fresh deployed-container check is pending.
- [x] **Cloud Configurations:** `render.yaml` for backend and `frontend/vercel.json` for frontend SPA routing.
- [ ] **Owner decision before publication:** Choose the project’s software license and confirm the terms that apply to redistributing the compact cube. The checkout includes source attribution and the bundled fonts’ separate license files.
- [x] **Documentation:** The [Windows setup](../README.md#preview-a-refreshed-demo-cache), [demo script](DEMO_SCRIPT.md), and [API reference](API_REFERENCE.md) describe the supported workflows and their limits.

## 4. Public release preflight

Read-only GET results on 2026-11-15. These requests did not redirect.

| Host | Paths checked | Response |
|---|---|---|
| `github.com` | `/agenttaffy/spherex-discovery-2026` | 200 HTML |
| `api.github.com` | repo record, `/deployments?per_page=15`, `/pages` | 200 JSON with no homepage, 200 JSON with no public deployment records, 404 JSON for Pages |
| `spherex-discovery-backend.onrender.com` | `/`, `/health`, `/api/health`, `/openapi.json` | 404 plain text, `x-render-routing: no-server` |
| `spherex-discovery-api.onrender.com` | `/`, `/api/health`, `/openapi.json` | 404 plain text, `x-render-routing: no-server` |

The Render edge did not route requests to FastAPI at either hostname. Public responses cannot establish whether a dashboard service is absent, uses another hostname, or has its Render subdomain disabled. Locally, the Blueprint-equivalent command returned HTTP 200 JSON at `/api/health`, while the plain `/health` path returned FastAPI’s JSON 404. Upstream IRSA connectivity failed independently of application health.

The Blueprint uses the current `runtime: python` field. The Vercel rewrite points to the Blueprint-named service. Both files passed local validation against the published schemas. The local production build served the SPA deep link and its assets. The Vite preview proxy returned HTTP 200 JSON for health and preserved HTTP 404 and 503 JSON from the backend.

- [ ] **Confirm the backend in Render first.** Open [Render Dashboard](https://dashboard.render.com/) and find `spherex-discovery-backend`. Copy its assigned public URL and confirm that `/api/health` returns HTTP 200 JSON. If the service is absent, plan **New → Blueprint** for the approved repository and release branch with `render.yaml` at the repo root. The Web Service name is `spherex-discovery-backend`, runtime Python 3.11.4, build command `pip install -r backend/requirements.txt`, and start command `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Render supplies `PORT`. Keep the repo root as the service root and use a blank `CORS_ORIGINS` value for the same-origin Vercel proxy. Make that setup only after release approval. [Render Blueprint setup](https://render.com/docs/infrastructure-as-code)
- [ ] **Confirm the frontend configuration against the assigned URL.** Use Vercel root `frontend`, framework Vite, build `npm run build`, output `dist`. If the assigned Render URL differs from the Blueprint-named destination, update the external rewrite before release. Verify the frontend’s same-origin `/api/health`, a browser deep link, production assets, and observation loading. [Vercel rewrites](https://vercel.com/docs/routing/rewrites)
- [ ] **Decide what data the hosted release needs.** The verified ten-frame preview and D5 arithmetic depend on local, ignored FITS staging. The source checkout omits those FITS. The verified clean Windows run acquired them through the explicit bootstrap, then served the prepared demo with archive access disabled. Hosted offline parity needs a separate decision and verification. Verify the compact cube artifact and its source pins are present in the approved release revision.

Local CORS verification covered the localhost defaults, an explicit single-origin configuration, and an empty production list. Unlisted origins received a denied preflight and wildcard configuration failed startup. The same-origin proxy worked with an empty list. The configuration scan excluded local environment files. Git ignores environment variants, local Vercel state, and local verification outputs.
