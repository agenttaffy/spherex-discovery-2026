# SPHEREx Discovery challenge traceability

| Requirement | Status | Evidence and limits |
|---|---|---|
| REQ-01 Coordinate entry | Implemented and verified | Decimal and sexagesimal input, coordinate validation, and RA wrapping are covered by coordinate tests. |
| REQ-02 IRSA search and image viewer | Implemented; live search currently unreliable | SIA searches have returned errors during the current IRSA outage. Historical search records and cached images are labeled; independently checked public-cloud cutouts now provide image pixels, with IRSA cutouts as a fallback. Search availability may change. |
| REQ-03 Epoch playback | Implemented and verified | Timeline offers stepping, looping, and 1, 2, or 4 frames per second. Network latency can affect uncached playback. |
| REQ-04 Change inspection | Field comparison verified | Blink supports dated field inspection. The Epsilon Indi D5 field difference and co-add retained 207/225 pixels; a R Draconis D6 field difference retained 169/529, and an independent real three-exposure D6 co-add retained 123/529. The D6 deep-field control retained 378/400. The staged WISE pair returned HTTP 422. The field checks establish no target motion. [Calibration evidence](DETECTOR_CALIBRATION.md) |
| REQ-05 Five targets | Verified for epoch-dependent footprint coverage | The optional ten-file preview has two covered epochs for each target. Each frame displays the predicted coordinate from its FITS exposure midpoint. Footprint coverage supports field inspection. Source associations remain unconfirmed. |
| REQ-06 Infrared bands | Verified at 20 coordinates on six DR1 tiles | D1–D6 are detector arrays. The former synthetic 102-point continuum was removed. Spectral Cube shows actual DR1 channels, hit counts, flags and gaps in a co-added sky-pixel sample. [Audit results](#dr1-cube-coverage) |
| REQ-07 Metadata and flags | Implemented and verified | Inspector displays observation metadata, FITS-derived statistics and quality information, and provenance when available. |
| REQ-08 Shareable coordinates | Implemented | Share links carry search state and observation selection. |
| REQ-09 Candidate motion | Automatic measurement unavailable | Blink and difference permit visual inspection. A motion claim requires validated source identity, passband compatibility, a suitable baseline, and astrometric uncertainties. |
| REQ-10 Light curves and target photometry | Field diagnostics available, target flux unavailable | The staged preview has three field-sample-only apertures and seven unavailable apertures. All ten lack validated source association and target flux. Variability remains unconfirmed. |
| REQ-11 Catalog overlay | Implemented and verified for display | Live Gaia DR3 sources from VizieR are projected through the cutout WCS. Catalog positions start at J2016.0; markers approximately shift known proper motions to the exposure midpoint. Parallax and radial motion are not modeled, and neither projection nor proximity proves identity. The search is limited to 200 bright sources. |
| REQ-12 Report export | Implemented, independent science validation pending | Markdown and JSON carry available evidence and limitations. |
| REQ-13 Guided tour | Implemented | Educational walkthrough is available in the interface. |

See [test evidence](../TEST_RESULTS.md) and the [demo audit](DEMO_DATA_AUDIT.md).

## DR1 cube coverage

These are co-added sky-pixel samples at the current ten-frame preview preset coordinates. The compact offline preview contains exactly these five sampled pixels and their 25 × 25 native channel-map windows. Pixel indexes are zero-based. Wavelength ranges give the first and last measured centers. Interior gaps remain possible.

| Preset | Requested ICRS RA, Dec (°) | Tile / pixel | Measured | No usable coverage | Flagged | Blank | Missing wavelength | Measured centers (µm) |
|---|---|---|---:|---:|---:|---:|---:|---|
| Barnard’s Star | 269.4461286205729, +4.769998359667445 | 7945 / (98, 103) | 8 | 90 | 2 | 2 | 0 | 4.294–4.879 |
| WISE 0855 | 133.75896227492004, −7.242116064321349 | 10226 / (212, 238) | 99 | 0 | 1 | 2 | 0 | 0.753–4.988 |
| RW Aurigae | 76.95658820303035, +30.401287398865755 | 277 / (400, 252) | 35 | 15 | 50 | 2 | 0 | 0.753–4.988 |
| R Draconis | 248.16722768733652, +66.75502445923215 | 2928 / (20, 425) | 0 | 100 | 0 | 2 | 0 | — |
| Epsilon Indi B | 331.09813086506205, −56.801144263858404 | 11391 / (97, 408) | 100 | 0 | 0 | 2 | 0 | 0.753–4.988 |

The audit also checked the original configured coordinates, the independent ICRS J2000 references, and the earlier DR1 exposure-midpoint predictions in [target validation](TARGET_VALIDATION.md). At the original coordinates, the measured counts were 100, 100, 53, 100 and 100 in table order. R Draconis’s original coordinate lands on tile 2906, while its J2000 reference and exposure prediction both land on the empty sampled pixel in tile 2928. Barnard’s Star’s earlier prediction gives 29 measured channels on tile 7945. These differences describe the sampled mosaic pixels. A configured coordinate, a catalog reference, or a propagated position supplies no single epoch for the cube and confirms no source association.

All 20 live discovery requests received upstream HTTP 502 and the app returned HTTP 503. The audit separately supplied verified archive tile URLs to the existing cube endpoint and checked the returned values against native FITS samples. The complete local evidence at `outputs/verification/cube-coverage.json` includes all 102 ordered channel records for each position, FITS provenance and source access outcomes.

After that audit the cube endpoint gained an offline fallback for the five rows above. Live archive results take precedence. The app labels a fallback result **Cached DR1 sky-pixel preview** and discloses the extraction coordinate, date, tile, and archive file identity. See [offline demo instructions](DEMO_SCRIPT.md#offline-spectral-cube).
