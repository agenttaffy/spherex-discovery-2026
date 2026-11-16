# SPHEREx Discovery — Test Execution Record

> **Current availability baseline.** Cloud and IRSA observations support dated image viewing, timeline/blink, and celestial context; live metadata search remains intermittent. The synthetic continuum was removed. The DR1 cube supplies native co-added sky-pixel measurements and can read bounded cloud ranges, with gaps and flags retained. Candidate source identity, motion, and target photometry remain unconfirmed. Difference and co-add validate calibrated passbands and WCS; incompatible pairs are rejected. Historical milestones below may describe superseded behavior. See [the current traceability matrix](docs/CHALLENGE_REQUIREMENTS.md).

## Cloud and multi-exposure checks, November 15

- Real public-cloud cube reads for Epsilon Indi, WISE 0855 and R Draconis matched all 102 channel records and a selected native map against verified packaged samples. The Epsilon sample returned 100 measured slots and two blanks. One cold sample transferred approximately 185 KB. A pinned DR1 fallback is labeled separately from SIA-discovered data.
- Six real cloud image cutouts matched cached IRSA image, variance, flags and zodiacal planes. Two cloud D5 cutouts reproduced the independently checked 207/225-pixel difference and propagated variance. An 18′ cloud cutout transferred about 10.24 MB in the recorded local check.
- Three independent R Draconis D6 exposures produced a real mean and sum co-add with 123/529 field pixels; an independent FITS/WCS/calibration calculation matched values and propagated variances. This does not establish an object detection or motion.
- Using the running preview and partial cloud-header list, the Epsilon Indi D5 pair `2025W17_4B_0027_3` and `2026W17_2A_0308_3` at a 2.4′ shared field returned HTTP 200 for difference, mean and sum with 485/529 field pixels retained. The pair is offered as a shortcut when both records are present; each use reruns the compatibility checks. Detection and motion remain unconfirmed.
- The running preview returned eight Epsilon Indi records (five unique exposure IDs on four calendar dates) and 60 WISE 0855 records (60 unique exposure IDs on 26 calendar dates) during an archive-search failure. Both lists include incomplete, dated cloud-header surveys and demo records; they are not proof of target identity or exhaustive archive coverage.
- The complete backend suite passed 265 tests with three warnings from deliberately malformed FITS and WCS fixtures. The frontend production build and focused band, CSV, blink, spectrum, provenance and frame-cache checks passed. Browser end-to-end checks of the newest interactions are still needed; the build retains an Aladin bundle-size notice.


## Clean Windows candidate and offline launch

