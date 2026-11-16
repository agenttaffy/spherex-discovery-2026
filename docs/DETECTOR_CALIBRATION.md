# Detector calibration provenance audit

## Current RW Aurigae D1 check (Nov 15, 2026)

The screenshot pair `2025W36_1A_0095_1` and `2025W36_1A_0155_1` consists of real, cloud-cached D1 cutouts at RA 76.956588203°, Dec +30.401287399°, with a 2.4′ requested cutout. Both science IMAGE headers cite spectral-calibration plane `019f4f98-edf0-744b-9600-424841d46dc0`. As an **exploratory visualization-only check**, interpolation of each image's own WCS-WAVE table gives central sampled wavelengths of approximately 1.06848 and 1.11970 µm, with nominal bandwidths approximately 0.02827 and 0.02914 µm respectively. Among aligned quality-eligible pixels, the best approximate nominal passband overlap was **0.0%** at the app's 90% threshold. This is not an exact calibrated overlap, target detection, or motion measurement; WCS-WAVE is an approximation and IRSA specifies CWAVE/CBAND for science.

An exploratory sample of 19 D1 cloud cutouts found a different possible pair, `2025W36_1A_0606_2` and `2026W10_1A_0445_2`, retaining 219/529 field pixels using the approximate lookup. The two cloud cutouts are cached, but this is **not yet a verified calibrated comparison** and is not a recommendation to infer target identity or motion. It must be repeated using the exact independently matched detector calibration.

To reproduce both approximate checks from the staged local cache without any network requests, run `python scripts/audit_rw_aur_d1_preview.py`. The script prints each science image's calibration UUID, estimated center and bandwidth, and either the approximate overlap rejection or retained count. Missing inputs cause an explicit error; the script does not register a calibration or feed these preview calculations to the app.

The public D1 cloud calibration under `cal-swcs-v5-2026-191` has ETag `624790eba5fdde40a6cb2187099e415d`; its WCS-WAVE table matches the first screenshot image's table bit-for-bit. This is useful corroboration, but an identical approximation and mirror ETag do not prove the required plane-UUID-to-full-resolution artifact association. No D1 artifact has been registered on that basis. Exact catalog jobs [28376461](https://irsa.ipac.caltech.edu/TAP/async/28376461) (D1/D4) and [28376462](https://irsa.ipac.caltech.edu/TAP/async/28376462) (D2) were initially queued; a later check on Nov 16 UTC reported both `CANCELLED`, without a successful result. A future lookup needs a new job once the archive is responsive. Independently verify the UUID, detector, archive path and published checksum before pinning any artifact, then rerun the screenshot and candidate pairs with native CWAVE/CBAND, quality masks, WCS alignment, exposure independence and variance checks. A cancelled job is not evidence that a calibration does not exist.

Previously TAP-verified D3/D5 artifacts can now be reused by a DR1 or QR3 image **only when the detector and science-header calibration plane UUID exactly match**; no new QR3 sample has been independently validated by this rule. Verified artifacts are downloaded from the public cloud mirror first and the on-premises archive second, with the published MD5 checked before use or caching.

**D3 and D5 are each verified for five readable sampled DR1 exposures. D6 is verified in the sampled DR1 and QR3 exposures.** The archive exposes Spectral WCS products for all six detectors. Using one for a comparison requires the exact `[CALIB] spectral_wcs` plane UUID from the science IMAGE header, a unique matching `spherex.artifact` record naming the detector and archive artifact, and verification of its published checksum. `CWAVE` and `CBAND` give the per-pixel center and bandwidth in µm. The visualization lookup `WCS-WAVE` supports approximate display wavelengths. [IRSA data products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/) · [IRSA data access](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/)

## Archive objects and coverage

IRSA's public AWS listing and HEAD returned 12 files (one per detector and release), all 33,312,960 bytes under `cal-swcs-v5-2026-191`. The DR1 and QR3 object ETags agreed for each detector. HEAD provided no plane UUID or additional checksum metadata for these files. A version listing or mirror ETag alone supplies no science-header UUID association. No unlinked D1–D5 map was downloaded or used for science. [Official AWS mirror](https://nasa-irsa-spherex.s3.amazonaws.com/?list-type=2&prefix=dr1%2Fspectral_wcs%2Fcal-swcs-v5-2026-191%2F)

