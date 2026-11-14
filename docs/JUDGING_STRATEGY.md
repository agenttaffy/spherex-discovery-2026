# NASA Space Apps Challenge 2026 — Judging Strategy & Criteria Alignment

## Judging Category Alignment

### 1. Impact (Weight: 20%)
- **Citizen Science & Education:** Allows non-specialists to inspect genuine NASA infrared survey data without requiring Astropy, DS9, or Python expertise.
- **Scientific Utility:** Enables rapid visual identification of transient events (supernovae, active galactic nuclei flaring) and proper-motion candidates (brown dwarfs, nearby low-mass stars).

### 2. Creativity (Weight: 20%)
- **Interactive Multi-Epoch Blink Comparator:** Recreating classic astronomical blink comparator workflows (like Clyde Tombaugh used to discover Pluto) in a modern web interface.
- **Dynamic Asinh Stretch Engine:** Real-time client-side and server-side contrast adjustment allowing users to see faint dust and stellar cores simultaneously.

### 3. Validity (Weight: 20%)
- **Zero Hallucinated Astronomy:** All observations queried directly from NASA/IPAC IRSA SIA2 endpoints.
- **Accurate Physics & Calibration:** Units strictly preserved in MJy/sr; linear variable filter dispersion effects acknowledged; quality flag bitmasks evaluated.

### 4. Relevance (Weight: 20%)
- Direct adherence to the "Planet X and SPHEREx" challenge requirements:
  - Takes RA/Dec coordinates.
  - Queries real SPHEREx image series.
  - Plays images in video/animation format.
  - Demonstrates detection of position and brightness changes across the 5 official targets.

### 5. Presentation (Weight: 20%)
- High-contrast, publication-grade dark astronomy UI.
- Real-time telemetry, clear scientific explanations, and complete data provenance attribution.
