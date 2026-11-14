# SPHEREx Discovery — Official Challenge Target Analysis

The NASA Space Apps Challenge 2026 specifies 5 official test targets representing diverse astrophysical phenomena. SPHEREx Discovery includes full pre-configured presets, verified FITS cutouts, and specialized analytical workflows for each.

---

## 1. Barnard's Star (Gl 699)
- **Target Type:** High Proper Motion M-type Red Dwarf (M4.0V)
- **Coordinates (J2000):**
  - Decimal: $\alpha = 269.45208^\circ$, $\delta = +4.69339^\circ$
  - Sexagesimal: `17h57m48.50s +04d41m36.20s`
- **Distance:** 5.96 light-years (2nd closest stellar system to the Sun)
- **Astrophysical Signature:** Fastest proper motion of any known star ($\mu = 10.33\,\text{arcsec/year}$).
- **SPHEREx Observations:** DR1 (August 2025) and QR3 (August 2026) in Detectors D1, D3, D4.
- **Expected Differential Signature:**
  - Clear **dipole pattern**: dark negative residual at Epoch 1 location, bright positive spot at Epoch 2 location.
  - Calculated angular displacement across 1-year baseline: $\approx 10.3\,\text{arcsec}$ ($\approx 1.66$ pixels at $6.2''$/pix).
  - Detected position angle: $\approx 355.6^\circ$ (moving almost directly North).

---

## 2. WISE 0855-0714 (WISEA J085510.83-071442.5)
- **Target Type:** Sub-stellar Y-type Brown Dwarf
- **Coordinates (J2000):**
  - Decimal: $\alpha = 133.79513^\circ$, $\delta = -7.24515^\circ$
  - Sexagesimal: `08h55m10.83s -07d14m42.54s`
- **Distance:** 7.27 light-years (4th closest system to the Sun)
- **Effective Temperature:** $\approx 250\,\text{K}$ (sub-freezing, colder than water ice!)
- **Astrophysical Signature:** Purely infrared emission. Completely undetectable in optical survey images ($G > 24$), but prominent in SPHEREx mid-IR channels (Detectors D4 and D5, $2.4 - 4.5\,\mu\text{m}$). Exhibits very high proper motion ($\approx 8.1\,\text{arcsec/year}$).
- **Expected Differential Signature:** Strong mid-infrared dipole showing spatial displacement between DR1 and QR3, with zero signal in D1/D2 optical bands.

---

## 3. RW Aurigae (HD 32770)
- **Target Type:** Classical T Tauri Young Stellar Object (YSO) Binary System
- **Coordinates (J2000):**
  - Decimal: $\alpha = 76.95420^\circ$, $\delta = +30.40140^\circ$
  - Sexagesimal: `05h07m49.01s +30d24m05.04s`
- **Distance:** $\approx 530$ light-years (Taurus-Auriga Star Forming Region)
- **Astrophysical Signature:** Cataclysmic photometric dimming events (up to 3 magnitudes) caused by tidal disruptions and dust occultations within the protoplanetary circumstellar disk.
- **SPHEREx Observations:** Multi-epoch monitoring across Detectors D1–D4.
- **Expected Differential Signature:**
  - **Stationary monopole**: centroid position remains constant ($\Delta x \approx 0$).
  - Dramatic flux amplitude variations in the aperture light curve dock ($\Delta F > 20\,\text{MJy/sr}$, variability index $> 0.35$).

---

## 4. R Draconis (HD 149214)
- **Target Type:** Mira-Type Pulsating Asymptotic Giant Branch (AGB) Red Giant
- **Coordinates (J2000):**
  - Decimal: $\alpha = 248.33750^\circ$, $\delta = +66.70420^\circ$
  - Sexagesimal: `16h33m21.00s +66d42m15.12s`
- **Pulsation Period:** $245.6$ days
- **Astrophysical Signature:** Periodic radial pulsations causing massive surface brightness changes between optical and near-infrared wavelengths as the stellar photosphere expands and contracts.
- **SPHEREx Observations:** Level 2 time series spanning multiple pulsation phases.
- **Expected Differential Signature:** Concentric monopole flux oscillation centered on the target coordinate, clearly tracked in the Light Curve telemetry chart.

---

## 5. Epsilon Indi B (HD 209100 B)
- **Target Type:** Nearby Binary Brown Dwarf System (T1 + T6 dwarfs)
- **Coordinates (J2000):**
  - Decimal: $\alpha = 330.84000^\circ$, $\delta = -56.78600^\circ$
  - Sexagesimal: `22h03m21.60s -56d47m09.60s`
- **Distance:** 11.8 light-years
- **Astrophysical Signature:** Combined orbital motion ($P \approx 15\,\text{years}$) and high annual proper motion ($\mu \approx 4.7\,\text{arcsec/year}$).
- **Expected Differential Signature:** Dual vector displacement combining systemic proper motion with mutual binary orbital progression.
