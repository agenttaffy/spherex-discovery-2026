# SPHEREx Discovery — Time-Domain Astronomical Observatory

[![NASA Space Apps Challenge 2026](https://img.shields.io/badge/NASA%20Space%20Apps-2026-blue.svg)](https://www.spaceappschallenge.org/2026/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11+-cyan.svg)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/React-18-indigo.svg)](https://react.dev/)
[Test results](TEST_RESULTS.md)

**SPHEREx Discovery** is an experimental astronomical exploration tool built for the **NASA Space Apps Challenge 2026** ("Planet X and SPHEREx").

The app explores dated infrared observations from NASA’s SPHEREx mission. Use the timeline and blink view to inspect changes and the Aladin overlay to see the cutout in sky context. Catalog and photometry results are evidence for investigation. See the [challenge traceability matrix](docs/CHALLENGE_REQUIREMENTS.md) for verification and availability.

> [!NOTE]
> **Spectral measurements and scope:**
> The inspector displays only available detector field aperture sums. These are not calibrated source flux densities; source association, continuum shape and temperature remain unconfirmed. The former synthetic continuum is no longer produced. The separate 102-slot DR1 cube provides co-added sky-pixel surface brightness, with blank and unavailable channels identified; it does not establish a source spectrum or variability.

---

## Cloud access and archive availability

For newly opened spectral images the app first reads bounded ranges from the public NASA/IPAC SPHEREx cloud mirror and creates a native-pixel FITS cutout locally. It checks the object identity and preserves the image, quality, variance and WCS information; if the cloud read fails, it tries IRSA's cutout service. Previously cached cutouts can be reused, and the interface identifies their source. SIA/TAP metadata searches still depend on IRSA; cloud storage alone is not a sky-coordinate search index.

The DR1 spectral cube uses bounded cloud byte ranges instead of downloading a whole 321 MB tile. When SIA cannot identify the current tile, the app can try the explicitly labeled `hips_20261026` DR1 release at the requested coordinate; it checks the FITS WCS, but this dated fallback is not a guarantee of the newest available release. After verifying a new DR1 layout in IRSA documentation, set `SPHEREX_DR1_CUBE_VERSION` to its `hips_YYYYMMDD` directory and restart the backend to update this fallback. Cached previews remain available for five preset positions. Cloud requests can still fail, and an available image does not prove the observation search was complete.

During an archive outage, a small packaged snapshot can show historical search records for the positions it covers. The snapshot was saved locally on November 14, 2026; the original query timestamps were not independently recorded. Its records are not the image files and may be incomplete or outdated. Image retrieval and coverage are checked separately. To refresh it after obtaining a new attributed IRSA search in the same job/request/rows JSON format, run `python scripts/refresh_search_snapshot.py PATH_TO_SEARCH.json --saved-date YYYY-MM-DD` and review the provenance record. The app verifies the packaged snapshot hash before serving it.

An IRSA SIA CSV can also be added when you have its **original request URL**, including the collection and circle coordinates. The CSV must contain `obs_id`, `energy_bandpassname`, `t_min`, and `access_url` columns; not every IRSA interface export necessarily has this format. For example, in PowerShell:

```powershell
python scripts/refresh_search_snapshot.py .\search.csv --saved-date 2026-11-15 --csv-request 'https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=circle+248.16723+66.75502+0.001&RESPONSEFORMAT=CSV' --append
```

Use the actual date, original request, and file for your search. `--append` checks and keeps the existing package, preserves each search's saved date, and records source checksums; omitting it replaces the existing package. Invalid requests or files with no usable rows are rejected before replacement; individual unusable rows are skipped and counted. This imports search metadata, not image pixels, and cannot establish that a search was complete or that its images are still available. The CSV must actually come from the stated request; the tool cannot independently verify that attribution.

## Share or embed a sky position

A URL can include ICRS decimal coordinates in degrees, for example `/?ra=248.1672277&dec=66.7550245`. The Share control also includes the applied search, selected observation, field of view and display settings. Add `embed=1` to skip the introduction and initially collapse the desktop side panels; users can reopen them. Once the app is deployed at a public HTTPS URL, an external site can embed that URL in an iframe, subject to the hosting service's frame policy and network availability. A localhost URL works only on the machine running the preview. The embedded viewer retains the same source and availability notices.

```html
<iframe title="SPHEREx sky viewer" src="https://YOUR-DEPLOYMENT/?embed=1&ra=248.1672277&dec=66.7550245" width="100%" height="800" loading="lazy"></iframe>
```

## Key Features

1. **Direct NASA/IPAC IRSA Integration:**
   - Spatial and temporal querying against **DR1** (Surveys 1 & 2) and **QR3** (Surveys 3 & 4) via the IRSA SIA2 protocol.
   - Cloud-first, bounded native-pixel cutouts with an IRSA IBE fallback; transfer size depends on the field of view and file layout.

2. **Interactive Multi-Epoch Blink Comparator:**
   - Recreating Clyde Tombaugh's classic discovery workflow with high-frequency alternate epoch toggling.
   - Chronological video-like time-lapse playback with variable frame rates (1x, 2x, 4x) and looping.

3. **Calibrated difference and co-addition:**
   - Difference two exposures or co-add two to six independent exposures from one detector. Checksum-verified CWAVE/CBAND maps and celestial WCS retain only usable pixels with a sufficiently shared nominal passband. A real three-exposure R Draconis field co-add was checked against an independent calculation; this is not a target detection. Use blink for pairs without verified overlap.


4. **Rigorous Scientific Calibration:**
   - Multi-extension FITS parsing: `IMAGE` (calibrated surface brightness), `FLAGS` (per-pixel data quality bitmasks), `VARIANCE`, `ZODI` (zodiacal model), and celestial `WCS`.
   - **Spectral Cube** shows co-added DR1 surface brightness at the nearest native sky pixel and a channel map. It has 102 channel slots, including two blank DR1 channels. Coverage depends on position and flags. The verified 2.7 MB fallback covers five preview coordinates. The cube has no variance plane or single target epoch.
   - Display-only contrast stretching (`asinh`, `zscale`, `linear`) preserving underlying scientific floating-point data arrays.

5. **Challenge target presets:**
   - The default 22-file manifest has 18 named-target cutouts and four documentation examples. Of the 18, only the four RW Aurigae cutouts include the named system’s exposure-epoch prediction. The optional ten-file preview covers every preset at two epochs.
   - See the [target validation report](docs/TARGET_VALIDATION.md) for exposure IDs, references, and photometry limits. See the [demo audit](docs/DEMO_DATA_AUDIT.md) for cache integrity and warnings.

### Preview a refreshed demo cache

Public `main` at `4c0e482` predates the portable preview. Use these steps from a checkout that includes the bootstrap script, download pins, compact cube preview, and Windows launcher. See the [judge walkthrough](docs/DEMO_SCRIPT.md) for the presentation sequence.

From the repository root on Windows, install Python 3.11+, Node.js 18+ with npm, and the dependencies. Keep the checkout on a drive that supports hard links, such as NTFS. The first bootstrap needs Internet access to IRSA. It verifies sizes and SHA-256 before installing the exact FITS bytes under the ignored cache and preserves existing files.

```powershell
python -m pip install -r backend/requirements.txt
npm.cmd ci --prefix frontend
python scripts/bootstrap_demo_data.py --with-comparisons
```

The default bootstrap downloads the ten preview cutouts, **39,513,600 bytes**. The `--with-comparisons` option adds **74,528,640 bytes** for the two D5 cutouts and the exact D5 and D6 spectral calibration maps. Use it for the judge walkthrough’s calibrated D5 result and the WISE passband rejection. Allow about 115 MB for the complete FITS cache, plus space for the checkout, dependencies, and setup caches. The verified Windows run used Python 3.11.4 and Node.js 22.19.0. To check everything without writing or contacting IRSA, run `python scripts/bootstrap_demo_data.py --check-only --with-comparisons`.

The checkout supplies the compact **2,708,179-byte** cube preview and its source records. The bootstrap verifies their hashes without downloading full cube tiles. The preview preserves 102 native DR1 channel slots and their map windows per preset. The measured values are co-added surface brightness at a sky pixel. Blank, flagged, and uncovered values remain gaps. Dated detector samples do not provide a resolved continuum. If a future verified cube refresh changes the artifact bytes, update the cube and source-record hashes in `data/manifests/demo_preview_assets.json` together with the regenerated files. [Cube refresh method](HANDOFF.md#offline-spectral-cube-preview)

Start the audited preview after the bootstrap passes.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-demo.ps1 -Dataset Preview
```

To search IRSA for additional observations and request new cutouts, add `-Live` to the same command. Live results depend on archive availability; if the archive does not return observations, the app identifies any cached fallback. The cached preview has two saved observations per preset and fixed cutout footprints.

The app opens at `http://127.0.0.1:5173/`. The launcher checks `http://127.0.0.1:8000/api/health` and `/api/demo/manifest` before opening it. It pins observation searches to the selected cache and labels the app **Cached demo**. Spectral Cube attempts the archive first and can fall back to verified local samples at the optional preview’s five preset coordinates. Aladin surveys and other archive-backed features can still require internet access. [Offline cube walkthrough](docs/DEMO_SCRIPT.md#offline-spectral-cube)

All five presets have two covered epochs. Source identity, target flux, motion and variability remain unconfirmed. The accepted D5 comparison validates arithmetic on retained field pixels around the predicted Epsilon Indi position. Epsilon Indi Ba and Bb remain unresolved. Three apertures pass field-sampling checks only. WISE 0855 can be blinked. Its tested calibrated difference and pair co-add return HTTP 422 for incompatible passbands. [Target evidence](docs/TARGET_VALIDATION.md)

Use the [3:30 judge walkthrough](docs/DEMO_SCRIPT.md) for the rehearsed launch URL and sequence. The current build is verified locally. [Submission checklist](docs/SUBMISSION_CHECKLIST.md)

To stop the launcher-owned servers and keep the logs and cache:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop-demo.ps1
```

- For the original 22-frame data, add `-Dataset Original` to the start command. It selects `data/manifests/demo_dataset.json` and requires the separate original FITS cache. The ten-frame bootstrap leaves it alone. Only four original RW Aurigae cutouts cover a preset prediction at exposure time. A server started manually still uses the original manifest by default and can use live observations.
- For busy ports, add `-ApiPort 18100 -AppPort 15173`. The launcher prints the selected URLs and leaves existing listeners running. Add `-NoBrowser` to start without opening a window.
- If IRSA returns a download error, rerun the bootstrap when the archive is reachable. It reuses successfully verified files. If an existing cache file fails verification, move that file aside before retrying. With a missing cache, use the read-only check to list the inputs before retrying the network bootstrap.
- For startup failures, read the server logs and `fits-audit.json` in the timestamped directory under `.spherex-demo.local`. The launcher requires a clean FITS audit for the ten-frame stage. The original permits its documented audit warnings. On a slow system, add `-StartupTimeoutSeconds 90`. If a previous session is recorded, run the stop command first.

The refresh tool writes a new candidate directory and audits it with warnings treated as failures. The live preview can read the staged manifest and its neighboring FITS files through `SPHEREX_DEMO_MANIFEST`. Removing that environment setting restores the default demo the next time the backend starts.

In PowerShell from the repository root, use the staged catalog-validation results if available locally.

```powershell
python scripts/build_demo_dataset.py --evidence data/cache/target_validation/evidence.json --source-cache data/cache/target_validation --stage-dir data/cache/demo_refresh
$env:SPHEREX_DEMO_MANIFEST = (Resolve-Path data/cache/demo_refresh/demo_dataset.json).Path
```

Review `data/cache/demo_refresh/audit.json` before starting the backend in that same shell. Choose another new directory if `demo_refresh` already exists. The staging directory uses exact archive URLs as cache keys. For general imagery, the tool also accepts `--probe` and does not assert catalog coverage for those files.

---

## Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Git

### 1. Install backend dependencies and check IRSA connectivity
```bash
python -m pip install -r backend/requirements.txt
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

In a second terminal, start from the repository root.
```bash
cd frontend
npm ci
npm run build
npm run dev
```
Open browser to `http://localhost:5173`

## Public release preflight

The [Aladin Lite third-party notice](frontend/public/third-party/aladin-lite/NOTICE.txt) identifies the bundled version, exact upstream source, and accompanying license texts.

The current release candidate is local. Use the [Windows preview](#preview-a-refreshed-demo-cache) for the rehearsed demonstration. The GitHub landing page was reachable on 2026-11-15. Render returned HTTP 404 with `x-render-routing: no-server` for both repository-named hosts. A public frontend URL could not be established from the repository or its public GitHub metadata. [Endpoint results and pre-deploy checklist](docs/SUBMISSION_CHECKLIST.md#4-public-release-preflight)

Create the Python web service from the repository's `render.yaml` using a [Render Blueprint](https://dashboard.render.com/blueprints). Its build installs `backend/requirements.txt`, and Uvicorn binds to `0.0.0.0:$PORT`. Confirm the assigned host returns healthy JSON at `/api/ready`, then check `/api/health` for IRSA connectivity. The readiness check is independent of the external archive. Keep one backend worker and instance until observation metadata and file caches have shared storage.

For Vercel, import this repository with root directory `frontend`, the Vite preset, build command `npm run build`, and output directory `dist`. Compare the Render-assigned host to `frontend/vercel.json` and update the `/api/:path*` rewrite if needed. After deployment, verify `/api/ready` and `/api/demo/presets` through the Vercel URL, then open Explorer and load a real frame and a 102 Bands link. Vite’s `SPHEREX_DEMO_API_PORT` controls the local proxy only. [Render Blueprint reference](https://render.com/docs/blueprint-spec) · [Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite)

The browser calls the frontend’s own `/api` path. Render’s Blueprint sets `CORS_ORIGINS` to an empty value, which disables cross-origin browser access and supports the same-origin proxy. With the setting unset, the backend permits only the built-in localhost development origins. If a production frontend needs direct browser access to the backend, list only its exact HTTP(S) origin in `CORS_ORIGINS`. Wildcards, paths and origin strings with credentials fail startup validation. Keep real environment settings outside Git.

Docker Compose builds the backend from the repository root and the frontend from `frontend/`. Nginx serves the built SPA on port 3000 and proxies `/api/` to `backend:8000`. The backend container reads `./data` through its volume mount. The backend defaults cover a normal archive launch. To use `.env.example` locally, pass its values as process environment variables or use Uvicorn’s `--env-file` with an explicit path.

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

The bootstrap stages released DR1/QR3 products directly from the public IRSA archive. Exact versioned URLs, sizes and checksums are in [the preview asset pins](data/manifests/demo_preview_assets.json). The compact cube cache preserves the native sampled values and cites the original FITS products in [its source records](data/manifests/cube_preview_sources.json). Acknowledge NASA-funded SPHEREx, the JPL and Caltech mission, and NASA/IPAC IRSA when presenting these data. [IRSA public data terms](https://irsa.ipac.caltech.edu/data_use_terms.html) · [DR1 spectral images DOI](https://doi.org/10.26131/IRSA678) · [DR1 cube DOI](https://doi.org/10.26131/IRSA679)
- SPHEREx DR1 Spectral Images DOI: `10.26131/IRSA678`
- SPHEREx DR1 All-Sky Cube DOI: `10.26131/IRSA679`
- NASA Space Apps Challenge 2026: "Planet X and SPHEREx"
