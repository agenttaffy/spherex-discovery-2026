# SPHEREx Discovery — Prioritized Backlog

## P0: Core Challenge & Eligibility (ALL COMPLETED)
- [x] `P0-001` | COMPLETED | Live NASA IRSA SIA2 observation search integration (`irsa_client.py`)
- [x] `P0-002` | COMPLETED | Multi-extension FITS cutout pipeline & parsing (`cutout_service.py`, `fits_processing.py`)
- [x] `P0-003` | COMPLETED | Celestial coordinate validation (decimal & sexagesimal) (`coordinates.py`)
- [x] `P0-004` | COMPLETED | Interactive astronomical explorer frontend with HTML5 Canvas (`CanvasViewer.tsx`, `App.tsx`)
- [x] `P0-005` | COMPLETED | Multi-epoch chronological timeline player & Blink Comparator (`TimelinePlayer.tsx`)
- [x] `P0-006` | COMPLETED | Verification against all 5 official test targets (`probe_results.json`, `demo_dataset.json`)

## P1: Scientific Validity & High Judging Impact (COMPLETED & READY)
- [x] `P1-001` | COMPLETED | Calibrated differential image engine ($I_2 - I_1$) (`comparison.py`, `ComparisonView.tsx`)
- [x] `P1-002` | COMPLETED | Display contrast scaling engines (`asinh`, `zscale`, `linear`)
- [x] `P1-003` | COMPLETED | Data quality flag bitmask evaluation (`flags_processing.py`, `MetadataPanel.tsx`)
- [x] `P1-004` | COMPLETED | Local caching of 22 verified real FITS cutouts for judging demo reliability (`data/cache`)
- [x] `P1-005` | COMPLETED | Full automated test suite (23 pytest tests passing)

## P2: Advanced Astronomy & User Experience (Next Iteration)
- [ ] `P2-001` | OPEN | Gaia DR3 celestial source overlay (render star markers on canvas)
- [ ] `P2-002` | OPEN | Multi-epoch photometric light curve graph for variable stars (RW Aurigae, R Draconis)
- [ ] `P2-003` | OPEN | Shareable deep-link state encoder (e.g., `/explore?target=barnards_star&stretch=asinh`)
- [ ] `P2-004` | OPEN | Spectral energy distribution (SED) plot across detectors D1–D6

## P3: Enhancements
- [ ] `P3-001` | OPEN | Automated sub-pixel moving object trajectory vector drawing
- [ ] `P3-002` | OPEN | Export discovery report as publication-ready PDF
- [ ] `P3-003` | OPEN | Aladin Lite sky overview map embedding
