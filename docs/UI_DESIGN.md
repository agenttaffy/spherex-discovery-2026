# UI/UX Design System: Deep Infrared Astronomical Explorer

## 1. Design Philosophy
Astronomical inspection requires extreme contrast fidelity, dark adaptation preservation, responsive 60 FPS viewport manipulation, and uncluttered instrument telemetry.
- **Color Palette:**
  - Background Deep Space Navy: `#020617` (Slate 950)
  - Panel Surfaces: `#0f172a` (Slate 900) with `#1e293b` (Slate 800) borders
  - Primary Accent: Astronomical Cyan `#38bdf8` / `#06b6d4`
  - Infrared Heatmap Accents: `#f43f5e` (Rose), `#fbbf24` (Amber), `#10b981` (Emerald)
  - Typography: Inter for UI chrome and navigational elements; JetBrains Mono for coordinates, epochs, and pixel telemetry.

## 2. Layout Hierarchy
1. **Top Header Bar (64px):**
   - Brand: SPHEREx Discovery (NASA Space Apps 2026)
   - Navigation: Explorer & Timeline, Blink Comparator, Difference Engine, About & Science
   - Action buttons: Guided Tour, Share URL (deep linking), Export Report
   - Global status: NASA/IPAC IRSA Live vs. Demo Cache Active indicator
2. **Left Control Dock (320px):**
   - Quick Target Presets: Barnard's Star, WISE 0855, RW Aurigae, R Draconis, Epsilon Indi B
   - Coordinate Search: RA / Dec inputs with Sexagesimal / Decimal auto-detect and validation
   - Field of view (FOV) selector: 0.02° to 0.10°
   - Data release (`spherex_dr1`, `spherex_qr3`) & detector filters (D1–D6)
3. **Center Astronomical Canvas (Fluid Flex):**
   - Hardware-accelerated HTML5 Canvas 2D renderer with nearest-neighbor block interpolation
   - Interactive mouse drag pan and wheel zoom ($0.4\times$ to $8.0\times$)
   - Gaia DR3 catalog reference star vector overlay with proper motion arrows
   - Live celestial crosshair and cursor position HUD
   - Contrast stretch controls: Asinh, ZScale, Linear
   - Colormap selector: Grayscale and Inferno
4. **Bottom Time-Lapse Player (76px):**
   - Multi-epoch scrubber bar with observation markers
   - Step forward / backward, Play / Pause, variable FPS (1–10 fps)
   - Blink Comparison mode: rapid 2-frame alternate blink
   - In-memory frame caching and adjacent prefetching for zero latency
5. **Right Telemetry & Science Dock (320px):**
   - Interactive Circular Aperture Photometry Light Curve SVG chart with variability detection
   - Observation metadata: ObsID, Release, Detector, UTC Date, dimensions
   - Scientific pixel telemetry: peak flux, baseline, mean, noise ($\pm\sigma$) in $\text{MJy/sr}$
   - Quality flag bitmask breakdown: masked pixels, saturation, cosmic rays, dead pixels
   - Celestial WCS parameters: CRVAL1, CRVAL2, nominal 6.2″/pixel scale
   - One-click "Export Discovery Report" modal trigger
   - Direct NASA IRSA FITS provenance hyperlink
6. **Modals & Overlays:**
   - **Guided Tour Modal:** 4-step interactive educational walkthrough explaining LVF physics and challenge targets
   - **Discovery Report Modal:** Formatted Markdown and structured JSON report preview and download
