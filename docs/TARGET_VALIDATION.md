# Challenge target validation

The ten-file expanded local preview has two covered epochs for every preset. The original demo is a separate 22-file manifest with 18 named-target cutouts and four documentation examples. The requested coordinates are inside all 18 original named-target cutouts. The predicted exposure-epoch coordinates are inside only the four original RW Aurigae files.

## Moving-source preflight

The [broader D1–D6 screen](MOTION_MULTIDETECTOR.md) found zero eligible motion pairs among 18 selected. An alternate WISE DR1 D6 pair had 94.50% source-core passband overlap and fully usable cores. Its common sky pixels failed the existing half-pixel alignment gate even in wider cutouts. At the end of that search the exact D1–D5 lookups had no result. Subsequent lookups verified the sampled DR1 D3 and D5 maps.

The [calibration coverage audit](DETECTOR_CALIBRATION.md) verifies sampled DR1 D3 and D5 and sampled DR1/QR3 D6. D1, D2 and D4 remain unresolved. In the Epsilon Indi field, the D3 pair passed the core overlap check and failed native-pixel alignment. The D5 pair retained 207 of 225 field pixels for arithmetic. Ba and Bb remain unresolved. Neither the field comparison nor the catalog-predicted cores establish source identity, target flux, motion, or variability.

**No-go for a measured motion example in the tested sample.** `python scripts/study_motion_preflight.py` reproduces the local audit. Use `--fetch` for the bounded public catalog/SIA search and `--retry-failed` for one smaller retry of failed cutouts. The cache directory `data/cache/target_validation/motion_study/` holds the catalog query provenance, SIA URLs/results, FITS hashes, `motion_preflight.json` and `motion_pair_matrix.csv`. The matrix lists every tested pair's exposure IDs, releases, detector, UTC midpoints, baseline, propagated positions, mask counts, passband overlap and rejection. Empty observed-centroid, uncertainty and stationary-control entries mean those measurements were unavailable.

### Astrometry and gates

Start with the five staged pairs. Evaluate the previously cached distinct later WISE, RW Aurigae and R Draconis exposures against their first staged epochs. Then sample three additional infrared-bright high-proper-motion stars from the AllWISE motion survey and Gaia DR3. The additional sample is Kapteyn's Star (`4810594479418041856`, 8.64″/yr), Lalande 21185 (`762815470562110464`, 4.81″/yr), and Wolf 359 (`3864972938605115520`, 4.72″/yr). [Gaia high-proper-motion catalog comparison](https://www.cosmos.esa.int/web/gaia/iow_20250513) · [AllWISE motion survey](https://doi.org/10.1088/0004-637x/783/2/122)

Propagate Gaia J2016.0 positions with measured proper motion and radial velocity where present, then subtract Earth's barycentric vector using Astropy's built-in ephemeris. Barnard's Star and Epsilon Indi B also use the retrieved Gaia rows. Epsilon Indi B and Wolf 359 use zero radial velocity because those Gaia rows lack it. The Epsilon catalog prediction has RUWE 4.296 and remains an unresolved system reference. WISE 0855, RW Aurigae and R Draconis use the referenced J2000 proper motions and parallaxes below without perspective acceleration. This is a geometric geocentric parallax approximation for SPHEREx's low-Earth orbit. The spacecraft offset is below 0.00003″ at these parallaxes. The Blink marker retains the application's separately labeled catalog prediction. Neither prediction provides source association. [Gaia astrometric solution and epoch](https://arxiv.org/abs/2012.03380) · [SPHEREx orbit](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/spacecraft/)

Read the actual FITS IMAGE midpoint and native WCS. Use detector D6 and the checksum-verified CWAVE/CBAND maps matched by FITS provenance. Require distinct exposures at least 180 days apart for this bounded search, a fully contained and usable 2.5-pixel core in both epochs, and at least 90% worst nominal passband overlap across both source cores. Each interval is CWAVE ± CBAND/2, with overlap divided by the wider interval. Independently run the existing sky-aligned field comparator at its 90% per-pixel threshold. Both paths require finite brightness and positive variance and exclude all quality flags except SOURCE and FULLSAMPLE. No passband or mask rule was relaxed. [IRSA spectral calibration products](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-products/)

### Staged pairs

All observations below are D6. Dates are UTC exposure-midpoint dates. Core counts use the geocentric prediction, so the included pixel set can differ from the app's linear-propagation evidence table. The displacement is a catalog prediction including parallax.

