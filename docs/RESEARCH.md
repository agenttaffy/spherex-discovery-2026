# In-Depth Scientific & Architectural Research

## 1. Challenge Definition & Constraints
- **Event:** NASA Space Apps Challenge 2026
- **Challenge Title:** Planet X and SPHEREx
- **Challenge Prompt:** Create a public-facing web application that displays images of the sky obtained by SPHEREx and allows users to easily see how the sky changes over time.
- **Official Judging Criteria:**
  1. **Impact:** Clear accessibility for citizen scientists, students, and astronomers to discover transient infrared events or moving objects.
  2. **Creativity:** Intuitive blink comparison, interactive timeline playback, responsive WCS coordinates, and clean astronomical visualization.
  3. **Validity:** Strict adherence to calibrated SPHEREx Level 2 data, proper coordinate transformations, and rejection of fake detections.
  4. **Relevance:** Direct utilization of NASA IRSA SIA2 and IBE cutout endpoints.
  5. **Presentation:** Polished dark-mode astronomical UI, responsive layout, clear provenance data.

## 2. SPHEREx Mission Technical Specifications
- **Telescope Architecture:** 20 cm all-aluminum unobscured eccentric Cassegrain telescope.
- **Detectors:** 6 focal plane arrays (3 short-wavelength Teledyne H2RG detectors D1–D3 covering 0.75–2.4 µm, and 3 long-wavelength detectors D4–D6 covering 2.4–5.0 µm).
- **Pixel Scale:** 6.2 arcseconds per pixel.
- **Instantaneous Field of View:** 3.5° × 11.3°.
- **Spectral Resolution:** R ~ 35 to 130 across 102 distinct spectral channels using Linear Variable Filters (LVF).
- **Survey Cadence:** SPHEREx scans the sky along great circles perpendicular to the Sun line, observing every point on the celestial sphere every 6 months across a 2-year primary mission (Surveys 1, 2, 3, 4).

## 3. Data Releases & Archive Endpoints
- **IRSA SPHEREx Mission Archive:** `https://irsa.ipac.caltech.edu/Missions/spherex.html`
- **Official Citation DOIs:**
  - SPHEREx DR1 Spectral Images: `10.26131/IRSA678`
  - SPHEREx DR1 All-Sky Cube: `10.26131/IRSA679`
- **API Access:**
  - **SIA2 Protocol:** Supported by NASA/IPAC for spatial queries returning VO/CSV metadata.
  - **IBE Cutout Protocol:** The Image-Based Evaluation (IBE) service allows dynamic sub-image slicing directly from cloud-accessible FITS storage via URL parameters: `?center=<ra>,<dec>&size=<deg>`.
  - Full L2 FITS size: ~70 MB.
  - Cutout size (0.05° ~ 3 arcmin): ~3.9 MB. This 18x reduction in payload size enables real-time web exploration without choking client bandwidth.

## 4. Astrometric & Photometric Analysis of Test Targets
| Target | RA (deg) | Dec (deg) | Expected Phenomenon | DR1 Epoch | QR3 Epoch | Baseline |
|---|---|---|---|---|---|---|
| **WISE 0855** | 133.79513 | -7.24515 | Sub-stellar motion (~8.1″/yr) | 2025-05 | N/A | N/A |
| **Barnard's Star** | 269.45208 | +4.69339 | Highest proper motion (10.3″/yr) | 2025-08 | 2026-08 | ~1.0 yr |
| **Epsilon Indi B** | 330.84000 | -56.78600 | Binary brown dwarf motion (4.7″/yr) | 2025-04 | 2026-09 | ~1.4 yr |
| **RW Aurigae** | 76.95420 | +30.40140 | Irregular circumstellar accretion bursts | 2025-09 | 2026-09 | ~1.0 yr |
| **R Draconis** | 248.33750 | +66.70420 | Mira long-period pulsation (~245 days) | 2025-05 | 2026-05 | ~1.0 yr |

## 5. Algorithmic Image Registration & Differencing
- **Spatial Alignment:** SPHEREx pixels are 6.2″. Between two observations separated by months, pointing orientation differs. Astropy WCS and bilinear/bicubic resampling must reproject candidate frames to a shared target grid before difference calculations ($I_{\text{diff}} = I_2 - I_1$).
- **Display Scaling:** The `asinh` stretch function is implemented as:
  $$f(x) = \frac{\text{asinh}((x - \text{min}) / \text{non\_linear\_factor})}{\text{asinh}((\text{max} - \text{min}) / \text{non\_linear\_factor})}$$
  This preserves both faint background structure and bright stellar cores without saturation clipping.