The counts below are verified calibrations divided by readable science files from the 36 selected endpoints of the prior motion screen. A cell marked “No readable sample” means the selected QR3 cutout could not be loaded. Mirror ETags identify published objects. D3, D5 and D6 also have independently verified archive MD5 values. D1, D2 and D4 remain unresolved.

| Detector | Science IMAGE calibration UUID seen | DR1 calibrated / readable | QR3 calibrated / readable | Mirrored object ETag |
|---|---|---:|---:|---|
| D1 | `019f4f98-edf0-744b-9600-424841d46dc0` | 0/3 | 0/1 | `624790eba5fdde40a6cb2187099e415d` |
| D2 | `019f4f99-03f1-7376-a5a0-676318f2ddb6` | 0/3 | 0/1 | `af87630c33716cd77ae54ab6c63d388d` |
| D3 | `019f4f99-19af-763f-8f2e-b7dc6cd00055` | 5/5 | No readable sample | `327f973e59efeaa101bf1fe9ac7c354e` |
| D4 | `019f4f99-3265-766b-b368-e28eb08fdbed` | 0/2 | 0/2 | `438a1d94ca7b392cf854f68d18bfd7db` |
| D5 | `019f4f99-48fc-73a4-b778-eb25bf616d6b` | 5/5 | No readable sample | `d59bd98b5d1d14ae8d74499b1c1ccb3f` |
| D6 | `019f4f99-5f21-722d-bd8d-a6033df45708` | 5/5 | 1/1 | `e665c189ad63ca0cd032c0797e8aabf2` |

The app resolver pins exact detector and plane combinations for D3, D5 and D6; matching current-release DR1/QR3 images can reuse the same pinned artifact. D1/D2/D4 remain unresolved in the local cache even when those detector files appear in the archive listing. The online resolver still requires an exact artifact association. Cached calibrations are checked against the published MD5 before use.

