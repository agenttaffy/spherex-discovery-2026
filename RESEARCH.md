# SPHEREx Discovery — Research Summary

## 2026-11-14 — Sky context and interface sources

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) informed keyboard, focus, labels and non-color state cues. [Nielsen Norman Group on complex applications](https://www.nngroup.com/articles/complex-application-design/) and [progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/) informed the collapsible analysis and prioritization of the image. These references do not establish conformance.
- The supplied CDS Aladin documentation paths returned HTTP 404 during this session. The installed `aladin-lite` npm package and [Aladin API](https://cds-astro.github.io/aladin-lite/Aladin.html) document the v3 `A.init` lifecycle. The CDS direct script and tested CDS HiPS endpoints also returned 404; this is a point-in-time observation, not a diagnosis of a general outage.
- IRSA's HiPS mirror returned metadata and all-sky image HTTP 200 for 2MASS Color and DSS2 color. 2MASS metadata identifies all-sky coverage, ODbL-1.0, University of Massachusetts/IPAC-Caltech and CDS HiPS production. [MAST DSS data-use guidance](https://archive.stsci.edu/publishing/data-use) specifies CC BY-NC-SA 4.0; DSS usage is restricted to scientific/nonprofit purposes. These layers are contextual survey imagery, not SPHEREx measurements.
- [IRSA SPHEREx data-product documentation](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/) describes separate per-pixel wavelength calibration products. One header UUID was resolved via IRSA's artifact table to a D1 calibration file and its published MD5 was verified; using the file in cutout-to-detector compatibility calculations is unfinished and remains guarded.

## 1. NASA SPHEREx Mission & Data Architecture
- **Mission Overview:** The Spectro-Photometer for the History of the Universe, Epoch of Reionization and Ices Explorer (SPHEREx) is a NASA MIDEX mission conducting an all-sky infrared survey across 0.75 to 5.0 µm in 102 spectral channels.
- **Instrument Design:** 6 optical detectors with Linear Variable Filters (LVF) (Detectors 1 through 6). The effective passband shifts continuously across the detector surface.
- **Data Releases:**
  - **DR1 (Data Release 1):** Covers Surveys 1 and 2 (May 2025 – Nov 2025 baseline). Reprocessed with high-accuracy celestial astrometry and photometric calibration.
  - **QR3 (Quick Release 3):** Covers Surveys 3 and 4 (May 2026 – Nov 2026 baseline).
  - *Note on Cube vs Images:* The DR1 All-Sky Cube merges spectral channels into 102 bands but combines epochs into a static map. **Temporal detection must use individual Level 2 Spectral Image cutouts.**

## 2. Verified IRSA API Endpoints & Protocols
- **SIA2 Query Endpoint:** `https://irsa.ipac.caltech.edu/SIA`
  - Validated Parameters: `COLLECTION=spherex_dr1` (or `spherex_qr3`), `POS=circle <ra_deg> <dec_deg> <radius_deg>`, `RESPONSEFORMAT=CSV` (or `VOTABLE`).
  - Response Fields: `obs_id`, `access_url`, `t_min` (MJD), `t_max`, `energy_bandpassname`, `s_ra`, `s_dec`, `em_min`, `em_max`.
- **IBE Cutout Service:**
  - Append `?center=<ra>,<dec>&size=<deg>` to the Level 2 FITS URL.
  - Verified Example: `https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W18_1B/l2b-v27-2026-196/1/level2_2025W18_1B_0162_1D1_spx_l2b-v27-2026-196.fits?center=127.69444,-39.17760&size=0.05`
  - Returns: Multi-extension FITS cutout containing sub-arrays for all primary extensions (~4 MB vs 70 MB for full frame).

## 3. Scientific FITS Extension Verification
From live testing on IRSA cutouts:
- `PRIMARY`: Metadata header (TELESCOP='SPHEREx', INSTRUME='SPHEREx').
- `IMAGE`: Ext 1, float32 array, units `MJy/sr` (calibrated surface brightness, zodiacal light included).
- `FLAGS`: Ext 2, int32 bitmask encoding bad pixels, cosmic rays, saturation, stray light.
- `VARIANCE`: Ext 3, float32 measurement variance per pixel.
- `ZODI`: Ext 4, float32 modeled zodiacal background (MJy/sr).
- `EPSF`: Ext 5, effective point-spread function table.
- `WCS-WAVE`: Ext 6, wavelength calibration table mapping detector coordinates to wavelength in microns.

## 4. Official Test Targets Verification
Live queries via `probe_irsa.py` confirmed observations in both DR1 and QR3:
1. **WISE 0855** (RA 133.79513°, Dec -7.24515°): 282 DR1 observations (May 2025). Coldest known sub-stellar brown dwarf (~250 K).
2. **Barnard's Star** (RA 269.45208°, Dec 4.69339°): 255 DR1 observations (Aug 2025), 126 QR3 observations (Aug–Sep 2026). 1.0-year temporal baseline, high proper motion (~10.3″/yr).
3. **Epsilon Indi B** (RA 330.84000°, Dec -56.78600°): 403 DR1 observations (Apr 2025), 122 QR3 observations (Sep 2026). ~1.4-year temporal baseline.
4. **RW Aurigae** (RA 76.95420°, Dec 30.40140°): 228 DR1 observations (Sep 2025), 114 QR3 observations (Sep 2026). Classical T Tauri variable star.
5. **R Draconis** (RA 248.33750°, Dec 66.70420°): 452 DR1 observations (May 2025), 132 QR3 observations (May 2026). Mira pulsating variable star.

## 5. Scientific Display & Comparison Caveats
- Visual stretch: SPHEREx data spans orders of magnitude. Must provide `asinh` (arcsinh) and `ZScale` stretching to reveal faint point sources against zodiacal background without clipping.
- Registration: Reprojection or WCS grid alignment is essential before differencing frames because pointing jitter and survey scans produce sub-pixel shifts and rotational variations.
- Wavelength Matching: Images subtracted must be from the same detector band (or interpolated to the same effective wavelength) to prevent false-positive differencing artifacts caused by spectral slope differences.


## Interface and data references (2026-11-14)
- [IRSA SPHEREx overview](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/overview.html): LVF images associate each position with a wavelength; full coverage accumulates over time. Detector labels alone do not prove wavelength compatibility.
- [IRSA visualization guide](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/visualization.html): Level 2 products include IMAGE, FLAGS, VARIANCE and WCS-WAVE extensions. Missing metadata must stay unknown.
- [CDS HiPS documentation](https://aladin.cds.unistra.fr/hips/): context surveys are separate progressive image layers, not SPHEREx science images.
- These references support explicit provenance, wavelength and uncertainty labels. Automated source checks are not a substitute for keyboard, screen-reader and visual testing.

- [IRSA SPHEREx Explanatory Supplement, v2.1](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf): the embedded WCS-WAVE lookup is suitable for visualization; science analysis should use separate spectral WCS files. A shared detector does not verify per-pixel wavelength compatibility. Difference and stacking are guarded pending integration and validation.
