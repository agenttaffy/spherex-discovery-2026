# UI/UX Design System: Deep Infrared Astronomical Explorer

## 1. Design Philosophy
Astronomical inspection requires extreme contrast fidelity, dark adaptation preservation, and uncluttered instrument control.
- **Color Palette:**
  - Background Deep Navy: `#0b0f19` / `#050811`
  - Panel Surfaces: `#111827` with subtle `#1f293d` borders
  - Primary Accent: Scientific Indigo/Cyan `#38bdf8` / `#6366f1`
  - Infrared Heatmap Accents: `#f43f5e` (highlights), `#fbbf24` (indicators)
  - Typography: Inter / SF Pro for interface labels; JetBrains Mono for coordinates, epochs, and pixel telemetry.

## 2. Layout Hierarchy
1. **Top Header Bar (56px):**
   - Brand: SPHEREx Discovery
   - Badge: NASA Space Apps Challenge 2026
   - Global status: IRSA Live / Demo Mode toggle
2. **Left Control Dock (320px):**
   - Quick Target Presets: WISE 0855, Barnard's Star, RW Aurigae, etc.
   - Coordinate Search: RA / Dec inputs with Sexagesimal / Decimal auto-detect.
   - Field of view (FOV) selector: 3 arcmin (0.05°), 6 arcmin (0.10°), 12 arcmin (0.20°).
   - Data release & detector filters.
3. **Center Astronomical Canvas (Fluid Flex):**
   - High-DPI Canvas 2D renderer.
   - Interactive mouse pan and wheel zoom.
   - Live crosshair with RA/Dec and MJy/sr flux telemetry under cursor.
   - Contrast stretch controls: asinh, ZScale, MinMax, Log.
   - Colormap selector: Grayscale, Inferno, Magma, Viridis.
4. **Bottom Time-Lapse Player (80px):**
   - Multi-epoch scrubber bar with observation markers.
   - Step forward / backward, Play / Pause.
   - Playback speed slider (0.5 fps to 5 fps).
   - Blink Comparison mode: rapid 2-frame alternate blink.
   - Epoch timestamp and delta-t indicator ($\Delta t = +366$ days).
5. **Right Telemetry & Provenance Dock (300px):**
   - Observation metadata: ObsID, UTC Date, MJD, Release.
   - Instrument specs: Detector (D1–D6), Wavelength coverage ($\lambda = 0.75 - 1.12$ µm).
   - Quality flag status and variance estimation.
   - Direct NASA IRSA FITS provenance hyperlink.