| Preset | Exposure 1 | Exposure 2 | Baseline (days) | Predicted shift | Usable / total core pixels | Minimum source overlap / matched field pixels | Decision |
|---|---|---|---:|---:|---|---|---|
| Barnard's Star | DR1 `2025W33_2C_0321_2`, 2025-08-15 | QR3 `2026W33_2A_0594_4`, 2026-08-16 | 365.765 | 10.420″ | 10/18 → 11/19 | 0% / 0 | Masked and incompatible |
| Epsilon Indi B | DR1 `2025W18_1B_0081_2`, 2025-04-29 | QR3 `2026W39_1A_0276_2`, 2026-09-22 | 511.164 | 6.435″ | 20/20 → 19/20 | 0% / 0 | Masked and incompatible, unresolved |
| WISE 0855 | DR1 `2025W19_1B_0116_2`, 2025-05-05 | DR1 `2026W19_2A_0952_1`, 2026-05-09 | 369.232 | 8.238″ | 19/19 → 21/21 | 0% / 0 | Passband-incompatible, matching the previous API HTTP 422 |
| RW Aurigae | DR1 `2025W38_1A_0691_2`, 2025-09-17 | QR3 `2026W37_2A_0581_1`, 2026-09-13 | 360.374 | 0.0215″ | 14/21 → 16/20 | 0% / 0 | Masked and incompatible, unresolved |
| R Draconis | DR1 `2025W20_2D_0243_1`, 2025-05-16 | QR3 `2026W20_2A_0294_4`, 2026-05-16 | 364.411 | 0.0215″ | 0/21 → 0/19 | 0% / 0 | No usable core, incompatible |

### Bounded search results

- Thirteen additional distinct cached pairs met the baseline gate (two WISE, three RW Aurigae, eight R Draconis). All had zero valid aligned field pixels. The maximum nominal source-core overlap was 71.32%, in the R Draconis pair ending with `2026W24_1A_0125_1`, where both source cores had zero usable pixels.
- For each additional catalog star, query DR1 and QR3 within 0.012° of its J2026 prediction. Deduplicate D6 by exposure ID and sample up to four evenly spaced archive rows on each side of 2026-01-01 UTC. The DR1 queries returned 42 Kapteyn, 42 Lalande and 53 Wolf D6 rows. Each QR3 query ended with HTTP 502, which leaves QR3 coverage unresolved. Twenty cutout requests were selected. Sixteen returned FITS on the first request at 0.035° and four returned HTTP 503. The four smaller 0.025° retries returned FITS and passed D6 calibration preparation. [IRSA archive access](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/)
- Kapteyn's Star had eight cutouts spanning 170.768 days. None had a complete usable core, so its shorter baselines would still fail the mask gate. Lalande 21185 had eight cutouts and seven pairs at least 180 days apart. Wolf 359 had four cutouts and four such pairs. All four Wolf pairs were masked and had zero source overlap and zero valid aligned field pixels. The per-exposure cutoff and all request outcomes are preserved in the audit files.
- The sole passband-compatible source pair among the 29 was Lalande 21185 DR1 D6 `2025W17_4B_0475_1` (2025-04-27 21:04:28.496 UTC) and `2026W18_1A_0566_1` (2026-04-29 17:48:23.128 UTC). Across 366.864 days, Gaia predicts 4.840″ displacement (east −0.589″, north −4.804″). Source-core passband overlap is 93.95% and the existing field comparison retained 372 pixels. Only 0/21 and 2/19 core pixels are usable. The pair cannot support a source centroid.

No pair reached the stage for independent detections, a centroid uncertainty estimate or a nearby stationary-control measurement. No photometric amplitudes or unvalidated centroids were used. A defensible example needs two unmasked, same-passband images of a catalog-associated source, a validated centroid estimator at the source's sampling and S/N, and independently identified stationary sources nearby to measure registration residuals and uncertainty. The available Blink demo supports field inspection while this work remains open.

## Independent astrometry