- A tracked snapshot of public main at `4c0e482` contained no FITS, launcher, or bootstrap. A separate candidate built from that snapshot and the pending source started with zero FITS. The unseeded read-only check reported 15 missing runtime paths without writing.
- The candidate downloaded and verified 14 pinned FITS files totaling 114,042,240 bytes. Two cutouts needed retries after HTTP 503. No full cube tile was needed. A repeat run with archive access disabled reused every verified file.
- The actual Windows launcher passed its preflight and served ten cached images and five cached cube samples through the local proxy. Measured channel counts were 8 for Barnard’s Star, 99 for WISE 0855, 35 for RW Aurigae, 0 for R Draconis, and 100 for Epsilon Indi B. Channel 51 remained blank. D5 difference and mean/sum co-add retained 207/225 pixels. The staged WISE pair returned HTTP 422 for incompatible passbands.
- The focused backend run passed 34 tests with one warning. All six launcher checks and the whitespace check passed. The test used Python 3.11.4 and Node.js 22.19.0. [Fresh-checkout instructions](README.md#preview-a-refreshed-demo-cache)

## Public release safety and routing

- The tracked and changed text scan found historical machine-specific paths in this file. The working copy has the paths normalized. The scan found no credential-shaped literals or embedded credentials in the eligible text and skipped local environment files. Git ignore checks covered environment variants, Vercel state and local run outputs.
- Local processes verified three CORS settings. Unset allows the explicit localhost defaults, blank disables cross-origin access, and an explicit origin allows only that origin. Unlisted preflight requests returned HTTP 400 and wildcard configuration failed startup validation. The production bundle served an SPA deep link and static assets. Its local proxy preserved healthy HTTP 200 JSON, a missing-route HTTP 404, and an archive-unavailable HTTP 503.
- Both public Render hostnames still returned HTTP 404 plain text with `x-render-routing: no-server`. The GitHub page returned HTTP 200. No frontend URL was established. Both deployment files passed the published schemas. [Public release checklist](docs/SUBMISSION_CHECKLIST.md#4-public-release-preflight)
- The Windows launcher served ten frames and five presets through its API proxy, and the D5 difference, mean and sum each retained 207/225 pixels. The focused tests passed 13 checks and the full backend suite passed 197 with three Astropy fixture warnings. All 49 UI checks passed. The frontend build passed with the existing Aladin bundle-size warning. Both manifests, the cube artifact and source pins, the D5 manifest and the launcher matched their previous hashes.

## Judge walkthrough rehearsal

- Windows launched the optional ten-frame preview at `http://127.0.0.1:15173/`. Chrome checked the WISE dated observation selector, updated exposure prediction, playback toggles, and target-photometry disclosure at 1440 and 320 px. It then verified the WISE comparison rejection, D5 calibration UUID and MD5, difference and mean co-add at 207/225 pixels, and the Barnard’s Star and R Draconis cached cube results with eight and zero measured channels, respectively. Channel 51 showed the blank map. Aladin 2MASS rendered at both widths, and the Canvas return worked. No horizontal page overflow appeared. On mobile, the timeline and lower comparison/cube controls require vertical scrolling.
- The configured GitHub landing page loaded without authentication. The Render health endpoint returned HTTP 404. The main NASA challenge page was unavailable during the check. The challenge title and objective match the brief reproduced by NASA Space Apps Lucerne and the Ulaanbaatar listing.
- This pass changed documentation only. At the time, the recorded full checks were 184 backend tests, 49 UI checks, and a successful frontend build with the existing Aladin chunk-size warning. The backend run recorded three Astropy fixture warnings. [Rehearsed script](docs/DEMO_SCRIPT.md)

## Offline Spectral Cube preview

- Reused the checksum-verified tile 7945. Read pinned IRSA mirror ranges for tiles 277, 2928, 10226, and 11391, validating each HTTP 206 range and the matching ETag and byte length. The refresh matched every audited channel digest and each native map’s values, masks, size, center, and FITS row order. The 510 native windows and five co-added sky-pixel channel series occupy 2,708,179 compressed bytes. Two independent extractions for UTC 2026-11-15 produced SHA-256 `FD064FA610DD7CC12E84B54C35F8FB8FA7DF58B13277EC2D15433DB827C3AD27`.
- The focused suite passed 16 tests and the full backend passed 184 tests with three Astropy fixture warnings. All 49 static UI checks passed. The production build passed with the existing Aladin chunk-size warning. Whitespace checks passed. D5 difference, mean and sum retained 207/225 pixels through the launched preview. The optional launcher still served ten frames and five presets. Both demo manifest hashes matched the prior verification.
- The archive-precedence check used a controlled SIA response naming the actual Barnard’s Star FITS tile. The regular endpoint resolved it, read the verified full FITS file, and returned HTTP 200 with `source: "irsa_archive"` and no preview payload.
- Offline Chrome blocked external name resolution and the backend pointed SIA at a refused loopback port. All five presets loaded through the real local API at 1440 and 320 px. Each check exercised channels 1, 3, 51, 52, and 102, verified the cache/source disclosure, and found no horizontal overflow. The two blank maps were empty, and R Draconis showed no usable spectrum. An unrelated test coordinate returned the original archive error. The walkthrough used no browser response replay.
- Restored the launcher’s normal archive endpoint afterward. That SIA request still returned upstream HTTP 502, and the actual app served the matching cached channel 3 preview. The verification launcher was then stopped.

## Five-target DR1 cube audit

- Verified 20 positions on six IRSA DR1 tiles. The audit requested the five active preview presets, the five original configured coordinates, the independent ICRS J2000 positions, and the five earlier DR1 FITS midpoint predictions. All live SIA lookups returned HTTP 502 upstream and the cube endpoint returned HTTP 503. With an audit-only lookup supplying verified archive tile URLs, the same endpoint returned HTTP 200 for each coordinate. Archive access failures are logged separately from no usable channel coverage.
- Reused the app’s cached tile 7945, recorded its SHA-256 and matched the complete cached file’s MD5 to the public mirror ETag `07d1a4fdc7ff3e74f12af115609a3814`. For tiles 277, 2906, 2928, 10226 and 11391, verified each exact HTTP 206 byte range and the matching object ETag from IRSA’s public AWS mirror. The audit compared the endpoint’s nearest native pixel and center, all 102 ordered channel numbers, wavelength centers and widths, hit counts, flags, brightness and null masks against the FITS WCS, channel table, and scalar samples. Map centers agreed with channels 1 and 3 where tested. [Per-preset counts and limits](docs/CHALLENGE_REQUIREMENTS.md#dr1-cube-coverage)
- Chrome at 1440 and 320 px transferred all five exact preview coordinates from Explorer to Cube and from direct links. Browser replay of the audited endpoint responses exercised the coverage summary, 102 channel options, and switching to channel 3, including R Draconis’s no-usable-spectrum state. The pages fit the viewport.
- Focused cube and D5 tests passed 11 checks. The full suite passed 179 tests with three known Astropy fixture warnings. All 47 UI checks passed. The frontend build passed with the existing Aladin bundle-size warning. Whitespace checks passed. The Windows launcher served the optional ten-frame preview. Both manifest hashes matched the D5 record below. D5 difference, mean and sum each returned 207/225 retained pixels at nominal minimum overlap 0.9862206923573.

## Glass observatory integration

- Chrome at 1440, 320 and 375 px checked Explorer, Blink, Aladin, D5 difference and co-add, and the cube. The WISE 0855 FITS preview is a 20 × 20 native sample. It drew at 340 × 340 in a 1134 × 384 desktop canvas, 220 × 220 in a 314 × 255 canvas at 320 px, and 240 × 240 in a 369 × 285 canvas at 375 px. Image smoothing was disabled. Keyboard zoom, pan and reset, epoch playback, and reduced-motion mode were exercised. No horizontal overflow was found in the tested areas.
- Aladin rendered both live 2MASS Color and DSS2 color at all three widths and returned to the SPHEREx canvas. Browser captures retain the survey credit, selected coordinate and FITS footprint. Live cube queries returned the archive-unreachable state in the final three-width run. The loaded cube UI was separately verified by replaying material sampled with the existing code from cached IRSA DR1 tile 7945. It showed 102 slots, 29 measured, one flagged, two blank and 70 without usable coverage, with the channel 3 native map and flag intact.
- The preview launcher served ten frames and five presets. Both manifest SHA-256 digests matched the D5 integration record below. Running D5 difference, mean and sum returned HTTP 200 with 207/225 retained and minimum nominal overlap 0.9862206923573. The WISE 0855 difference rejection remained visible before selecting D5. The full suite rechecked WISE co-add rejection, and the D6 deep-field replay retained 378/400.
- Backend suite: 175 passed with three Astropy fixture warnings. All 47 static UI checks passed. The production build passed with the Aladin chunk-size warning. Git whitespace check passed. The local screenshots and viewport report are under `outputs/verification/glass-*`. Comparison cards use compact values for the narrow layout. The metrics table retains the values returned by the API.

## D5 comparison integration — 2026-11-15

- The local cache contains both exact DR1 D5 Level 2 cutouts. FITS inspection matched both observation IDs, detector 5, the table’s exposure midpoints, and spectral WCS plane `019f4f99-48fc-73a4-b778-eb25bf616d6b`. Release provenance comes from the checksummed IRSA DR1 cutout URLs. The calibration map matched archive MD5 `d59bd98b5d1d14ae8d74499b1c1ccb3f`.
- The running preview returned HTTP 200 for the D5 difference, mean co-add, and sum co-add. Each returned a 15 × 15 grid, **207 retained pixels**, **18 masked pixels**, and minimum retained nominal overlap **0.9862206923573** at the 0.90 threshold. The endpoint tests independently reconstructed the FITS/WCS sample pairs and matched all returned values, propagated variances, native-order null masks, and display-oriented PNG alpha masks. Both WISE 0855 operations returned HTTP 422 with the passband-overlap rejection. The cached Epsilon Indi D3 replay retained zero pixels. The cached D6 deep-field control retained 378/400.
- Chrome at 1440 and 320 px started at `/?target=wise_0855&tab=diff`, showed the WISE rejection, selected the D5 pair, displayed both real previews and both arithmetic modes, expanded the plane ID and MD5, and returned to the WISE co-add rejection. The layout fit both widths. An injected browser 503 disabled the selector and displayed the calibration error. A backend test separately exercised the missing-calibration response.
- Focused tests: 13 passed. Full backend suite: 175 passed, with one Astropy `VerifyWarning` from the intentionally malformed FITS fixture and two `FITSFixedWarning` warnings from the axes-mismatch fixture. All 47 static UI checks passed. The production build passed with the Aladin chunk-size warning. Whitespace checks passed. The Windows launcher FITS audit passed and served ten frames and five presets via the frontend proxy.
- The original and optional preview manifest SHA-256 values matched before and after the integration. Original `9DBB091624CCFC9B471CEE234CC07C5208634B6749757A55C597D3A23ADCB39B`. Optional `781C4D4EE7D72C04B150D07BCBEDD59A8010A04F591DE0AF8F9D63E27BFF4E60`.
- Local evidence is in `outputs/verification/d5-api-evidence.json` and the `epsilon-d5-*.png` and `wise-0855-rejected-*.png` Chrome captures.

## Initial IRSA UWS calibration follow-up — 2026-11-15

- The query-string submission for D3 returned job 28349004, and the final phase responses were HTTP 200 `QUEUED`. The 150-second observation window ended without a result or client cancellation. D5, D2 and D1/D4 recorded proxy and/or read failures without job URLs. The coverage audit again retained 378/400 for the D6 control and zero for the three D6 motion candidates. No D1–D5 map was verified. [UWS evidence and rerun commands](docs/DETECTOR_CALIBRATION.md#exact-asynchronous-lookup-procedure)
- Focused checks: 17 passed. Backend suite: 170 passed, with three known Astropy fixture warnings. Static UI checks: 47 passed. The launcher served healthy local APIs, ten cached cutouts and five presets through the frontend proxy, and the frontend HTML loaded. Stop released the launcher-owned ports and preserved the existing port 8000 listener. Both manifest hashes matched. Production UI and build inputs were unchanged in this pass.

## Detector calibration provenance audit — 2026-11-15

- Reverified the D6 TAP UUID and checksum against the local FITS and mapped six sampled DR1/QR3 exposures. D1–D5 public files were listed, with no exact science UUID association established. Reran the three calibrated candidate pairs with zero retained pixels and the independent D6 deep-field control with 378/400 retained. [Evidence and coverage matrix](docs/DETECTOR_CALIBRATION.md)
- Focused calibration and overlap tests: 12 passed. Full backend suite: 165 passed, with three known Astropy fixture warnings. Static UI checks: 47 passed. The production build passed with the Aladin bundle-size warning. Chrome verified the D6 comparison rejection at 1440 and 320 px without horizontal overflow. Git and new-file whitespace checks passed, and both manifest hashes matched.

## Broader D1–D6 motion screen — 2026-11-15

- All 18 metadata queries returned HTTP 200. The 18 selected pairs span all six detectors and nine sources. Twenty-eight of 36 primary cutouts were recovered and both wider WISE cutouts loaded. Only the three D6 pairs had locally verified spectral calibration. None passed motion preflight. The wider WISE comparison found zero aligned pixels within the unchanged 0.5-pixel limit out of 4,900 geometrically common samples. [Report and pair counts](docs/MOTION_MULTIDETECTOR.md)
- Focused tests passed 19 checks. The full backend suite passed 164 tests with three known Astropy fixture warnings. All 46 static UI checks passed. The production build passed with the Aladin bundle-size warning. Git and new-file whitespace checks passed. Both manifest hashes matched the previous study.

## Moving-source archive preflight — 2026-11-15

- The reproducible local audit rejected all 29 distinct D6 pairs. All five staged pairs had zero source-core overlap and no qualifying aligned pixels. The sole compatible source-core pair was Lalande 21185 (93.95%, 372 field pixels). Its masked cores prevented centroid measurement. Three additional Gaia sources were queried in DR1 and QR3. All 20 selected DR1 cutouts were recovered after four smaller retries, while the QR3 queries ended in HTTP 502. See the [pair matrix and methods](docs/TARGET_VALIDATION.md#moving-source-preflight).
- Focused tests: 13 passed. Full backend suite: 160 passed, with three known Astropy fixture warnings. UI source checks: 46 passed. Production build passed with the Aladin chunk-size warning. Chrome rendered the Blink explanation using the audited preview at 1440 and 320 px with no horizontal overflow. At 320 px, the timeline is below the fold. Captures are `outputs/verification/motion-blink-1440px.png` and `outputs/verification/motion-blink-320px.png`.

## D6 real-source controls — 2026-11-15

- Six D6 exposures in three fields were evaluated with Gaia DR3 and AllWISE. Zero of 578 catalog-quality star-exposure candidates passed the footprint and isolation checks, and zero of 225 blank-grid footprints qualified. Across 120 real detector ePSF stamps, the maximum pixel difference from the IRSA tutorial's Photutils rendering was zero. The deep-field pair had 95.82% conservative nominal field-center overlap and no matched clean star. See the [reproducible report](docs/D6_CONTROL_VALIDATION.md).
- Focused tests passed 23 checks, including the epoch match, quality veto, complete centroid/residual criteria, and conservative passband overlap. The full backend suite passed 157 tests with three known Astropy fixture warnings. No product code changed, so frontend build and UI verification were outside this pass.

## Isolated ePSF study — 2026-11-15

- The study ran locally on ten staged D6 frames and a 93 × 94-pixel comparison field. Two staged fits ran experimentally, eight were skipped by geometry or quality, and zero were eligible for target flux. All three staged injection patches had independent catalog contaminants. There were 28 injection fits, eight rejected phases, and one independent-position stellar recovery without a matched D6 flux reference. The exact input checks, per-frame masks and residuals, and failed validation gates are in [TARGET_VALIDATION.md](docs/TARGET_VALIDATION.md#isolated-d6-prototype-and-product-checks).
- Focused ePSF/photometry/astrometry tests: 19 passed. Full backend suite: 153 passed with three Astropy fixture warnings. UI source checks: 45 passed. Production build passed with the Aladin chunk-size warning. The analysis is a standalone script. Browser and API evidence labels were not modified for this study.

## Windows demo launcher — 2026-11-15

- Windows PowerShell loaded the default ten-frame preview at app port 15173 and API port 18100. Both direct and frontend-proxied manifest requests returned ten entries and five presets. Each preset returned two cached observations. Chrome rendered the WISE 0855 2026 frame, the **Cached demo** indicator and the field-only evidence disclosure. Both WISE comparison operations returned the expected passband HTTP 422. Screenshot: `outputs/verification/windows-demo-launcher.png`.
- The preview FITS audit returned ten passes and zero warnings. Explicit `-Dataset Original` returned 22 entries and the audit reported 19 passes and three known warnings. Both launcher sessions stopped and released their ports. The existing listener on port 8000 retained the same PID. A one-second startup timeout also released both ports and removed the session record.
- Six focused PowerShell checks passed, covering arguments, exact manifest selection, missing cache, occupied ports, timeout and process identity cleanup. Backend suite: 150 passed with three Astropy fixture warnings. UI checks: 45 passed. Production build passed with the Aladin chunk-size warning.

## Photometry evidence closeout — 2026-11-15

- Focused evidence and astrometry tests: 16 passed. Full backend suite: 149 passed, with three Astropy FITS/WCS fixture warnings. Frontend production build: passed with the Aladin chunk-size warning. Static UI checks: 45 passed. `git diff --check` passed.
- A local offline-preview server returned all ten real staged exposures from the FITS cache. API checks matched the reference RA/Dec within 0.0000001°, MJD within 0.0000001 days, and published rounded WCS pixels within 0.006 pixels. All ten target flux statuses are unavailable. Field aperture statuses were three `field_sample_only` and seven `unavailable`, with exact mask counts in [TARGET_VALIDATION.md](docs/TARGET_VALIDATION.md#source-photometry-feasibility). Both WISE pair operations returned HTTP 422 for passband overlap.
- Opened each preset and stepped through both epochs in Chromium at 1440 px. Inspected expanded evidence on R Draconis at 1440 px and WISE 0855 at 320 px. Both views retained a visible sky image with no page-level horizontal overflow. The expanded disclosure adds vertical scrolling at 320 px. Captures are `outputs/verification/photometry-evidence-1440px.png` and `outputs/verification/photometry-evidence-320px.png`.
- Probed synthetic fallback using a forced archive miss. The API returned simulated provenance and empty prediction/evidence maps. Chromium rendered that response with the synthetic image banner and no target-evidence disclosure or prediction marker label. The default 22-file manifest and optional ten-file stage were preserved.

## Target-centered follow-up — 2026-11-14 (historical)

- The full backend suite passed 138 tests with three Astropy fixture warnings. The frontend production build passed with its Aladin chunk-size warning. UI source checks passed 44 assertions, including source-identity labeling, a single-exposure state and the cube coverage display. Git's whitespace check passed.
- The legacy demo audit returned 19 pass, three known warnings and zero failures. The expanded `data/cache/demo_multiepoch` preview returned ten pass with zero warnings or failures.
- Chromium opened both real WISE exposures using the local audited cache. The 2026 frame rendered at 320, 375, 768 and 1440 px without horizontal page overflow. The 2025 view displayed its different exposure-epoch prediction. The local difference API rejected that pair with HTTP 422.
- Re-read the actual DR1 tile FITS metadata and pixels. The epoch-corrected Barnard’s Star sample had 30 hit-covered channels, including 29 measured and one flagged. Channels 1–2 had zero hits at 0.753 and 0.771 µm. Channels 51–52 were blank. Channel 102 had 10 hits at 4.988 µm with flags `0x200002` and no plotted value. The first and last measured centers were 0.790 and 4.951 µm in channels 3 and 101. The legacy coordinate on the same tile returned 100 measured channels and the two blank channels.
- Both the hostname in the frontend rewrite and the hostname suggested by the Render service name returned HTTP 404 on `/api/health`. No deployment action was taken.

## Calibrated API and browser verification — 2026-11-14

- The local API accepted the two deep-field D6 exposures below, rejected the incompatible Barnard’s Star D6 pair with HTTP 422, and returned matched-pixel variance and mask information. The final artifact mask permits SOURCE and FULLSAMPLE and excludes other flags. It retained 378/400 pixels in the accepted case at 100% nominal overlap.
- Chromium rendered both difference and mean co-add at 1440 px and the rejected Barnard’s Star pair at 320 px. The temporary browser harness supplied selected real archive observation records so the test did not depend on SIA returning them first. The current backend read the real FITS cutouts and matched calibration maps. See the `calibrated_*` captures in `outputs/verification`.
- Difference, mean, median, and sum were exercised via the API. Pair median equals mean. Propagated statistical variance assumes independent exposure noise. The app does not report an empirical SNR gain or validate source motion from the difference image.
- Full suite after restoring duplicate and distant-pointing request validation. 133 passed with three known Astropy fixture warnings. The focused calibration, cube, and comparison run passed 23 checks.

## Target validation — 2026-11-14

- All 18 named-target cache files contain the requested coordinate. An independent SIMBAD catalog query and FITS exposure epoch projection found 14 files where the expected target position is outside the field. The four RW Aurigae files contain the expected system position.
- Corrected archive searches staged nine D6 FITS samples separately. Each contains the corresponding predicted target position at the observation epoch. The WISE 0855 QR3 D6 query returned no rows. Aperture tests and their limitations are recorded in [TARGET_VALIDATION.md](docs/TARGET_VALIDATION.md).
- The existing 22-entry demo cache audit still reports 19 pass, three known warnings, and zero failures after adding coverage labels. FITS files and manifest URLs remained intact.
- Live DR1 cube API verification at Barnard’s Star’s predicted DR1 exposure position (269.4463524°, +4.7671159°). Tile 7945, zero-based pixel (97, 103), returned 29 measured, 70 without coverage, one flagged, and two blank channels. Channel 3 at 0.7900 µm returned 7.3446698 MJy/sr, one hit and SOURCE flag 2097152. The channel map center, spectrum, and original FITS sample agreed exactly. This is surface brightness of a co-added sky pixel.

## Demo refresh, browser, and deployment verification — 2026-11-14

- The staging tool independently reread each corrected FITS file, checked exposure and detector identity, verified native WCS coverage, and produced nine pass, zero warnings, zero failures. The original active manifest had the same SHA-256 before and after staging. The staged preview API returned two frames each for Barnard’s Star, RW Aurigae, R Draconis, and Epsilon Indi B, and one for WISE 0855. All nine were labeled real cached cutouts.
- Chromium checked loaded cache fallback under a simulated archive outage at 320, 375, 768, and 1440 CSS pixels. No horizontal document scroll. It rendered a 320 px empty state and an invalid-coordinate message, confirmed the reduced-motion CSS transition duration, and zoomed the focused image to 125% with a keyboard command. Screenshots are in `outputs/verification`.
- The production browser loaded both 2MASS and DSS2 Aladin imagery using the audited preview after removing the redundant eager CDN script. The selected coordinate marker, exact FITS footprint, and survey attribution appeared. The Aladin module remains lazy at 840.25 kB gzip. The main JavaScript bundle is 86.35 kB gzip.
- Loaded 2MASS imagery and attribution displayed at 320, 375, 768, and 1440 CSS pixels with no horizontal document overflow. Blocking the HiPS requests during survey switching at 320 px produced the in-panel error, Retry button, and external Aladin link. Captures are named `audited_context_*`.
- The full backend suite passed 133 tests with three existing Astropy fixture warnings. The accessibility and responsive source script passed 41 checks. The production build passed with the Aladin chunk-size warning.
- The configured public Render health endpoint returned HTTP 404. A public frontend URL and public deployment could not be verified.

## DR1 cube and baseline verification — 2026-11-14

- Comparison validation in progress. Six focused calibration and comparison tests passed. IRSA TAP asynchronous job 28334899 resolved D6 calibration plane `019f4f99-5f21-722d-bd8d-a6033df45708` to `spectral_wcs_D6_spx_cal-swcs-v5-2026-191.fits`. The 33,312,960-byte download matched archive MD5 `e665c189ad63ca0cd032c0797e8aabf2`.
- The actual CWAVE/CBAND maps, source masks, and variance layers loaded for seven cached D6 cutouts. The three distinct same-target pairs for Barnard’s Star, Epsilon Indi B, and R Draconis each had zero accepted aligned pixels at the provisional 90% passband overlap threshold. These results were obtained before the API was connected.
- A live SIA search and FITS cutout check at RA 270°, Dec +66.56° found one accepted DR1 deep-field D6 pair, `2025W18_1B_0242_2` (2025-04-30 02:40:21.675 UTC) and `2025W18_1B_0252_2` (2025-04-30 04:18:34.115 UTC). The verifier retained 397 of 400 aligned pixels, each with full nominal passband overlap. It used the same checksum-verified D6 calibration. The cutouts used 0.035° requests. Of the 28 queried records, 19 cutouts loaded and nine returned archive errors. This verification exercised the offline algorithm and archive inputs. This preceded the stricter artifact mask used by the API.

- `python -m pytest -q tests/test_demo_manifest_audit.py tests/test_stacking_and_spectrum.py`: 30 passed. The malformed FITS audit fixture intentionally triggered an Astropy warning.
- `python -m pytest -q tests/test_spectral_cube.py tests/test_demo_manifest_audit.py`: 17 passed, with the same fixture warning. The cube tests cover NESTED tile selection, missing tiles, HPX mapping, channel metadata and order, masking, native map sampling, and blank channels.
- Live IRSA SIA CSV searches at RA 269.45208°, Dec +4.69339° returned DR1 cube tile 7945 and dated DR1 spectral image records, including observation `2025W33_2C_0321_1`. The cube FITS file was downloaded and cached once.
- `GET /api/cube/spectrum?ra=269.45208&dec=4.69339&channel=1` returned HTTP 200 against that actual tile. At zero-based pixel (81, 118), 100 channels were measured and two were blank (51 and 52). Independent HTTP byte ranges confirmed the channel 1 archive value of 0.08370494097471237 MJy/sr, 13 hits and SOURCE flag 2097152. The 25 × 25 map center and extracted spectrum agreed exactly for channel 1.
- Frontend production build passed with the existing Aladin bundle size warning. The existing source-based UI check passed 41 checks.
- Chromium loaded the production frontend with an isolated current backend at 320, 375, 768, and 1440 CSS pixels. The measured spectrum and channel map loaded with no horizontal page overflow. Switching to channel 51 showed a blank map and a coverage message. Captures are in `outputs/verification/cube_*px.png`. At narrow widths the chart follows the map in the document flow.

## Observatory interface redesign

- Final inspector check: opened the catalog disclosure with Enter, enabled the overlay, and inspected the demo source, separation, and provenance alongside the plotted markers. Submitted invalid coordinates and confirmed the error banner appeared and the previous frame cleared. Production build and 41 UI source checks passed after the changes.

- Glass styling pass: verified no page-level horizontal overflow at 320, 375, 768, and 1280 pixels. Opened the target and inspector panels at the three narrow widths. At desktop, selecting an observation in the target panel updated the timeline, and switching to Aladin showed live 2MASS imagery, the footprint, and attribution. Inspected fresh browser captures of the loaded workspace and checked the initial empty/loading state. The Aladin error path was not induced during this pass.

- Production build passed with the existing lazy Aladin chunk size warning. The source-based UI script passed 41 checks and Git reported no whitespace errors.
- Captured and inspected running explorer and Aladin screenshots at 320, 375, 768, and 1280 CSS pixels. Opened target and inspector panels at all three narrow widths and inspected the open desktop inspector while spectrum data loaded. Verified the target filter shows a no-results message and rechecked the native image at 320 pixels after fixing resize distortion.
- The explorer displayed a cached observation and live 2MASS context. Full keyboard traversal, external archive failure injection, mobile timeline playback, and end-to-end reduced-motion testing were not repeated for this revision. Rapid viewport changes produced a transient Aladin framing issue in the capture sequence.

## 2026-11-14 — Sky-context update (supersedes the historical summary below)

- Follow-up browser check: the native timeline slider changed from epoch 1 to epoch 2 on Right Arrow in a 60-observation live search. The native canvas, updated controls and metadata panel were inspected at a 375px viewport; the archive link and WCS reference labels were present. The connectivity badge wording was corrected after that observation and was build-checked, not separately browser-inspected.
- All five preset context views were subsequently inspected individually with the archive-search endpoint deliberately unavailable and cached demonstration cutouts. For each, Aladin displayed the corresponding ICRS coordinates, a distinct amber target marker and a cyan footprint on rendered 2MASS imagery: Barnard's Star 269.45208°, +4.69339°; WISE 0855 133.79513°, −7.24515°; RW Aurigae 76.95420°, +30.40140°; R Draconis 248.33750°, +66.70420°; Epsilon Indi B 330.84000°, −56.78600°. Separate Astropy tests compare each cached footprint's corners with its FITS WCS. A plotted coordinate does not establish source identity.
- Contrast follow-up: calculated WCAG relative-luminance ratios for opaque Tailwind colors: white on cyan-600 is 3.68:1 and on cyan-500 is 2.43:1; white on cyan-700 is 5.36:1 and on cyan-800 is 7.27:1. Updated the affected white-on-cyan actions, including their hover states. The search button gradient endpoints use cyan-700 and indigo-700 (white on indigo-700: 7.90:1). These spot checks do not constitute a full contrast audit. The production build and 41 source checks passed after the changes.
- Catalog evidence follow-up: in an offline-search preview, enabling the reference overlay showed the nearest listed demo source, its separation and demo provenance, and warned that the demo coordinates do not independently confirm identity. The catalog projection request returned HTTP 200. Subsequent wording changes clarified that coordinates are projected as provided and that the curated demo list is not necessarily Gaia-only.
- Catalog feedback follow-up: the browser displayed the projected demo result; after the isolated backend was stopped and the overlay was toggled, it showed the catalog request failure and retry instruction. Loading, empty-or-unavailable, and projection states were implemented but were not separately timed or induced in that browser check. Build and source-based accessibility checks passed.
- Backend: `python -m pytest -q`: 110 passed, two Astropy FITSFixedWarnings. Coverage includes rotated pixel-edge WCS corners across the RA seam, five cached preset cutouts, unavailable WCS, and catalog coordinate projection.
- The committed backend at `ee79492` was exported to an isolated directory along with the manifest's 22 existing demonstration cutouts: `python -m pytest -q` passed 107 tests with two Astropy FITSFixedWarnings. This used the existing Python environment; tests that exist only in the uncommitted working tree were excluded. The isolated directory was removed.
- Frontend: `npm run build` passed. Aladin is a separate lazy chunk (about 2.6 MB minified / 840 KB gzip), producing Vite's large-chunk warning. `node scripts/verify_accessibility_and_responsive.mjs`: 41 source checks passed; these are not a complete accessibility audit.
- The committed frontend at `7808f84` was also exported into a temporary isolated directory and built successfully using the existing installed dependencies, independently of the uncommitted source edits. The temporary directory was removed. This was not a fresh dependency installation.
- Browser: inspected the native cached SPHEREx image and real 2MASS sky imagery at desktop and a 375-pixel mobile viewport. The selected RW Aur coordinates matched Aladin's reported position; all five presets were selected and their displayed target coordinates checked. Cached preset footprint calculations were independently compared with Astropy WCS in tests. A manual position near RA 359.999 degrees showed the footprint across the RA seam. The screenshots do not independently establish an astronomical source identification.
- A deliberately invalid survey endpoint showed a contextual failure and Retry; switching to DSS2 rendered imagery. Direct checks of the IRSA mirror metadata and all-sky image returned HTTP 200. A subsequent Chrome browser resource inventory showed actual requests for 2MASS properties, the all-sky image, the coverage map, and several order-6 and order-9 image tiles while the RW Aur sky visibly rendered; Chrome's captured console had no warnings or errors. The resource inventory does not expose individual HTTP status codes, so it is not a complete network audit.
- Keyboard Tab and Enter navigation and visible focus were exercised for the search/analysis flow. In a separate temporary preview, the reduced-motion CSS rule was forced on by the development server: the browser reported 0.00001s animation and transition durations, one animation iteration, and Right Arrow moved the timeline from epoch 1 to 2. The actual operating-system media preference was not emulated (the browser reported it as false), so preference detection remains unverified. Physical screen-reader testing was not performed. Contrast and complete keyboard coverage have not been formally audited.

The following sections are historical records and their counts do not describe the current revision.

**Execution Timestamp:** 2026-11-14T23:27:00Z  
**Platform:** Windows 11 / Python 3.11.4 / Node.js v22.19.0  
**Test Suite Status:** 93 backend pytest tests passed (with 2 Astropy FITSFixedWarnings) in 10.11s | 41 automated UI accessibility checks passed | Frontend Build: 1,497 modules transformed, 0 errors in 2.55s | Demo Assets: 22/22 verified | NASA/IPAC IRSA SIA: 200 OK

---

## 1. Automated Backend Test Suite (`python -m pytest -v`)

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.2.0, pluggy-1.7.0 -- python.exe
cachedir: .pytest_cache
rootdir: backend
plugins: anyio-4.12.1, zarr-3.1.6
collecting ... collected 93 items

backend/tests/test_comparison.py::test_comparison_eligibility PASSED     [  1%]
backend/tests/test_comparison.py::test_comparison_ra_boundary_wrapping PASSED [  2%]
backend/tests/test_comparison.py::test_compute_difference_frame PASSED   [  3%]
backend/tests/test_comparison.py::test_compute_difference_frame_nan_handling PASSED [  4%]
backend/tests/test_comparison.py::test_compute_difference_frame_wcs_reproject PASSED [  5%]
backend/tests/test_comparison.py::test_compute_difference_frame_fft_shift_fallback PASSED [  6%]
backend/tests/test_comparison.py::test_compute_difference_frame_spectral_3d_wcs PASSED [  7%]
backend/tests/test_comparison.py::test_compute_difference_frame_rotated_wcs PASSED [  8%]
backend/tests/test_coordinates.py::test_parse_decimal_coordinates PASSED [  9%]
backend/tests/test_coordinates.py::test_parse_string_decimal PASSED      [ 10%]
backend/tests/test_coordinates.py::test_parse_sexagesimal_hms PASSED     [ 12%]
backend/tests/test_coordinates.py::test_parse_sexagesimal_colon_format PASSED [ 13%]
backend/tests/test_coordinates.py::test_parse_sexagesimal_space_format PASSED [ 14%]
backend/tests/test_coordinates.py::test_parse_challenge_prompt_unicode_coordinates PASSED [ 15%]
backend/tests/test_coordinates.py::test_empty_coordinate_input PASSED    [ 16%]
backend/tests/test_coordinates.py::test_ra_wrapping PASSED               [ 17%]
backend/tests/test_coordinates.py::test_dec_out_of_range PASSED          [ 18%]
backend/tests/test_coordinates.py::test_invalid_input PASSED             [ 19%]
backend/tests/test_coordinates.py::test_format_sexagesimal PASSED        [ 20%]
backend/tests/test_demo_resilience.py::test_demo_manifest_endpoint PASSED [ 21%]
backend/tests/test_demo_resilience.py::test_offline_observation_discovery_fallback PASSED [ 23%]
backend/tests/test_demo_resilience.py::test_diff_on_demo_epochs PASSED   [ 24%]
backend/tests/test_demo_resilience.py::test_webp_frame_and_diff_endpoints PASSED [ 25%]
backend/tests/test_fits_processing.py::test_load_and_extract_image PASSED [ 26%]
backend/tests/test_fits_processing.py::test_extract_wcs PASSED           [ 27%]
backend/tests/test_fits_processing.py::test_evaluate_quality_flags PASSED [ 28%]
backend/tests/test_fits_processing.py::test_calculate_pixel_stats PASSED [ 29%]
backend/tests/test_fits_processing.py::test_asinh_and_zscale_stretch PASSED [ 30%]
backend/tests/test_fits_processing.py::test_render_image_to_base64_png PASSED [ 31%]
backend/tests/test_fits_processing.py::test_render_image_to_base64_webp PASSED [ 32%]
backend/tests/test_fits_processing.py::test_extract_astropy_wcs_celestial PASSED [ 34%]
backend/tests/test_fits_processing.py::test_render_image_to_base64_float_sanitization PASSED [ 35%]
backend/tests/test_fits_processing.py::test_spherex_documented_flags_distinguish_source_mask PASSED [ 36%]
backend/tests/test_fits_processing.py::test_apply_diverging_colormap PASSED [ 37%]
backend/tests/test_health.py::test_root PASSED                           [ 38%]
backend/tests/test_health.py::test_health PASSED                         [ 39%]
backend/tests/test_health.py::test_demo_presets PASSED                   [ 40%]
backend/tests/test_image_registration.py::test_identical_images PASSED   [ 41%]
backend/tests/test_image_registration.py::test_known_shift_recovery PASSED [ 42%]
backend/tests/test_image_registration.py::test_different_dimensions PASSED [ 43%]
backend/tests/test_image_registration.py::test_nan_and_inf_robustness PASSED [ 45%]
backend/tests/test_image_registration.py::test_constant_image PASSED     [ 46%]
backend/tests/test_integration.py::test_full_explorer_flow PASSED        [ 47%]
backend/tests/test_integration.py::test_invalid_coordinates_flow PASSED  [ 48%]
backend/tests/test_irsa_client.py::test_irsa_client_parse PASSED         [ 49%]
backend/tests/test_irsa_client.py::test_observation_registry_insertion PASSED [ 50%]
backend/tests/test_science.py::test_aperture_photometry_gaussian_source PASSED [ 51%]
backend/tests/test_science.py::test_lightcurve_variability_classification PASSED [ 52%]
backend/tests/test_science.py::test_astrometric_motion_measurement PASSED [ 53%]
backend/tests/test_science.py::test_catalog_endpoint_barnard PASSED      [ 54%]
backend/tests/test_science.py::test_photometry_endpoint_demo PASSED      [ 56%]
backend/tests/test_science.py::test_motion_endpoint_on_demo_epochs PASSED [ 57%]
backend/tests/test_science.py::test_discovery_report_endpoint PASSED     [ 58%]
backend/tests/test_science.py::test_photometry_preset_differentiation PASSED [ 59%]
backend/tests/test_scientific_audit_regression.py::test_priority_1_flags_metadata_and_source_mask_distinction PASSED [ 60%]
backend/tests/test_scientific_audit_regression.py::test_priority_2_photometry_wcs_target_measurement_and_variance PASSED [ 61%]
backend/tests/test_scientific_audit_regression.py::test_priority_2_spectrum_interpolation_labeled_correctly PASSED [ 62%]
backend/tests/test_scientific_audit_regression.py::test_priority_3_astrometric_motion_wcs_target_tracking PASSED [ 63%]
backend/tests/test_scientific_audit_regression.py::test_priority_4_differencing_lvf_compatibility_and_reprojection_error PASSED [ 64%]
backend/tests/test_scientific_audit_regression.py::test_priority_5_stacking_detector_compatibility_and_variance PASSED [ 65%]
backend/tests/test_scientific_audit_regression.py::test_priority_6_gaia_provenance_explicit_labeling PASSED [ 67%]
backend/tests/test_scientific_audit_regression.py::test_priority_1_extract_source_mask PASSED [ 68%]
backend/tests/test_scientific_audit_regression.py::test_priority_2_aperture_photometry_boundary_and_wcs_wave PASSED [ 69%]
backend/tests/test_scientific_audit_regression.py::test_priority_3_astrometric_vector_components_and_no_wandering PASSED [ 70%]
backend/tests/test_scientific_audit_regression.py::test_priority_5_stacking_variance_with_masked_pixels PASSED [ 71%]
backend/tests/test_scientific_audit_regression.py::test_priority_1_source_mask_background_exclusion_without_aperture_rejection PASSED [ 72%]
backend/tests/test_scientific_audit_regression.py::test_priority_2_discovery_report_sed_truthfulness PASSED [ 73%]
backend/tests/test_scientific_audit_regression.py::test_priority_3_pointing_shift_not_presented_as_target_motion PASSED [ 74%]
backend/tests/test_scientific_audit_regression.py::test_priority_1_lightcurve_source_mask_background_exclusion PASSED [ 75%]
backend/tests/test_scientific_audit_regression.py::test_audit_photometry_target_wcs_failure_returns_unavailable PASSED [ 75%]
backend/tests/test_scientific_audit_regression.py::test_audit_fits_processing_wavelength_and_mask_semantics PASSED [ 76%]
backend/tests/test_scientific_audit_regression.py::test_audit_spectrum_truthfulness_and_documented_bb_fit PASSED [ 77%]
backend/tests/test_scientific_audit_regression.py::test_audit_spectrum_truthfulness_tightened_temperature_and_neutral_shapes PASSED [ 78%]
backend/tests/test_scientific_audit_regression.py::test_audit_stacking_snr_improvement_uncensored PASSED [ 79%]
backend/tests/test_scientific_audit_regression.py::test_audit_nan_inf_preserved_as_masks_not_fabricated PASSED [ 80%]
backend/tests/test_scientific_audit_regression.py::test_audit_motion_requested_target_never_substitutes_brightest_peak PASSED [ 81%]
backend/tests/test_stacking_and_spectrum.py::test_compute_coadd_stack_mean_median_sum PASSED [ 82%]
backend/tests/test_stacking_and_spectrum.py::test_compute_coadd_stack_nan_handling PASSED [ 83%]
backend/tests/test_stacking_and_spectrum.py::test_compute_coadd_stack_wcs_reproject PASSED [ 84%]
backend/tests/test_stacking_and_spectrum.py::test_spectrum_generation_102_channels PASSED [ 86%]
backend/tests/test_stacking_and_spectrum.py::test_spectrum_endpoint_barnard PASSED [ 87%]
backend/tests/test_stacking_and_spectrum.py::test_spectrum_endpoint_wise0855_brown_dwarf PASSED [ 88%]
backend/tests/test_stacking_and_spectrum.py::test_spectrum_endpoint_sexagesimal PASSED [ 89%]
backend/tests/test_stacking_and_spectrum.py::test_spectrum_endpoint_invalid_coords PASSED [ 90%]
backend/tests/test_stacking_and_spectrum.py::test_stack_frames_endpoint_on_demo_epochs PASSED [ 91%]
backend/tests/test_stacking_and_spectrum.py::test_stack_frames_endpoint_validation PASSED [ 92%]
backend/tests/test_stacking_and_spectrum.py::test_stack_frames_endpoint_webp_and_median PASSED [ 93%]
backend/tests/test_stacking_and_spectrum.py::test_compute_coadd_stack_edge_cases PASSED [ 94%]
backend/tests/test_stacking_and_spectrum.py::test_stack_frames_endpoint_duplicate_frames_rejected PASSED [ 95%]
backend/tests/test_stacking_and_spectrum.py::test_compute_coadd_stack_non_overlapping_wcs_raises PASSED [ 96%]
backend/tests/test_stacking_and_spectrum.py::test_stack_frames_endpoint_distant_pointings_rejected PASSED [ 97%]
backend/tests/test_stacking_and_spectrum.py::test_spectrum_endpoint_fov_validation PASSED [ 98%]
backend/tests/test_stacking_and_spectrum.py::test_robust_noise_sigma_point_source_insensitivity PASSED [100%]

============================== warnings summary ===============================
backend/tests/test_scientific_audit_regression.py::test_audit_fits_processing_wavelength_and_mask_semantics
backend/tests/test_scientific_audit_regression.py::test_audit_fits_processing_wavelength_and_mask_semantics
  site-packages\astropy\wcs\wcs.py:695: FITSFixedWarning: The WCS transformation has more axes (3) than the image it is associated with (2)
    warnings.warn(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 93 passed, 2 warnings in 10.11s =======================
```

---

## 2. Frontend Production Build (`cd frontend && npm run build`)

```text
> spherex-discovery@1.0.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 1497 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.96 kB │ gzip:  0.60 kB
dist/assets/index-8rk7elrb.css   33.29 kB │ gzip:  6.62 kB
dist/assets/index-DyTu7ZfP.js   301.60 kB │ gzip: 80.64 kB
✓ built in 2.55s
```

---

## 3. Automated UI Accessibility & Responsive Verification (`node scripts/verify_accessibility_and_responsive.mjs`)

```text
============================================================
SPHEREx Discovery Accessibility & Responsive Verification
============================================================

[PASS] index.css defines global :focus-visible indicators
[PASS] index.css respects prefers-reduced-motion media query
[PASS] index.css defines 320px minimum viewport safety constraint
[PASS] index.css prevents horizontal document scroll
[PASS] CanvasViewer implements handleKeyDown handler
[PASS] CanvasViewer implements Arrow key panning
[PASS] CanvasViewer implements "+" / "=" zoom in
[PASS] CanvasViewer implements "-" / "_" zoom out
[PASS] CanvasViewer implements "0" reset view
[PASS] CanvasViewer has aria-live="polite" region for screen reader announcements
[PASS] CanvasViewer container has tabIndex={0} keyboard focusability
[PASS] CanvasViewer has high-visibility focus ring
[PASS] CanvasViewer viewer switcher uses role="tablist" and role="tab"
[PASS] SpectrumChart includes expandable <details> disclosure
[PASS] SpectrumChart includes "View Accessible Data Table" summary
[PASS] SpectrumChart data table has role="table"
[PASS] SpectrumChart table headers have scope="col"
[PASS] SpectrumChart table includes screen-reader caption
[PASS] LightCurveChart includes expandable <details> disclosure
[PASS] LightCurveChart includes "View Accessible Data Table" summary
[PASS] LightCurveChart data table has role="table"
[PASS] LightCurveChart table headers have scope="col"
[PASS] Header navigation uses role="tablist"
[PASS] Header navigation buttons use role="tab"
[PASS] Header wraps gracefully on narrow viewports
[PASS] App implements mobilePanel state for deliberate panel stacking
[PASS] App implements mobile tabs for Canvas, Target, and Telemetry
[PASS] App displays side-by-side multi-dock layout on lg (>=1024px) screens
[PASS] SearchControls uses responsive full width on mobile and 320px on desktop
[PASS] MetadataPanel uses responsive full width on mobile and 320px on desktop
[PASS] ComparisonView operation mode switcher uses role="tablist"
[PASS] ComparisonView operation mode buttons use role="tab"
[PASS] ComparisonView includes accessible metrics table disclosure
[PASS] ComparisonView supports diverging colormap toggle for difference frames
[PASS] GuidedTourModal has role="dialog" and aria-modal="true"
[PASS] DiscoveryReportModal has role="dialog" and aria-modal="true"
[PASS] SpectrumChart includes 102-channel spectrophotometric continuum accessible table toggle
[PASS] SpectrumChart manages accessible table dataset state between observed bands and continuum channels
[PASS] CanvasViewer generates dynamic offset coordinates in announcements to prevent consecutive speech silence
[PASS] CanvasViewer announces zoom limit boundaries to screen readers
[PASS] App synchronizes active observation with URL search params on timeline navigation

============================================================
Results: 41 passed, 0 failed
============================================================
```

---

## 4. Demonstration Assets Verification (`python scripts/verify_demo.py`)

```text
============================================================
VERIFYING SPHEREx DISCOVERY DEMONSTRATION DATASET
============================================================
Total entries in manifest: 22

[1/22] Documentation Example (spherex_dr1 | SPHEREx-D1) - [OK] FITS Shape: (8, 20), Mean Flux: 0.6486 MJy/sr
[2/22] Documentation Example (spherex_dr1 | SPHEREx-D4) - [OK] FITS Shape: (20, 20), Mean Flux: 0.4505 MJy/sr
[3/22] Documentation Example (spherex_qr3 | SPHEREx-D4) - [OK] FITS Shape: (20, 20), Mean Flux: 0.2939 MJy/sr
[4/22] Documentation Example (spherex_qr3 | SPHEREx-D1) - [OK] FITS Shape: (20, 20), Mean Flux: 2.0423 MJy/sr
[5/22] WISE 0855 (spherex_dr1 | SPHEREx-D3) - [OK] FITS Shape: (20, 20), Mean Flux: 0.1788 MJy/sr
[6/22] WISE 0855 (spherex_dr1 | SPHEREx-D6) - [OK] FITS Shape: (20, 20), Mean Flux: 0.7434 MJy/sr
[7/22] Barnard's Star (spherex_dr1 | SPHEREx-D6) - [OK] FITS Shape: (20, 20), Mean Flux: 0.4104 MJy/sr
[8/22] Barnard's Star (spherex_dr1 | SPHEREx-D3) - [OK] FITS Shape: (20, 20), Mean Flux: 0.4072 MJy/sr
[9/22] Barnard's Star (spherex_qr3 | SPHEREx-D3) - [OK] FITS Shape: (20, 20), Mean Flux: 0.6118 MJy/sr
[10/22] Barnard's Star (spherex_qr3 | SPHEREx-D6) - [OK] FITS Shape: (20, 20), Mean Flux: 3.2555 MJy/sr
[11/22] Epsilon Indi B (spherex_dr1 | SPHEREx-D6) - [OK] FITS Shape: (20, 20), Mean Flux: 0.7249 MJy/sr
[12/22] Epsilon Indi B (spherex_dr1 | SPHEREx-D3) - [OK] FITS Shape: (20, 20), Mean Flux: 5.0138 MJy/sr
[13/22] Epsilon Indi B (spherex_qr3 | SPHEREx-D3) - [OK] FITS Shape: (20, 20), Mean Flux: 1.4518 MJy/sr
[14/22] Epsilon Indi B (spherex_qr3 | SPHEREx-D6) - [OK] FITS Shape: (20, 20), Mean Flux: 0.6907 MJy/sr
[15/22] RW Aurigae (spherex_dr1 | SPHEREx-D1) - [OK] FITS Shape: (20, 20), Mean Flux: 1.6113 MJy/sr
[16/22] RW Aurigae (spherex_dr1 | SPHEREx-D4) - [OK] FITS Shape: (20, 21), Mean Flux: 4.9404 MJy/sr
[17/22] RW Aurigae (spherex_qr3 | SPHEREx-D1) - [OK] FITS Shape: (20, 20), Mean Flux: 1.1126 MJy/sr
[18/22] RW Aurigae (spherex_qr3 | SPHEREx-D4) - [OK] FITS Shape: (20, 20), Mean Flux: 2.9775 MJy/sr
[19/22] R Draconis (spherex_dr1 | SPHEREx-D6) - [OK] FITS Shape: (20, 20), Mean Flux: 0.1325 MJy/sr
[20/22] R Draconis (spherex_dr1 | SPHEREx-D3) - [OK] FITS Shape: (20, 20), Mean Flux: 0.2633 MJy/sr
[21/22] R Draconis (spherex_qr3 | SPHEREx-D3) - [OK] FITS Shape: (20, 20), Mean Flux: 0.2092 MJy/sr
[22/22] R Draconis (spherex_qr3 | SPHEREx-D6) - [OK] FITS Shape: (20, 20), Mean Flux: 0.2830 MJy/sr

============================================================
[SUCCESS] All demonstration assets verified and valid!
============================================================
```

---

## 5. Environment & Remote Connectivity (`python scripts/verify_environment.py`)

```text
============================================================
SPHEREx Discovery Environment Verification
============================================================

--- System Tools ---
[OK] Python: Python 3.11.4
[OK] Node.js: v22.19.0
[OK] npm: 10.9.3
[OK] Git: git version 2.54.0.windows.1

--- Python Dependencies ---
[OK] Python package 'fastapi': 0.128.8
[OK] Python package 'uvicorn': 0.54.0
[OK] Python package 'httpx': 0.28.1
[OK] Python package 'astropy': 8.0.2
[OK] Python package 'numpy': 2.4.6
[OK] Python package 'scipy': 1.15.3
[OK] Python package 'PIL': 12.1.1
[OK] Python package 'pytest': 9.2.0
[OK] Python package 'certifi': 2026.01.04

--- NASA/IPAC Connectivity ---
Testing IRSA SIA connectivity to: https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS...
[OK] IRSA SIA endpoint reachable and returned valid CSV data (status 200)

============================================================
[SUCCESS] All environment requirements passed!
============================================================
```

---

## 6. Verification Scope & Limitations Notice
- **Automated Verification:** All 93 backend pytest tests passed (with 2 Astropy `FITSFixedWarning` warnings on 3D WCS dimension reduction tests); 41 automated UI accessibility and responsive checks passed; 22/22 demonstration assets verified valid; frontend production build succeeded with 1,497 modules transformed and 0 errors; environment verification confirmed live IRSA SIA HTTP 200 connectivity outside restricted network.
- **Manual Verification Status:** No manual physical visual inspection or interactive screen-reader (NVDA/JAWS/VoiceOver) testing was performed in this session. Visual rendering relies on automated headless layout assertions and previously saved PNG screenshots in `docs/screenshots/`.


## Current session verification (2026-11-14)

- Full backend: 98 passed, 2 Astropy FITSFixedWarnings with normal local networking. Restricted execution stalled on the first TestClient request and was interrupted.
- Frontend production build passed; accessibility/responsive source-check script passed 41 checks; demo asset validator passed 22/22. These checks do not establish WCAG conformance or target-object scientific validity.
- IRSA SIA environment probe returned HTTP 200 with CSV using normal networking.
- Desktop and 375px viewer layouts were visually inspected, including the mobile science panel. An updated-backend preview showed an IRSA search result. The final observed-band table correction was built but not rechecked visually. Physical screen-reader audio was not tested.

- Cache regression: verifies that a legacy entry is not reused as a live cutout and that differing field sizes have distinct keys. The demo cache remains fixed coverage.
- Release-selection regression: empty selected-release searches do not silently retry across all releases for photometry or spectrum.


## Wavelength safety follow-up (2026-11-14)
- Backend: 98 passed, 2 Astropy FITSFixedWarnings with normal local networking. Frontend build passed; the 41 source-based accessibility checks and 22 demo asset checks passed.
- Endpoint tests now verify HTTP 422 for difference and co-addition until per-pixel spectral compatibility is established. Numerical difference and stack unit tests still exercise their internal algorithms; they do not validate science compatibility. WCS-WAVE checks reject missing mapping cards and positions outside the lookup grid.
- Visual checks predate this safety notice; the updated notice and new unavailable state have not been manually inspected.


## Aperture safety follow-up (2026-11-14)
- Full backend: 99 passed, 2 Astropy FITSFixedWarnings with normal local networking. Tests cover subpixel full apertures, clipped/masked apertures and a source-masked annulus.
- Some cached observations yield no usable background; their photometry and derived observed-band metrics are unavailable. Existing fixture tests no longer assume a target name guarantees a measurement or variability.

## Cloud and clean-checkout verification (2026-11-15)

- Backend: 276 passed and 4 skipped on the working checkout; a clean checkout without downloaded FITS data passed 269 tests and skipped 11. Three expected Astropy warnings arose from malformed-data and WCS test fixtures.
- Frontend production build and seven focused navigation, blink, CSV, sharing, cache, provenance, and spectrum checks passed. The build reports a large Aladin bundle.
- A real Epsilon Indi D5 field pair returned 485 of 529 valid field pixels for difference, mean and sum at the checked position and field size. These are field comparisons, not a confirmed detection or motion measurement.
- IRSA DataLink and cross-mirror checks established example calibration associations for D1, D2 and D4; reuse for other images with the same detector and UUID is an inference, as documented in the detector calibration audit. A checked RW Aurigae D1 field pair retained 218/529 pixels; the screenshot pair failed wavelength compatibility. A checked Epsilon Indi D2 field pair retained 486/529 pixels. Neither field test confirms a target detection or motion.
- Live deep-field SIA searches timed out. Unknown calibration identifiers remain unavailable, and visual end-to-end testing of the newest controls is outstanding.
