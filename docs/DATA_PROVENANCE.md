# SPHEREx Discovery — Data Provenance & Archival Citations

## 1. Primary Data Source
All SPHEREx observational data utilized in this application originate from the **NASA/IPAC Infrared Science Archive (IRSA)**.

- **Data Archive:** NASA/IPAC Infrared Science Archive (IRSA)
- **Primary Archival DOI:** [10.26131/IRSA678](https://doi.org/10.26131/IRSA678)
- **Data Collections:**
  - `spherex_dr1`: SPHEREx Data Release 1 (Level 2 Calibrated Images, August 2025 baseline)
  - `spherex_qr3`: SPHEREx Quick Release 3 (Level 2 Calibrated Images, August 2026 baseline)
- **Query Protocol:** IVOA Simple Image Access Protocol Version 2.0 (SIA2)
  - Endpoint: `https://irsa.ipac.caltech.edu/SIA`
- **Cutout Protocol:** IRSA Image Boundary & Cutout Service (IBE)
  - Base Pattern: `https://irsa.ipac.caltech.edu/ibe/data/spherex/{release}/level2/{survey}/{version}/{det_num}/...fits?center={ra},{dec}&size={fov}`

---

## 2. FITS Data Structure & Quality Metadata

SPHEREx Level 2 Calibrated Image products are stored as multi-extension FITS files:

| HDU Index | HDU Name | Data Type | Dimensions | Physical Unit / Content |
|---|---|---|---|---|
| Extension 0 | `PRIMARY` | `float32` | $2048 \times 2048$ (full frame) / $20 \times 20$ (cutout) | Surface Brightness in $\text{MJy/sr}$ |
| Extension 1 | `VARIANCE` | `float32` | $2048 \times 2048$ | Error variance in $(\text{MJy/sr})^2$ |
| Extension 2 | `FLAGS` | `uint16` / `uint32` | $2048 \times 2048$ | Data quality bitmask flags |

### Quality Flag Bitmask Table

| Bit Position | Value | Flag Identifier | Physical Meaning & Handling |
|---|---|---|---|
| Bit 0 | 1 | `DO_NOT_USE` | Unusable detector pixel (masked out) |
| Bit 1 | 2 | `SATURATED` | Full well electron saturation (excluded from linear photometry) |
| Bit 2 | 4 | `COSMIC_RAY` | Transient energetic particle strike |
| Bit 3 | 8 | `DEAD` | Dead / unresponsive pixel |
| Bit 4 | 16 | `HOT` | Abnormally high dark current |
| Bit 5 | 32 | `EDGE` | Detector physical boundary artifact |

---

## 3. Verified Demonstration Dataset

To guarantee 100% presentation uptime and zero latency during live judging reviews, the repository includes a curated, fully verified offline demonstration dataset (`data/manifests/demo_dataset.json`):
- **Total Cached FITS Cutouts:** 22 verified multi-extension FITS files
- **Total Cache Volume:** 40.4 MB in `data/cache/`
- **Coverage:** Multi-epoch observations across all 5 official challenge targets:
  1. **Barnard's Star:** 4 cutouts across DR1 and QR3 (Detectors D1, D3, D4)
  2. **WISE 0855:** 4 cutouts in D4 and D5 mid-IR bands
  3. **RW Aurigae:** 4 cutouts across early and late epochs
  4. **R Draconis:** 4 cutouts covering maximum and minimum pulsation phases
  5. **Epsilon Indi B:** 4 cutouts tracking binary orbital motion
  6. **Documentation Example:** 2 verified reference cutouts

---

## 4. Citation & Attribution Formats

### BibTeX
```bibtex
@misc{irsa_spherex_2026,
  author       = {{SPHEREx Science Team} and {NASA/IPAC Infrared Science Archive}},
  title        = {{SPHEREx Data Release 1 and Quick Release 3 Level 2 Science Archive}},
  year         = 2026,
  publisher    = {IPAC, California Institute of Technology},
  doi          = {10.26131/IRSA678},
  url          = {https://doi.org/10.26131/IRSA678}
}
```

### Formal Space Apps Acknowledgment
> "This platform utilizes public scientific data products from NASA's SPHEREx mission, distributed by the NASA/IPAC Infrared Science Archive (IRSA) under DOI 10.26131/IRSA678. Celestial coordinate transformations and WCS solutions are evaluated using Astropy."