Queried the [SIMBAD Harvard mirror](https://simbad.harvard.edu/simbad/sim-tap/) for catalog identifiers, right ascension, declination, proper motion, parallax, and original reference codes. SIMBAD stores positions in ICRS at epoch J2000. The two proper-motion columns below are μRA cos(Dec) and μDec in mas/year. Each position was propagated with a linear tangent-plane offset to the FITS `MJD-AVG` exposure midpoint and projected through the native celestial WCS. The model omits observer-specific parallax and perspective acceleration. Catalog parallaxes are under 0.55″ here, much smaller than the margin for the inside/outside decisions. [SIMBAD positional conventions](https://simbad.u-strasbg.fr/Pages/guide/ch15.htx)

| Target | Catalog identifier | ICRS J2000 RA, Dec (°) | Proper motion (mas/year) | Parallax (mas) | Reference |
|---|---|---:|---:|---:|---|
| Barnard’s Star | GJ 699 | 269.45207696, +4.69336497 | −801.551, +10362.394 | 546.9759 | [Gaia EDR3 via SIMBAD](https://simbad.harvard.edu/simbad/sim-id?Ident=GJ+699) |
| Epsilon Indi B | 2MASS J22041052−5646577 | 331.04414659, −56.78284420 | +3981.977, −2466.832 | 270.658 | [Gaia EDR3 via SIMBAD](https://simbad.u-strasbg.fr/simbad/sim-id?Ident=Epsilon+Indi+B), [resolved Ba/Bb astrometry](https://arxiv.org/abs/astro-ph/0309256) |
| WISE 0855 | WISEA J085510.74−071442.5 | 133.81890825, −7.24704800 | −8123.7, +673.2 | 439.0 | [Kirkpatrick et al. 2021 parallax and motion catalog](https://cdsarc.cds.unistra.fr/viz-bin/w/VizieR-3?-source=J%2FApJS%2F253%2F7%2Fplx) |
| RW Aurigae | V* RW Aur | 76.95652603, +30.40143817 | +7.23, −20.33 | 15.42 | [SIMBAD](https://simbad.harvard.edu/simbad/sim-id?Ident=RW+Aur), [van Leeuwen 2007 Hipparcos reduction](https://ui.adsabs.harvard.edu/abs/2007A%26A...474..653V/abstract) |
| R Draconis | V* R Dra | 248.16761083, +66.75497942 | −20.643, +6.149 | 1.2509 | [SIMBAD](https://simbad.harvard.edu/simbad/sim-id?Ident=R+Dra), [Gaia EDR3 catalog](https://cdsarc.cds.unistra.fr/viz-bin/ReadMe/I/350?format=html&tex=true) |

## Cached exposures

The pixel column shows the range of predicted coordinates across the two detectors in each row, with the first pixel at (0, 0). The allowed footprint is −0.5 ≤ x,y < 19.5. Separations are between the cache request and the propagated catalog position.

| Target and cached request (°) | Observation ID | FITS midpoint UTC | Release / detectors | Separation | Predicted pixel ranges x, y | Target coverage |
|---|---|---|---|---:|---|---|
| Barnard’s Star (269.452080, +4.693390) | 2025W33_2C_0321_1 | 2025-08-15 20:46:08.896 | DR1 / D3, D6 | 266.21″ | 3.55–4.05, −33.59 to −33.46 | Unavailable |
| Barnard’s Star | 2026W33_2A_0594_4 | 2026-08-16 15:09:19.681 | QR3 / D3, D6 | 276.62″ | 3.70–4.19, −35.06 to −34.82 | Unavailable |
| Epsilon Indi B (330.840000, −56.786000) | 2025W18_1B_0081_2 | 2025-04-29 01:34:17.378 | DR1 / D3, D6 | 505.94″ | −61.54 to −60.96, −28.61 | Unavailable |
| Epsilon Indi B | 2026W39_1A_0276_2 | 2026-09-22 05:29:51.176 | QR3 / D3, D6 | 511.83″ | 73.78–74.35, 57.10–57.16 | Unavailable |
| WISE 0855 (133.795129, −7.245147) | 2025W19_1B_0116_1 | 2025-05-05 16:49:00.018 | DR1 / D3, D6 | 121.38″ | −10.18 to −9.70, 13.93–14.31 | Unavailable |
| RW Aurigae (76.954200, +30.401400) | 2025W36_1A_0095_1 | 2025-09-01 10:05:15.025 | DR1 / D1, D4 | 7.42″ | 8.24–8.46, 9.29–9.52 | System location in field |
| RW Aurigae | 2026W36_1A_0476_1 | 2026-09-02 02:20:52.989 | QR3 / D1, D4 | 7.43″ | 8.55–8.65, 9.28–9.47 | System location in field |
| R Draconis (248.337500, +66.704200) | 2025W20_2D_0243_1 | 2025-05-16 22:57:21.196 | DR1 / D3, D6 | 303.50″ | 2.62–2.88, 58.73–58.84 | Unavailable |
| R Draconis | 2026W20_2A_0294_4 | 2026-05-16 08:49:02.889 | QR3 / D3, D6 | 303.52″ | 1.42–1.45, 58.07–58.58 | Unavailable |

The cached exposure baselines are 365.766 days for Barnard’s Star, 511.164 for Epsilon Indi B, 365.678 for RW Aurigae, and 364.411 for R Draconis. At the catalog proper motions those intervals correspond to about 10.41″, 6.56″, 0.022″, and 0.021″ of motion respectively, before parallax. Those are predictions from the reference astrometry. WISE 0855 has one cached exposure time across its two detectors, so no motion baseline exists.

## Photometry and variability

Ran the existing 3-pixel aperture and 4.5–7-pixel source-masked annulus on each cached requested coordinate with the FITS masks and variance layers. Sixteen apertures were unavailable because the source aperture had invalid or masked pixels or the annulus had no valid source-free pixels. The remaining two were WISE field samples with propagated variance. The catalog projection places WISE 0855 outside both cutouts, so those values cannot be attributed to the brown dwarf.

Recentered the four RW Aurigae apertures on the predicted system position. The DR1 D1 result had no acceptable background annulus. The other three had invalid or masked aperture pixels. All 18 files include an ePSF extension, but these aperture runs did not fit it or apply a point-source aperture correction. The app’s variance estimate covers aperture samples and an approximate background term. It does not account for correlated calibration errors, PSF changes, or unresolved blending. The ≈1.5″ A/B separation is below a SPHEREx native pixel. Independent optical and near-IR studies document variability in RW Aurigae, while these SPHEREx observations provide no usable photometric confirmation. [Resolved multiwavelength study](https://doi.org/10.1051/0004-6361/201527237)

These coverage results show where the cached data can be used. Outside-footprint cases are unavailable. Positions inside a footprint still require source association and validated photometry before claiming motion or variability.

## Corrected archive samples staged for review

Queried IRSA DR1 and QR3 at the catalog positions propagated to representative years 2025.60 and 2026.65. Each returned D6 cutout was requested at 0.035°, reprojected at its exact exposure midpoint, and checked for coverage. Nine cutouts contain the predicted position within half a pixel along each axis of the nominal cutout center. The raw cutouts and full evidence are under `data/cache/target_validation/`. The strict builder audit copied all nine to `data/cache/demo_refresh/` with zero warnings or failures. The original demonstration manifest still points to its original FITS files. [IRSA archive access](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/)

| Target | DR1 D6 | QR3 D6 | Aperture result at predicted position |
|---|---|---|---|
| Barnard’s Star | 2025W33_2C_0321_2, 2025-08-15 | 2026W33_2A_0594_4, 2026-08-16 | Both unavailable |
| Epsilon Indi B | 2025W18_1B_0081_2, 2025-04-29 | 2026W39_1A_0276_2, 2026-09-22 | DR1 aperture value with variance estimate. QR3 unavailable. The Ba/Bb pair is unresolved at this sampling. |
| WISE 0855 | 2025W19_1B_0116_2, 2025-05-05 | No D6 rows from this query | DR1 aperture value with variance estimate. Another date is required for a temporal comparison. |
| RW Aurigae | 2025W38_1A_0691_2, 2025-09-17 | 2026W37_2A_0581_1, 2026-09-13 | Both unavailable |
| R Draconis | 2025W20_2D_0243_1, 2025-05-16 | 2026W20_2A_0294_4, 2026-05-16 | Both unavailable |

The two staged aperture values are measurements at predicted coordinates. Association with the named source, PSF effects, and comparison across bands or epochs remain unverified.

## Re-audit and expanded preview

The reference positions and J2000 epoch are in the astrometry table above. The rows below were recomputed from the FITS IMAGE extension using its UTC `MJD-AVG` and native WCS. Linear proper motion is applied without observer parallax or perspective acceleration. WCS pixels are zero-based. None of these rows has an independently established source association or target photometry. An aperture sample is a field measurement at the predicted coordinate.

| Target | Observation | Release / detector | MJD midpoint (UTC) | Predicted ICRS (deg) | FITS footprint (x, y) | Aperture |
|---|---|---|---:|---|---|---|
| Barnard's Star | 2025W33_2C_0321_2 | DR1 / D6 | 60902.86687298 | 269.4463524, +4.7671159 | Inside (9.33, 9.52) | Unavailable |
| Barnard's Star | 2026W33_2A_0594_4 | QR3 / D6 | 61268.63147779 | 269.4461286, +4.7699984 | Inside (9.70, 9.18) | Unavailable |
| Epsilon Indi B | 2025W18_1B_0081_2 | DR1 / D6 | 60794.06547892 | 331.0953024, -56.8001865 | Inside (9.46, 9.39) | Aperture sample only |
| Epsilon Indi B | 2026W39_1A_0276_2 | QR3 / D6 | 61305.22906453 | 331.0981309, -56.8011443 | Inside (9.35, 9.16) | Unavailable |
| WISE 0855 | 2025W19_1B_0116_2 | DR1 / D6 | 60800.70218691 | 133.7612618, -7.2423054 | Inside (9.64, 9.39) | Aperture sample only |
| WISE 0855 | 2026W19_2A_0952_1 | DR1 / D6 | 61169.93387466 | 133.7589623, -7.2421161 | Inside (9.94, 9.90) | Aperture sample only |
| RW Aurigae | 2025W38_1A_0691_2 | DR1 / D6 | 60935.92409930 | 76.9565859, +30.4012930 | Inside (9.98, 9.80) | Unavailable |
| RW Aurigae | 2026W37_2A_0581_1 | QR3 / D6 | 61296.29825675 | 76.9565882, +30.4012874 | Inside (9.23, 9.71) | Unavailable |
| R Draconis | 2025W20_2D_0243_1 | DR1 / D6 | 60811.95649533 | 248.1672422, +66.7550228 | Inside (9.88, 9.84) | Unavailable |
| R Draconis | 2026W20_2A_0294_4 | QR3 / D6 | 61176.36739455 | 248.1672277, +66.7550245 | Inside (9.45, 9.07) | Unavailable |

- **Barnard's Star** has 2 distinct covered epochs separated by 365.765 days. Compare field images visually.
- **Epsilon Indi B** has 2 distinct covered epochs separated by 511.164 days. Compare field images visually.
- **WISE 0855** has two covered DR1 epochs in the expanded preview, 369.232 days apart. Show both fields. The API rejected calibrated subtraction and pair co-addition with HTTP 422 because no aligned, unmasked samples meet the passband overlap requirement. The earlier nine-file stage has one WISE exposure.
- **RW Aurigae** has 2 distinct covered epochs separated by 360.374 days. Compare field images visually.
- **R Draconis** has 2 distinct covered epochs separated by 364.411 days. Compare field images visually.

Each covered epoch supports position and field inspection. No target motion, variability, or validated target flux is established. The original manifest again yielded 14 outside and four inside.

### Additional archive requests

- Three IRSA SIA DR1 searches used radius 0.001° at the propagated WISE 0855 positions for 2025.35, 2025.85, and 2026.25. Each returned 258 rows across D1–D6. Two QR3 searches at (133.75880987°, −7.24210352°) and (133.75787724°, −7.24202672°) returned zero rows. These are the tested positions and releases.
- Of four D6 cutout requests for later WISE exposures, one returned HTTP 503 and three contained the predicted source position in their native FITS WCS. All three failed the 90% CWAVE/CBAND passband check against the 2025 file. Two produced field aperture samples. The third had invalid or masked aperture pixels.
- Fifteen additional D6 cutouts covered the predicted positions for RW Aurigae and R Draconis. All 15 had unavailable photometry after quality and aperture checks. None passed the tested calibrated pairing against its corresponding staged DR1 reference. One additional RW Aurigae request returned HTTP 503. This was a bounded D6 sample.
- Exact SIA URLs are in `data/cache/target_validation/additional_search.json`. FITS requests, UTC MJD, projected pixels, aperture results and compatibility outcomes are in `data/cache/target_validation/additional_epochs/evidence.json`. The expanded manifest at `data/cache/demo_multiepoch/demo_dataset.json` passed ten of ten checks with zero warnings. Both earlier manifests remain available.

## Source photometry feasibility

The [real-source control follow-up](D6_CONTROL_VALIDATION.md) evaluated six wide D6 frames in three fields. The strict catalog screen yielded zero eligible source or blank fits. The prototype matched the IRSA tutorial's native-stamp numerical output in all 120 trials. Absolute flux and uncertainty calibration remain unvalidated.

The inputs support a future forced-photometry study. The current workflow cannot publish validated target fluxes from these cutouts. IRSA’s documented method uses the local ePSF, a scene model, variance and flag planes, a fitted background, a pixel solid-angle map, and empirical uncertainty calibration. The ten local cutouts have no verified deblending or independent real-source recovery check. An aperture sample, even at the propagated position, does not supply those checks. [IRSA Explanatory Supplement, §3.3](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf)

The ten D6 files have 20 × 20 IMAGE and VARIANCE planes in MJy/sr and (MJy/sr)², native celestial WCS (about 6.15″ per pixel), FLAGS, ZODI, EPSF, WCS-WAVE, and a UTC exposure midpoint. Between 393 and 400 variance samples per image were finite and positive before masking. These are single exposures. Cube NHITS is a separate product and cannot replace exposure variance. D6 CWAVE/CBAND is available through the verified spectral calibration used earlier. The zone CWAVE values below describe the ePSF calibration zone and do not replace the pixel-level spectral calibration.

The EPSF table supplies 441 zones per file, each with a 33 × 33 template sampled five times finer than the detector grid. The selected templates sum to 1 at the stored sampling and contain signed samples. The table supplies contributing star counts and effective area, without a template uncertainty plane. A native model must account for subpixel phase and normalization. The image flux conversion requires the local pixel solid angle rather than the nominal 6.15″ scale. [IRSA ePSF tutorial](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/) · [Calibration product guide](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/)

| Exposure | ePSF bin x, y / stars | Zone CWAVE (µm) | Valid core pixels within 2.5 pixels | Source-excluded annulus pixels | Current aperture result |
|---|---:|---:|---:|---:|---|
| Barnard’s Star DR1 | 16, 1 / 441 | 4.9600 | 11/19 | 0 | Overflow/transient/bloom at aperture |
| Barnard’s Star QR3 | 6, 19 / 470 | 4.4383 | 12/20 | 0 | Overflow/ramp/transient/bloom at aperture |
| Epsilon Indi B DR1 | 8, 19 / 467 | 4.4358 | 19/19 | 45 | Field sample only. Ba/Bb unresolved. |
| Epsilon Indi B QR3 | 20, 17 / 572 | 4.5056 | 19/20 | 53 | Overflow/ramp/persistence at aperture |
| WISE 0855 DR1 2025 | 3, 0 / 465 | 4.9927 | 20/20 | 53 | Field sample only |
| RW Aurigae DR1 | 14, 16 / 504 | 4.5199 | 14/21 | 0 | Overflow/ramp/transient/bloom at aperture. A/B unresolved. |
| RW Aurigae QR3 | 15, 5 / 407 | 4.8376 | 16/20 | 0 | Overflow/halo at aperture. A/B unresolved. |
| R Draconis DR1 | 18, 20 / 492 | 4.4185 | 0/21 | 0 | No usable core |
| R Draconis QR3 | 17, 17 / 463 | 4.4972 | 0/19 | 0 | No usable core |
| WISE 0855 DR1 2026 | 3, 2 / 367 | 4.9314 | 21/21 | 53 | Field sample only |

These counts were verified against the frame API with the strict evidence mask. Only SOURCE and FULLSAMPLE are informational. The check also requires finite brightness, finite positive variance, and exclusion of SOURCE pixels from the background annulus. All ten target-photometry statuses are unavailable. Three apertures pass field checks only and seven are unavailable.

As an off-source control we used pixel (15, 15) in WISE frame `2026W19_2A_0952_1`, 7.18 native pixels from the predicted target. It had no SOURCE flag in the 3-pixel aperture. A 20″ cone in the 2MASS PSC at ICRS (133.764675164°, −7.253146908°) returned no catalog rows via VizieR. The legacy aperture routine returned 0.3957 ± 0.5015 in its native surface-brightness sum convention, S/N 0.79. The background annulus crosses the image edge and the control is only 2MASS-screened. It illustrates that a returned aperture value alone does not establish a detection. It does not validate an ePSF estimator. [2MASS control query](https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?-source=II%2F246%2Fout&-c=133.764675164+-7.253146908&-c.rs=20&-out=RAJ2000%2CDEJ2000%2C2MASS%2CKmag)

### Forced-fit study acceptance criteria

Before evaluating target fits, require matched and verified exposure calibration, a complete unmasked 2.5-pixel core, support within the cutout, enough source-excluded background for a fit, and a known or explicitly modeled source scene. For validation, use at least 20 independent clear background patches and 20 independently associated field-star measurements with matched passbands and credible reference fluxes. The minimum sample is intended to expose gross bias and uncertainty errors. It is insufficient by itself to establish a 5σ false-positive rate. Repeat subpixel phases and test injected signals at nominal S/N 3, 5, 10 and 20. For each S/N ≥5 bin require median signed relative recovery error ≤10%, normalized residual scatter in [0.8, 1.2], and fewer than 10% failed fits on eligible inputs. For real stars require median relative flux residual ≤10% and normalized residual scatter in [0.8, 1.2] including the reference errors. For blank controls require centered normalized amplitudes (absolute mean ≤0.25) with scatter in [0.8, 1.2] and no formal ≥5σ positives. Repeating injections on the same background does not increase the number of independent controls.

A named-target claim would also need independent source association, nominal S/N ≥5 after empirical uncertainty calibration, a fit residual check (χ² tail probability ≥0.01), and flux stability within 10% for the tested representative centroid and background perturbations. The fit must account for contaminating neighbors. RW Aurigae and Epsilon Indi B can only be tested as unresolved systems in these frames. These are study gates. They do not define mission catalog quality grades.

### Isolated D6 prototype and product checks

Run `python scripts/study_epsf_photometry.py` from the repository root with the archived products in `data/cache/target_validation/epsf_study/`. Local `forced_fit_diagnostics.json` records the masks, projected positions, nominal residual statistics and control outcomes. It omits named-target fluxes. The analysis does not write to the preview manifest or serve results through the application.

- Verified all ten staged IMAGE, VARIANCE, FLAGS, EPSF and WCS-WAVE extensions. Each WCS-WAVE table stores a 9 × 9 grid with two values at each node. The matched detector CWAVE/CBAND arrays, rather than that visualization table, show a 0.00103–0.00167 µm center-wavelength span within the 2.5-pixel cores and 0.03383–0.03851 µm median bandwidths. The prototype uses one amplitude per exposure and does not fit source color across those pixels. [IRSA calibration product guide](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/)
- The D6 SAPM v3 release FITS has a 2040 × 2040 float plane, `DETCOORD=sky`, and `BUNIT=arcsec2`. Its MD5 is `c01934ebcdd287f96e94c2af6ba9be26`. The zero-based cutout-to-detector offset is `1 − CRPIXnA` with identity mapping. The area at the nearest native target pixel spans 37.5766–38.4013 arcsec². Multiply pixel surface brightness in MJy/sr by `area_arcsec² × (π/648000)² × 10¹²` to obtain pixel µJy. The fit applies the inverse factor to each unit-flux template pixel and retains the variance weights in brightness units. This is the release detector map. An exposure-specific provenance match was not established. The supplement describes the map as a photometry input outside the Level 2 pipeline. [IRSA SAPM artifact](https://nasa-irsa-spherex.s3.amazonaws.com/dr1/solid_angle_pixel_map/cal-sapm-v3-2026-191/6/solid_angle_pixel_map_D6_spx_cal-sapm-v3-2026-191.fits) · [Explanatory Supplement, §3.3 and Appendix A](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf)
- Selected the unique detector zone containing each position. Evaluated the 5× sampled, 33 × 33 effective response by cubic interpolation at native pixel centers at the predicted subpixel phase, preserving signed lobes and applying zero outside the tabulated support. Normalized the full native stamp before masking. The tutorial's code evaluates the already-effective response at native centers, so the prototype performs no second pixel convolution. [IRSA ePSF tutorial, §7.2](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/#72-using-the-spherex-epsf-in-forward-modeling-eg-tractor) · [Photutils ImagePSF implementation](https://photutils.readthedocs.io/en/stable/_modules/photutils/psf/image_models.html)
- Used diagonal inverse-variance weights, an unconstrained signed amplitude and a simultaneously fitted constant background inside 4.5 pixels. Required a complete core and at least 20 valid source-excluded background pixels from 3.3–4.5 pixels, with at least two per quadrant. All flags except SOURCE and FULLSAMPLE are excluded, including unknown flags. SOURCE is also excluded from the background. Refit with a plane and four ±0.2-pixel axis shifts. The prototype does not recreate the mission's full-frame background subtraction or joint prior scene. The mission supplement describes an empirical 3% fractional term added in quadrature for its catalog uncertainties. That term cannot substitute for validating this prototype's uncertainty, noise correlations and ePSF mismatch. [Explanatory Supplement, §3.3](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf)

### Control results

- Three real staged patches passed the detector's SOURCE screen. Seven of 15 attempted phases passed the prototype geometry checks, giving 28 injected fits across nominal S/N 3, 5, 10 and 20; eight phases hit the edge gate before a fit. In each S/N bin the normalized error scatter was 0.608, outside the 0.8–1.2 gate. Median signed recovery error was +1.28%, +0.77%, +0.38% and +0.19%. The identical-template incremental recovery agreed to machine precision. The median absolute incremental bias after a 0.2-pixel displacement was 6.88% across eligible shifts. The tested gradient changed an S/N 5 injected amplitude by up to 6.09%. These repeated trials share background noise and do not simulate extra source shot noise. A later independent 33″ Gaia/AllWISE screen found catalog sources near all three patches, so they are contamination and algebra checks rather than validated nulls. The earlier WISE (15,15) control also has one AllWISE and two Gaia sources within 20″ despite having no 2MASS entries. [Gaia DR3](https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=I/355/gaiadr3) · [AllWISE](https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=II/328/allwise)
- In the staged exposures, 133 Gaia positions with proper motion projected inside the fields and at least four pixels from the named predictions. None passed geometry: 88 hit the cutout edge, 34 lacked sufficient background and 11 had a masked core. An additional 93 × 94 cutout from the same 2026 WISE D6 exposure supported a wider independent catalog screen. Zero of 81 disjoint grid patches passed the Gaia, AllWISE and SOURCE exclusions. Of 14 isolated Gaia/AllWISE crossmatches selected by position and W2 quality, four passed geometry. One, Gaia DR3 `5756943312809452160` / AllWISE `J085511.95−071854.0`, gave formal S/N 6.00 with reduced χ² 1.39 and nominal tail probability 0.023. This is one independent-position recovery. Its broad W2 measurement gives no matched D6 reference flux. The other three fits returned formal S/N 2.63, 0.82 and 0.64. The 20-star matched-flux gate and the 20-blank uncertainty gate remain unmet. Query URLs and candidate results are in the local diagnostics.

### Named exposure results

Pixels are zero-based. The background and fit-pixel columns count eligible samples before rejecting incomplete cores or backgrounds. Dashes mean the fit did not run. All ten have an external catalog prediction and no independently associated SPHEREx detection; all ten are ineligible as target measurements. The WISE S/N and χ² values are formal diagnostics under diagonal noise assumptions.

| Target / epoch | Predicted pixel | Usable / total core | Background / fit pixels | Fit status | Formal S/N | Reduced χ² / tail probability | Residual RMS (MJy/sr) |
|---|---:|---:|---:|---|---:|---:|---:|
| Barnard’s Star 2025 | 9.33, 9.52 | 11/19 | 0/24 | Masked core | — | — | — |
| Barnard’s Star 2026 | 9.70, 9.18 | 12/20 | 0/27 | Masked core | — | — | — |
| Epsilon Indi B 2025 | 9.46, 9.39 | 19/19 | 0/32 | Insufficient local background; unresolved | — | — | — |
| Epsilon Indi B 2026 | 9.35, 9.16 | 19/20 | 0/34 | Masked core; unresolved | — | — | — |
| WISE 0855 2025 | 9.64, 9.39 | 20/20 | 25/57 | Experimental fit | 2.06 | 0.610 / 0.990 | 0.0568 |
| WISE 0855 2026 | 9.94, 9.90 | 21/21 | 22/59 | Experimental fit | 3.51 | 1.126 / 0.239 | 0.0740 |
| RW Aurigae 2025 | 9.98, 9.80 | 14/21 | 0/28 | Masked core; unresolved | — | — | — |
| RW Aurigae 2026 | 9.23, 9.71 | 16/20 | 0/28 | Masked core; unresolved | — | — | — |
| R Draconis 2025 | 9.88, 9.84 | 0/21 | 0/0 | No usable core | — | — | — |
| R Draconis 2026 | 9.45, 9.07 | 0/19 | 0/0 | No usable core | — | — | — |

The two WISE fits shifted by up to 20.0% and 15.4% of their experimental amplitudes under the four centroid perturbations. A planar background changed them by 0.3% and 1.7%, respectively. Both are below the nominal S/N gate and above the centroid sensitivity limit. The WISE pair still fails the calibrated passband requirement. **No-go for publishing target flux, detection, motion or variability.** Next steps require an exposure-matched area provenance check, a broader set of real blank and matched spectral standards, and larger scenes with epoch-aware source priors and empirical repeated-measurement scatter.
