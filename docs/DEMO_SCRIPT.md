# SPHEREx Discovery judge walkthrough

**Planet X and SPHEREx** asks for a public-facing web tool that helps people inspect how SPHEREx images of the sky change over time. The public app uses NASA/IPAC archive data. The prepared local demonstration below uses staged copies of those data. [Challenge brief reproduced by NASA Space Apps Lucerne](https://www.spaceappschallenge.ch/) · [Regional challenge listing](https://www.spaceappsulaanbaatar.com/challenges)

## Public recording · about one minute

Open these three tabs before recording and let them finish loading. The free backend may need a minute to wake. Keep the [public home page](https://spherex-discovery-2026.vercel.app/) and [source repository](https://github.com/agenttaffy/spherex-discovery-2026) in the submission.

1. [Epsilon Indi Explorer](https://spherex-discovery-2026.vercel.app/?target=epsilon_indi_b&ra=331.09813086506205&dec=-56.801144263858404&fov=0.04). Identify the date, detector, and image source. Play for a few seconds, then pause. Optionally toggle **Gaia DR3** for reference stars. Explain that the timeline displays dated infrared observations and that the Gaia markers come from a reference catalog.
2. [Epsilon Indi Difference & Stack](https://spherex-discovery-2026.vercel.app/?ra=331.09813086506205&dec=-56.801144263858404&fov=0.04&tab=diff). Click **Try checked Epsilon Indi D5 field pair**, then switch to **Co-add**. The tested 2.4′ pair retained 485 of 529 pixels in both modes. The checkerboard shows excluded pixels. The results describe the field and do not establish object motion.
3. [M57 in 102 Bands](https://spherex-discovery-2026.vercel.app/?tab=cube&ra=283.39617&dec=33.02918). Point to the measured spectrum and channel map. The tested sky pixel had measurements in 100 of the 102 channel slots. The DR1 cube combines data across dates. The channel slider changes wavelength.

If time allows, open **Aladin context** in Explorer and select **AllWISE color** for a comparison sky survey. If the archive badge reports failed search, use the preloaded field. Saved observation lists are partial, and the app shows their provenance separately from the cloud source of a displayed image.

## Before the timer

Use a checkout containing the portable preview. Follow the [Windows prerequisites and dependency setup](../README.md#preview-a-refreshed-demo-cache), then run `python scripts/bootstrap_demo_data.py --with-comparisons` with internet access. It downloads 114,042,240 bytes of FITS for the ten observations, D5 pair, and D5/D6 maps. Verify a prepared cache without network access using `python scripts/bootstrap_demo_data.py --check-only --with-comparisons`.

Then start the preview.

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/start-demo.ps1 -Dataset Preview -ApiPort 18100 -AppPort 15173 -NoBrowser
~~~

Open [the local app](http://127.0.0.1:15173/) and confirm **Cached demo** in the header. The [manifest response](http://127.0.0.1:15173/api/demo/manifest) should show 10 cutouts and five presets. Open the four core tabs below and leave WISE Blink in front. Load both cube samples before presenting so a slow archive response stays outside the timed segment.

| Tab | Open before presenting |
|---|---|
| WISE 0855 blink | [Blink](http://127.0.0.1:15173/?target=wise_0855&tab=blink) |
| Calibrated comparison | [Difference & Stack](http://127.0.0.1:15173/?target=wise_0855&tab=diff) |
| Barnard’s Star cube | [Spectral Cube](http://127.0.0.1:15173/?target=barnards_star&tab=cube), then **Load spectrum** |
| R Draconis cube | [Spectral Cube](http://127.0.0.1:15173/?target=r_draconis&tab=cube), then **Load spectrum** and choose **51 · Blank in DR1** |
| Optional sky context | [WISE 0855 Explorer](http://127.0.0.1:15173/?target=wise_0855), then **Aladin context** or **Sky Context** |

## Timed walkthrough · 3:30

### 0:00–0:20 · Introduce the app

Show the **Cached demo** header and the WISE 0855 field. On a narrow screen, scroll below the image to reach the observation selector and playback controls.

> “For Planet X and SPHEREx, we built a tool that lets you flip between dated infrared images of the same sky field. This local preview has two archived epochs for each of the five challenge fields.”

### 0:20–1:10 · Blink two dated WISE 0855 fields

In **Blink**, use **Jump to observation by date and detector** to show **2025-05-05 · SPHEREx-D6** and **2026-05-09 · SPHEREx-D6**. Point to the date and detector above the image and **Catalog prediction at exposure** below it. The amber square marks the catalog position propagated to that exposure. The blue crosshair marks the cutout center. Use **Play time-lapse**, then **Pause time-lapse** after a few flips. Open **Target photometry unavailable**.

> “The amber square comes from a catalog prediction for that date. Its position inside the image tells us where to look. The source identity remains unconfirmed, and blinking these two fields does not establish motion or variability.”

### 1:10–2:10 · Show the comparison guard and an accepted D5 pair

Switch to the prepared **Difference & Stack** tab. Briefly point to the WISE rejection that says no aligned, unmasked pixel pairs meet the passband overlap requirement. Select **Epsilon Indi B · SPHEREx D5 · DR1**. The fixed cutouts are dated **2025-04-24** and **2026-04-24** UTC. Expand **IRSA spectral WCS · 207/225 pixels matched** to show the archive links, plane UUID, and MD5. Select **Co-add** with **Mean** and confirm the same matched count.

> “A matching detector name alone can’t tell us whether the same wavelengths were measured at each pixel. The app rejected the WISE pair. This D5 field pair passed for 207 of 225 pixels. We can subtract or combine those pixels. Epsilon Indi Ba and Bb remain unresolved, so this establishes no detection, target flux, motion, or variability.”

### 2:10–3:05 · Compare two co-added sky-pixel samples

Switch to the two prepared **Spectral Cube** tabs. Point out the requested coordinate, the sampled HPX pixel, and the coverage line. Barnard’s Star’s preview coordinate has **8 measured, 90 without usable coverage, 2 flagged, and 2 blank**. R Draconis’s preview coordinate has **0 measured, 100 without usable coverage, and 2 blank**. Show channel **51 · Blank in DR1**. With the cache active, point to **Cached DR1 sky-pixel preview** and optionally open **Cache provenance**. If the archive answers, say **IRSA archive result** and show the counts it returns.

> “These are 102 actual DR1 channel slots in a cube built by combining observations. The sample is surface brightness at one sky pixel, with no single observation date or confirmed source association. Available channels vary by position. Blank and flagged channels stay as gaps.”

### 3:05–3:30 · Context and close

Once the prepared context tab shows the sky image, show the survey credit and cyan FITS footprint, then return to **Canvas**. If the service is slow or unavailable, show the cached demonstration field in **Canvas**.

> “Context imagery helps orient the field. The dated FITS images and calibration checks are what let us compare the SPHEREx observations. This demo runs locally from verified archive samples.”

## Run the local D5 example

The comparison tab is [Difference & Stack](http://127.0.0.1:15173/?target=wise_0855&tab=diff). The pair’s FITS URLs and SHA-256 values are in the [D5 pair manifest](../data/manifests/d5_comparison.json). If the view reports **Eligible D5 pair unavailable**, run the comparison integrity check from the setup above. Rerun the comparison bootstrap if inputs are missing, then reopen the view. This pair is separate from the ten preview frames. Keep the 378/400 D6 deep-field control as supporting evidence for judge questions. [Calibration evidence](DETECTOR_CALIBRATION.md)

| Input | Local cache path |
|---|---|
| 2025-04-24 22:10:56.336 UTC | `data/cache/demo-comparison/7fad22722d3beab1d4d3680b7d6a939d3946ebc59fbe4ead1fe22400f45239ed.fits` |
| 2026-04-24 21:21:00.091 UTC | `data/cache/demo-comparison/fd63b5f4ead244b6c5fb2e19bcea29d09260274bad069421d9fa77db5c6b3fcd.fits` |
| IRSA D5 spectral calibration | `data/cache/spectral-calibration/spectral-d59bd98b5d1d14ae8d74499b1c1ccb3f.fits` |

## Offline Spectral Cube

The compact preview covers the [five staged coordinates](CHALLENGE_REQUIREMENTS.md#dr1-cube-coverage), within 0.000005° on each axis, with a native 25 × 25 map window per channel. Keep the preset coordinates unchanged to use it. The cube tries the archive first. The prepared demo can show these five samples with archive access disabled. Other positions can require internet access, as can Aladin remote surveys and live query mode. If the cube archive fails outside the preview coordinates, the app reports the archive error. The [source records](../data/manifests/cube_preview_sources.json) identify the exact tiles, extraction positions, and archive checksums or ETags.

## After the demo

Stop the launcher-owned servers from the same repository root.

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/stop-demo.ps1
~~~
