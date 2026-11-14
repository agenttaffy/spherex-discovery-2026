# Scientific Methodology & Data Standards

## 1. Astronomical Coordinate Integrity
All celestial coordinates undergo strict validation:
- Right Ascension $\alpha \in [0^\circ, 360^\circ)$
- Declination $\delta \in [-90^\circ, +90^\circ]$
- Support for sexagesimal strings (e.g., `08h55m10.831s -07d14m42.53s`) parsed via `astropy.coordinates.SkyCoord`.
- High precision retained across queries to avoid truncation or roundoff drift in astrometric comparisons.

## 2. Multi-Extension FITS Handling
SPHEREx Level 2 Spectral Image cutouts are processed strictly following IPAC/SPHEREx instrument documentation:
1. **IMAGE (Calibrated Intensity):** Units in MJy/sr (MegaJanskys per steradian). Contains surface brightness.
2. **FLAGS (Data Quality Bitmask):**
   - Bit 0: Dead/unusable pixel
   - Bit 1: Cosmic ray hit
   - Bit 2: Saturated detector pixel
   - Bit 3: High non-linearity
   - Bit 4: Stray light / glint warning
   Pixels with fatal flags are masked or clearly designated in metadata displays.
3. **VARIANCE:** Per-pixel noise estimate. Used to establish detection thresholds ($S/N = I / \sqrt{V}$).
4. **ZODI:** Modeled zodiacal foreground light. Zodiacal light is bright in the mid-infrared (particularly 2–4 µm). For photometric comparisons across different times of year, changing solar elongation alters zodiacal brightness; differential analysis must account for this baseline shift.

## 3. Image Contrast Scaling (Display Only)
Scientific data is preserved unchanged in memory and metadata. For visual browser preview rendering:
- `asinh` (arcsinh) stretching is utilized as the default:
  $$I_{\text{scaled}} = \frac{\text{asinh}((I - I_{\text{min}}) / \beta)}{\text{asinh}((I_{\text{max}} - I_{\text{min}}) / \beta)}$$
  where $\beta$ is a softening factor preventing core blowout.
- Percentile clipping (e.g., 0.5% to 99.5%) eliminates cosmic ray outliers from dominating dynamic range.

## 4. Frame Registration & Differencing Eligibility
Two observations are eligible for scientific subtraction ($I_2 - I_1$) only if:
1. **Geometric Match:** Sky coverage overlap $> 80\%$.
2. **Spatial Registration:** Coordinate frames are reprojected onto an identical celestial pixel grid via WCS transformation.
3. **Spectral Compatibility:** Same detector band (D1–D6) and matching central filter wavelength within tolerance ($\Delta \lambda / \lambda < 0.05$).