The existing D6 lookup refers to [completed IRSA TAP job 28334899](https://irsa.ipac.caltech.edu/TAP/async/28334899). Re-read the job parameters and its VOTable result. The exact UUID query returned the [DR1 D6 calibration FITS](https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/spectral_wcs/cal-swcs-v5-2026-191/6/spectral_wcs_D6_spx_cal-swcs-v5-2026-191.fits) with archive MD5 **`e665c189ad63ca0cd032c0797e8aabf2`**. Independently hashed the cached 33,312,960-byte file to that MD5. The two 2040 × 2040 extensions identify detector 6 and use µm. Both sampled releases' science headers reference the same UUID, which is what permits this verified artifact for the sampled QR3 exposure. No date- or detector-based substitution was used.

The six-UUID asynchronous query `28346199` and individual exact D3 (`28346496`) and D5 (`28346499`) jobs all returned `CANCELLED` on recheck. A bounded direct D3 TAP request timed out reading the response. The alternate public IRSA host timed out connecting for D5. At that stage those attempts had supplied no UUID-to-artifact checksum records. Later jobs verified the sampled DR1 D3 and D5 mappings, as documented below. D1, D2 and D4 still need exact archive associations.

## Exact asynchronous lookup procedure

`python scripts/resolve_spectral_uws.py --seconds 150` reads the saved IMAGE headers to recover the detector-specific plane IDs. It submits exact artifact queries for D3, D5, D2 (the Kapteyn's Star control), and a D1/D4 batch. The client uses a 12-second connect timeout, 30-second read timeout and 150-second per-attempt observation window. It records the job location, posts `PHASE=RUN` for PENDING or HELD jobs, polls `/phase`, and reads `/results/result` only after `COMPLETED`. Terminal errors retain the job and error response bodies. A local deadline leaves a remote job in place. An HTTP error or incomplete job never becomes an empty successful result. [IRSA TAP instructions](https://irsa.ipac.caltech.edu/docs/program_interface/TAP.html) · [IVOA TAP recommendation](https://www.ivoa.net/documents/TAP/20190927/REC-TAP-1.1.html)

The logs in `data/cache/target_validation/motion_multidetector/tap_uws/` preserve the exact ADQL, request URLs, UTC timestamps, response bodies, statuses and elapsed local observation time. Use `--resume --only D3` to poll a saved D3 job. The separately bounded `--retry-unconfirmed` option is for submissions without a saved job ID. `--via-get` uses the query-string submission route documented by IRSA. A completed result must identify the exact plane and provide a matching artifact URI and checksum before any map can be applied to a science frame.

| Scope | Job and final observed response | Cumulative local observation time |
|---|---|---:|
| D3 | Query-string submission returned HTTP 303 to [job 28349004](https://irsa.ipac.caltech.edu/TAP/async/28349004). `/phase` returned HTTP 200 `QUEUED` through the final attempt. The 150-second local window expired and the job was left alone. | 180.7 s |
| D5 | Three requests timed out reading a response. No job URL was returned to the client. | 90.7 s |
| D2 control | One HTTP 502 proxy response, followed by two read timeouts. No job URL was returned to the client. | 60.5 s |
| D1/D4 | One HTTP 502 proxy response, followed by a read timeout. No job URL was returned to the client. | 30.4 s |

Those initial attempts produced no successful result. The D2 Kapteyn's Star control `2025W34_1B_0134_1` → `2026W34_2A_0143_3` has 0/19 → 0/18 usable core pixels and remains unassessed for calibrated overlap. The separate 102-channel DR1 cube does not supply exposure-pair calibration.

### Resumed D3 result

Resumed [job 28349004](https://irsa.ipac.caltech.edu/TAP/async/28349004) without another submission. `/phase` returned HTTP 200 `COMPLETED` on the first resumed poll. `/results/result` returned HTTP 200 and exactly one row for the D3 science UUID. The final cumulative local observation time was 181.1 seconds. The returned [DR1 D3 artifact](https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/spectral_wcs/cal-swcs-v5-2026-191/3/spectral_wcs_D3_spx_cal-swcs-v5-2026-191.fits) had archive MD5 `327f973e59efeaa101bf1fe9ac7c354e`. The downloaded 33,312,960 bytes matched that checksum. The verified map is stored separately at `data/cache/spectral-calibration/spectral-327f973e59efeaa101bf1fe9ac7c354e.fits`.

All five readable D3 DR1 science files accepted that exact map through the existing checksum and detector checks. The updated coverage and diagnostics are `calibration_coverage_resumed.csv`, `calibration_coverage_resumed.json` and `epsilon-d3-verified-pair.json` under `data/cache/target_validation/motion_multidetector/`. Earlier files retain the pre-resume baseline. The resumed files record the exact artifact association and unchanged pipeline outcomes without changing the application resolver.

### D5 follow-up

Exactly one query-string submission for science UUID `019f4f99-48fc-73a4-b778-eb25bf616d6b` returned HTTP 303 to [D5 job 28350118](https://irsa.ipac.caltech.edu/TAP/async/28350118) and remained `QUEUED` at the first local cutoff. Resuming the saved job returned HTTP 200 `COMPLETED` on the first phase poll. `/results/result` returned HTTP 200 and one row with the exact science UUID, the [DR1 detector-5 artifact](https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/spectral_wcs/cal-swcs-v5-2026-191/5/spectral_wcs_D5_spx_cal-swcs-v5-2026-191.fits), and published MD5 `d59bd98b5d1d14ae8d74499b1c1ccb3f`. The job log totals 241.3 seconds of local observation including earlier connection attempts. The resume made two GET requests and submitted no new job.

The downloaded 33,312,960 bytes matched the published MD5 and passed the detector, provenance and native pixel mapping checks for all five readable D5 DR1 science exposures. The map is stored separately at `data/cache/spectral-calibration/spectral-d59bd98b5d1d14ae8d74499b1c1ccb3f.fits`. The exact resumed pair diagnostics are in `epsilon-d5-verified-pair.json` and the updated D1–D6 matrix is in `calibration_coverage_resumed.csv` and `.json`.

The D5 pair is available under **Difference & Stack** in the local demo. Difference and mean/sum co-add retained 207/225 pixels on the 15 × 15 reference grid. Their minimum retained nominal field overlap was 98.62206923573%. The two predicted cores each retained 19/19 pixels in the earlier science audit. This was a field arithmetic check near Epsilon Indi. Epsilon Indi Ba/Bb are unresolved and source detection, motion, target flux and variability remain unverified. [Endpoint and browser verification](../TEST_RESULTS.md#d5-comparison-integration--2026-11-15)

Verification for this follow-up included 17 focused UWS/calibration/overlap tests. The Windows launcher served a healthy backend, the ten-frame/five-preset manifest through the frontend proxy, and the frontend HTML, then released its two ports. Both manifest SHA-256 values matched. No product code or cube data was modified.

## Pair rerun

Run `python scripts/audit_detector_calibration.py` from the repository root. It replays exact saved science FITS through the existing preparation and comparison path and writes `calibration_coverage.csv` and `calibration_coverage.json` under `data/cache/target_validation/motion_multidetector/`. The existing `pair_matrix.csv` gives the exact exposure IDs and all selected rejection reasons. The pixel counts below show the pre-mask half-pixel alignment step, the valid aligned subset, and the final result from the comparison engine at its unchanged 90% passband threshold.

| Pair | Usable source core | Nominal source overlap | Common pixels | Within 0.5 pixel | Valid aligned pixels | Accepted / excluded reference pixels |
|---|---|---:|---:|---:|---:|---:|
| Epsilon Indi B D3 `2025W18_1B_0091_2` → `2026W18_1A_0444_1` | 20/20 → 21/21 | 96.06% | 225 | 0 | 0 | 0 / 400 |
| Epsilon Indi B D5 `2025W17_4B_0027_3` → `2026W17_2A_0308_3` | 19/19 → 19/19 | 95.33% | 225 | 225 | 207 | 207 / 18 |
| Epsilon Indi B D6 `2025W18_1B_0091_2` → `2026W18_1A_0444_1` | 19/20 → 17/18 | 96.14% | 225 | 0 | 0 | 0 / 400 |
| Barnard's Star D6 `2025W33_2C_0321_1` → `2026W34_1A_0176_2` | 4/16 → 9/20 | 59.42% | 360 | 360 | 332 | 0 / 400 |
| WISE 0855 D6 `2025W19_1B_0138_1` → `2026W19_2A_0651_1` | 21/21 → 21/21 | 94.50% | 380 | 0 | 0 | 0 / 400 |

Epsilon Indi B D3 passes the source-core overlap requirement and fails nearest-native-pixel alignment. Its D5 pair retains 207 pixels, including all 19 pixels in each predicted core. The lowest retained field overlap is 98.62%, and 18 aligned pixels fail the quality/validity check. Epsilon Indi B and WISE 0855 D6 also fail alignment. Barnard's Star D6 aligns across most of the field, but none of its valid aligned samples pass the wavelength overlap rule and its source cores are masked. The positive DR1 D6 deep-field control `2025W18_1B_0242_2` → `2025W18_1B_0252_2` retained **378/400** pixels in the prior audit. Twenty-two failed the quality mask.

The app labels detector field samples and estimated spectrum wavelengths separately, identifies unavailable comparison detectors, and labels successful pair checks with verified CWAVE/CBAND. The separate DR1 Spectral Cube retains native measured sky-pixel values and flags. Its co-added channels supply no calibration for a dated exposure pair. **Go for calibrated image comparison on the retained D5 pixels. No-go for a source detection or motion claim.** The next step is to independently associate the unresolved target with image features in both frames, then validate centroid error and registration against nearby stationary controls. This comparison did not measure a displacement or its uncertainty.
