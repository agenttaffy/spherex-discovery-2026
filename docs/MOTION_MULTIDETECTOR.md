# D1–D6 moving-source archive screen

**No-go for a measured motion demo in this sample.** Zero of 18 selected pairs passed the combined archive, native core, provenance, and comparison gates. This bounds the conclusion to the selected archive sample and the calibration available during the run.

At the time of the screen, only the sampled D6 map had an exact UUID link. The initial D6 follow-up reran three pairs and a positive arithmetic control. The [later calibration checks](DETECTOR_CALIBRATION.md) verified sampled DR1 D3 and D5. The D3 field pair failed native-pixel alignment, and the D5 field pair retained 207 of 225 pixels for arithmetic. Neither follow-up established a motion measurement.

## Search and selection

The sample includes the five challenge objects and four catalog-selected infrared sources with large proper motions. The supplemental sources were Kapteyn's Star (Gaia DR3 `4810594479418041856`), Lalande 21185 (`762815470562110464`), Wolf 359 (`3864972938605115520`), and Teegarden's Star (`35227046884571776`). Teegarden's Star has Gaia proper motion of about 5.12″/yr and a catalog Ks magnitude of 7.585. Use the preserved Gaia J2016.0 reference data and the existing challenge catalog references. Propagate proper motion, measured radial velocity when available, and geocentric parallax to the FITS midpoint. Gaia entries without radial velocity use zero for the perspective term. [Gaia high-proper-motion comparison](https://www.cosmos.esa.int/web/gaia/iow_20250513) · [Teegarden infrared photometry](https://exoplanetarchive.ipac.caltech.edu/overview/teegarden) · [Previous astrometry method and sources](TARGET_VALIDATION.md#astrometry-and-gates)

Query one 0.012° cone centered on the J2026 predicted position for each source and release. All 18 SIA queries returned HTTP 200 and yielded 3,299 science metadata rows across D1–D6 (2,511 DR1 and 788 QR3, before per-source exposure deduplication). This resolves the earlier HTTP 502 for the three previous supplemental sources. The WISE 0855 QR3 cone returned zero rows. This was the wide survey and a single cone per source and release. [IRSA SIA access and release definitions](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/)

Rank one candidate per source and detector using distinct exposures 180–550 days apart. The metadata ranking minimizes the difference between approximate fractional locations in the SIA footprint polygons plus the deviation from a one-year baseline, divided by 1,000 days. It serves as a retrieval heuristic. Sample at most three pairs per detector while covering all nine sources. This produced 54 metadata candidates and selected 18. Fetch 36 FITS cutouts at 0.035° centered on the predicted source. Retry failures once at 0.025°. Fourteen first requests and eight retries returned HTTP 503. The final result was 28 usable FITS downloads and eight unavailable. A pair is counted only once even if a wider sample of the same exposures is tested.

Inspect native FITS WCS, variance and documented integer flag planes at the geometric source prediction. Require a complete, contained 2.5-pixel core and use only finite brightness, finite positive variance and allowable flags (SOURCE/FULLSAMPLE). The exact detector calibration must match the science FITS plane UUID and the archive checksum. Require at least 90% worst nominal CWAVE/CBAND overlap across source cores, plus the existing 90% per-pixel sky-aligned comparison with a 0.5-native-pixel distance gate. The prototype never substitutes the WCS-WAVE visualization grid for detector calibration. [Spectral calibration product documentation](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/)

## Pair results

| Detector | DR1–DR1 selected | DR1–QR3 selected | Both FITS returned | Source overlap evaluated | Passed all gates |
|---|---:|---:|---:|---:|---:|
| D1 | 1 | 2 | 1 | 0 | 0 |
| D2 | 2 | 1 | 1 | 0 | 0 |
| D3 | 2 | 1 | 2 | 0 | 0 |
| D4 | 1 | 2 | 1 | 0 | 0 |
| D5 | 2 | 1 | 2 | 0 | 0 |
| D6 | 2 | 1 | 3 | 3 | 0 |
| **Total** | **10** | **8** | **10** | **3** | **0** |

- **WISE 0855 alternate DR1 D6 pair** `2025W19_1B_0138_1` and `2026W19_2A_0651_1`. Gaia-independent catalog astrometry predicts an 8.219″ shift across 368.360 days. Both cores have 21/21 usable pixels and 94.50% worst nominal passband overlap. The small FITS pair had zero accepted aligned pixels. Two 0.12° cutouts at a common sky center increased the common footprint to 4,900 pixels. The distance to the nearest native comparison pixel ranged from 0.50169 to 0.50484 pixel, so zero met the existing half-pixel gate. This alternate pair differs from the original staged WISE pair, which was passband-incompatible.
- **Epsilon Indi B** DR1 D3 `2025W18_1B_0091_2` and `2026W18_1A_0444_1` have 20/20 and 21/21 usable core pixels. DR1 D5 `2025W17_4B_0027_3` and `2026W17_2A_0308_3` have 19/19 in both. Their expected shifts are about 4.681″ and 4.680″. The initial screen lacked exact D3/D5 spectral calibration. See the later checks linked above. The D6 pair has 96.14% worst nominal source-core overlap, but 19/20 and 17/18 usable core pixels and zero accepted aligned field pixels. The catalog prediction represents an unresolved system. An eventual measurement would need scene and photocenter validation.
- **Barnard's Star** DR1/QR3 D6 `2025W33_2C_0321_1` and `2026W34_1A_0176_2` have 59.42% worst nominal overlap, 4/16 and 9/20 usable core pixels, and zero accepted aligned field pixels. **Teegarden's Star** DR1/QR3 D4 `2025W31_2A_0328_4` and `2026W31_2A_0448_4` have 15/20 and 12/16 usable core pixels. Exact D4 passband overlap remained unavailable.

The archive TAP synchronous lookups for D1–D5 timed out. A broad asynchronous job (`28345951`) was cancelled by the service. The exact UUID batch (`28346199`) and the separate D3 (`28346496`) and D5 (`28346499`) jobs remained queued at the final check. The local audit retains the errors and the exact UUIDs from the science headers. The existing checksum-verified D6 artifact matched all six D6 science headers. At the time, D1–D5 overlap was unknown. D1, D2 and D4 still lack verified mappings for the sampled cases. No pair reached source association, independent centroid or stationary-star evaluation. The audit produced no measured displacement, uncertainty or control residual. Earlier injection photometry provides no centroid validation for these detector/release pairs.

## Reproduce and extend

Run `python scripts/study_motion_multidetector.py --wide-wise` from the repository root using the preserved files in `data/cache/target_validation/motion_multidetector/`. The exact metadata queries, Gaia rows, selection, FITS URLs and SHA-256 hashes, and per-pair decisions are in `sia.json`, `catalog.json`, `selection.json`, `cutouts.json`, `results.json`, `pair_matrix.csv` and `wise-wide-check.json`. Add `--refresh-sia` to rerun metadata only, `--fetch` to retrieve the new selection, and `--calibrate` to recheck missing calibration for saved FITS. The previously verified D6 calibration lives in `data/cache/`.

A viable motion test needs complete masks, matched passbands, usable local alignment and independent source association in both epochs. The calibrated D5 field result establishes arithmetic compatibility on its retained pixels. Epsilon Indi Ba and Bb remain unresolved. Any future centroid claim requires detector/release-matched injection recovery, clean catalog stars and nearby stationary controls to measure registration and total positional uncertainty. The existing Blink workflow remains field inspection with its current caveat.
