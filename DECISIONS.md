# Architecture Decision Records (ADR)

## ADR-001: Separate FastAPI Backend from React Frontend
- **Date:** 2026-11-14
- **Decision:** Build a dedicated Python FastAPI backend alongside a Vite/React frontend rather than a serverless Next.js or pure client-side app.
- **Rationale:** NASA SPHEREx Level 2 data is distributed as multi-extension FITS files containing WCS keywords, quality bitmasks, and float32 arrays in MJy/sr. The standard astronomical tooling for parsing, aligning, and calibrating these files is `astropy`, `scipy`, and `numpy`. Running these in Python guarantees 100% scientific compliance, zero floating-point corruption, and seamless access to IPAC services.

## ADR-002: Dynamic Sub-Array Cutouts over Full-Frame Downloads
- **Date:** 2026-11-14
- **Decision:** Utilize the NASA/IPAC IBE Cutout protocol (`?center=<ra>,<dec>&size=<deg>`) rather than downloading full Level 2 spectral images.
- **Rationale:** Full SPHEREx Level 2 FITS files are approximately 70 MB each. Requesting small cutouts (0.02° to 0.08° / 1.2′ to 4.8′) downloads ~3.9 MB per frame (an 18x reduction in bandwidth), allowing real-time interactive multi-epoch animation without overloading client connections.

## ADR-003: Non-Destructive Display-Only Contrast Stretching
- **Date:** 2026-11-14
- **Decision:** Preserve raw pixel floating-point arrays in `MJy/sr` units while generating display previews using `asinh` (arcsinh), `zscale`, and percentile clipping.
- **Rationale:** Mid-infrared astronomical data spans multiple orders of magnitude (from zodiacal background of ~0.5 MJy/sr to stellar cores >1,000 MJy/sr). Naive linear scaling either washes out faint structures or clips cores. The arcsinh stretch reveals both simultaneously while keeping raw scientific data untouched in telemetry and difference calculations.

## ADR-004: Local Demonstration Cache with Fallback Resilience
- **Date:** 2026-11-14
- **Decision:** Cache 22 verified FITS cutouts for the official competition targets locally in `data/cache/`.
- **Rationale:** During hackathon judging sessions, internet connectivity and remote archive endpoints can suffer latency or rate-limiting. A verified cache ensures zero downtime and instant responsiveness during the live demonstration.
