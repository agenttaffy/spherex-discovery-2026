# SPHEREx Discovery — 3-Minute Live Judging Demonstration Script

This script is structured for a 180-second live presentation to NASA Space Apps judges.

---

### [0:00 – 0:30] Introduction & The Scientific Problem
- **Speaker:**
  > "Judges, NASA's SPHEREx mission is mapping the entire sky every 6 months across 102 infrared bands from 0.75 to 5 microns. But discovering moving brown dwarfs or variable stars across millions of multi-extension FITS images is notoriously difficult due to SPHEREx's unique Linear Variable Filters.
  > Today, we present **SPHEREx Discovery** — an interactive astronomical discovery platform that makes exploring multi-epoch SPHEREx data fast, scientifically rigorous, and accessible."
- **Action:** Open application landing page with live NASA/IPAC IRSA status badge glowing green.

---

### [0:30 – 1:15] Target 1: Barnard's Star & Astrometric Motion
- **Speaker:**
  > "Let's begin with **Barnard's Star**, the highest proper motion star in the sky, moving at over 10 arcseconds per year.
  > In our central Canvas viewer, rendered at 60 FPS with nearest-neighbor interpolation, we see the raw calibrated Level 2 FITS image in physical units of MJy/sr. We can toggle between Asinh and ZScale contrast stretches.
  > Notice the timeline at the bottom: as we drag across epochs from DR1 in 2025 to QR3 in 2026, adjacent frames are prefetched with zero latency.
  > Let's switch to the **Difference Engine**: our backend performs sub-pixel 2D Fourier phase registration and subtracts Epoch 1 from Epoch 2.
  > Look at that signature: a clear **astrometric dipole**! Our automated vector engine measures an angular displacement of 10.3 arcseconds, a proper motion of 10.31 arcsec/year, and plots the proper motion vector pointing North."
- **Action:** Select "Barnard's Star", drag timeline, switch to "Difference Engine", show dipole vector and motion card.

---

### [1:15 – 2:00] Target 2: RW Aurigae & Photometric Light Curve
- **Speaker:**
  > "Now, let's explore **RW Aurigae**, a young T Tauri variable star where protoplanetary disk disruptions cause violent brightness dips.
  > Notice that when we differencing RW Aurigae, there is NO dipole vector — because the star is stationary in space ($\Delta x \approx 0$). Instead, it leaves a pure flux monopole.
  > On the right telemetry dock, our automated circular aperture photometry engine has extracted the calibrated light curve across all epochs: we see a massive flux range of over 16 MJy/sr and an automated 'CONFIRMED VARIABLE' badge. Clicking any point instantly navigates to that observation epoch."
- **Action:** Click "RW Aurigae" preset, show Light Curve chart, hover points, click to jump to peak flux epoch.

---

### [2:00 – 2:30] Target 3: Gaia DR3 Catalog Overlay & Discovery Export
- **Speaker:**
  > "Next, let's toggle the **Gaia DR3 Catalog Overlay**: reference stars and proper motion vectors are projected directly onto our celestial canvas using Astropy celestial WCS.
  > When a discovery is confirmed, clicking **Export Discovery Report** generates a complete, publication-ready report formatted with J2000 sexagesimal coordinates, astrometric vectors, light curve metrics, and official NASA IRSA DOI citations (10.26131/IRSA678), ready for download in Markdown or JSON."
- **Action:** Toggle Gaia DR3 overlay on canvas, click "Export Discovery Report", show modal, preview Markdown, download JSON.

---

### [2:30 – 3:00] Architecture, Reliability & Closing
- **Speaker:**
  > "Under the hood:
  > - Python 3.11 FastAPI backend backed by Astropy, NumPy, and SciPy with 43 passing automated tests.
  > - React 18 & TypeScript frontend with zero compilation errors.
  > - 100% presentation uptime: in addition to live NASA IRSA SIA2 integration, 22 verified real FITS cutouts are cached locally.
  > - One-click Docker containerization and cloud deploy ready on Render and Vercel.
  > Thank you, and we welcome your questions!"
- **Action:** Show About page and Guided Tour modal.
