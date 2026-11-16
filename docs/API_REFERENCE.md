# SPHEREx Discovery — REST API Reference

Base URL: `http://localhost:8000/api`  
Interactive OpenAPI / Swagger UI: `http://localhost:8000/docs`

---

## 1. System & Health

### `GET /health`
Returns system status, software version, the root cache file count, and live NASA IRSA connectivity state. When `demo_cache_only` is true, the service skips the live connectivity probe and uses the selected manifest for observation searches.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-11-14T16:30:00Z",
  "version": "1.0.0",
  "irsa_connected": true,
  "demo_cache_only": false,
  "cached_frames": 22
}
```

---

## 2. Observations & Demonstrations

### `GET /demo`
Returns list of the 5 official challenge demonstration target presets with verified celestial coordinates and notable features.

### `GET /demo/manifest`
Returns the active manifest, its entry count and the preset count. The default has 22 entries. The optional staged preview has ten entries when selected at startup.

### `GET /demo/comparison`

Available when `SPHEREX_DEMO_CACHE_ONLY=1`. Returns two chronological `ObservationRecord` objects for the fixed-footprint DR1 D5 field near the epoch-propagated Epsilon Indi position. The records have IDs `demo_comparison_2025W17_4B_0027_3_D5` and `demo_comparison_2026W17_2A_0308_3_D5`. Request this endpoint before submitting these IDs to `POST /frames/diff` or `POST /frames/stack`.

The route verifies both science FITS SHA-256 digests and the exact D5 calibration MD5 before registering the pair. It returns HTTP 503 with the missing or invalid input category if the verified inputs are unavailable, and HTTP 404 outside cache-only mode. The cutout footprints are fixed. Both arithmetic endpoints independently validate the pair and include the matched-pixel mask and calibration provenance in the result. This separate pair is excluded from the manifest counts and ordinary preset search results. [Local cache and launch instructions](DEMO_SCRIPT.md#run-the-local-d5-example)

### `GET /observations`
Queries NASA IRSA SIA2 service (with automatic local manifest fallback) for SPHEREx observations matching coordinates.

**Query Parameters:**
- `ra` (string/float, required): Right Ascension in decimal degrees ($[0, 360)$) or sexagesimal (`17h57m48.5s`).
- `dec` (string/float, required): Declination in decimal degrees ($[-90, +90]$) or sexagesimal (`+04d41m36s`).
- `fov` (float, optional, default: `0.04`): Search cone radius in degrees (greater than 0 and at most 0.3).
- `collection` (string, optional, default: `spherex_dr1`): Data release (`spherex_dr1` or `spherex_qr3`).
- `detector` (string, optional): Filter by detector array (e.g. `SPHEREx-D1` to `SPHEREx-D6`).
- `limit` (int, optional, default: `50`): Max observations returned.

`total_found` counts returned records, not necessarily the full archive. `total_found_is_lower_bound` is true when the requested limit is reached or records come from a historical/demo fallback. An empty result does not by itself distinguish no coverage from an archive outage.

---

## 3. Calibrated Frames & Differencing

### `GET /frames/{frame_id}`
Retrieves calibrated FITS image cutout, Astropy celestial WCS parameters, quality flag bitmask evaluation, and base64 PNG previews.

**Query Parameters:**
- `stretch` (string, optional, default: `asinh`): Contrast stretch algorithm (`asinh`, `zscale`, `linear`).
- `fov` (float, optional, default: `0.04`): Cutout size in degrees.

**Response Schema:**
```json
{
  "frame_id": "spherex_dr1_2025W33_1A_0144_1_SPHEREx_D3",
  "obs_id": "2025W33_1A_0144_1",
  "collection": "spherex_dr1",
  "detector": "SPHEREx-D3",
  "utc_date": "2025-08-15T20:45:11.376",
  "dimensions": [20, 20],
  "pixel_stats": {
    "min_mjy_sr": 0.198,
    "max_mjy_sr": 39.294,
    "mean_mjy_sr": 0.648,
    "std_mjy_sr": 3.141,
    "median_mjy_sr": 0.253
  },
  "flag_summary": {
    "flagged_pixels": 0,
    "total_pixels": 400,
    "flag_breakdown": {}
  },
  "wcs": {
    "crval1": 269.45208,
    "crval2": 4.69339,
    "crpix1": 10.0,
    "crpix2": 10.0
  },
  "image_base64": "data:image/png;base64,...",
  "colormapped_base64": "data:image/png;base64,...",
  "provenance_url": "https://irsa.ipac.caltech.edu/ibe/data/spherex/...",
  "is_synthetic": false
}
```

`target_predictions` and `target_photometry` are keyed by preset ID. The prediction uses the real FITS IMAGE midpoint (`MJD-AVG`, UTC), linear catalog proper motion, and native WCS. Its `pixel` gives zero-based `(x, y)` and the footprint result; projection may be unavailable. The prediction provides no source association.

`target_photometry.status` is `unavailable`. `aperture_status` is `not_checked` when inputs or footprint are insufficient, `unavailable` when the field aperture fails checks, or `field_sample_only` when the field aperture passes. The response provides the reason, ePSF extension presence and pixel counts where available. It carries no target flux. Simulated images and local fixtures omit both maps’ entries.

### `POST /frames/diff`

Subtracts the first exposure from the second for validated pixels. Supply `frame_id_1`, `frame_id_2`, an optional `fov` in degrees (default 0.04), and an optional `format` (`png` or `webp`). The response includes `diff_stats`, `image_base64`, and `colormapped_base64`.

### `POST /frames/stack`

Combines two to six independent exposures from the same detector. Supply registered `frame_ids`, an optional `method` (`mean`, `median`, or `sum`), and optionally `fov`, `format`, and `stretch`. Median is supported only for two exposures, where it equals the mean. Every retained pixel must meet the common passband threshold across all selected exposures. The response includes `image_base64`, `noise_stats`, and `frame_count`. Multi-exposure behavior has controlled fixture tests but has not yet been validated against three or more real compatible exposures.

Both endpoints align nearest native sample pairs on the reference celestial WCS within 0.5 comparison pixels and require at least 90% overlap of the wider nominal CWAVE-centered CBAND interval. They exclude invalid, flagged, and repeated samples. Pixels flagged only SOURCE or FULLSAMPLE are eligible. The response provides native-order `surface_brightness_mjy_sr` and `variance_mjy_sr_squared` arrays with `null` for excluded pixels and a transparent display mask. The `calibration` object identifies the archive calibration plane, checksum, method, overlap threshold, and retained pixels. The variance assumes independent exposures. HTTP 422 indicates unavailable calibration or no compatible pixels. HTTP 404 indicates an unknown frame ID. Far-separated fields and duplicate input are rejected with HTTP 400.

### `GET /cube/spectrum`

Returns a co-added DR1 sky-pixel sample for `ra` and `dec` in ICRS degrees. The response gives the requested coordinate, the NESTED HPX tile, and the zero-based index and sky center of the nearest native pixel. An optional `channel` (1–102) includes a native map around that pixel. The default `source=archive_first` checks IRSA. `source=preview_only` explicitly requests the verified packaged preview without an archive lookup; it returns 404 for coordinates not in that preview and labels its source accordingly. `source=pinned_cloud` skips SIA discovery and reads the explicitly dated DR1 cloud product; it does not establish that a newer version is unavailable.

The `channels` array has 102 ordered slots with detector, subchannel, wavelength center, lower and upper wavelength bounds, bandwidth in µm, hit count, unsigned quality flags, and status. Only `measured` records carry non-null `surface_brightness_mjy_sr`. The other statuses are `no_coverage`, `flagged`, `blank_channel` (including DR1 channels 51 and 52), and `missing_wavelength`. A finite diagnostic `archive_brightness_mjy_sr` may still be present on an excluded channel. The plot uses the measured field and leaves gaps.

The inspector uses up to six detector field aperture sums; it does not generate a resolved continuum or source temperature. The cube contains measured channels from the DR1 FITS mosaic. A cube sample has no single observation epoch or source extraction. Its coordinate does not confirm source association, detection, target photometry, motion, or variability. HTTP 404 indicates no tile/footprint at the request, whereas HTTP 503 reports an upstream archive access failure and HTTP 502 reports unreadable archive data. [IRSA DR1 data products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/)

For the archive path, IRSA SIA is queried to discover a tile and its bytes are read from the public cloud. A successful SIA-discovered result has `source: "irsa_archive"` and a `cloud` object with the mirror URL, ETag and transferred byte count. If the SIA lookup cannot supply a usable tile, the service tries the explicitly pinned DR1 `hips_20261026` layout and reports `source: "cloud_dr1_pinned"` and `cloud.discovery: "pinned_dr1_release"`; it does not claim that this is the newest product. A cloud failure or unreadable tile can return HTTP 200 with `source: "cached_dr1_preview"` for an unambiguous match to one of the [five audited preview coordinates](CHALLENGE_REQUIREMENTS.md#dr1-cube-coverage). Each supplied RA and Dec must be within `0.000005`° of the cached extraction coordinate. The response retains the requested coordinates. The `preview` object reports the extraction coordinate, UTC generation date, matched preset ID, tolerance, archive failure reason, and original FITS URL and identity. All sources expose `sample_kind: "coadded_dr1_sky_pixel"`, `observation_epoch: null`, and `source_association: "unconfirmed"`.

Unmatched requests retain the original 503 or 502. A 404 footprint/coverage result remains authoritative. The compact artifact stores 102 ordered channel records and the 102 native 25 × 25 windows per preset, including blank windows and nulls. A visible neighbor in a window provides no measurement at a blank central pixel.

---

## 4. Scientific Differentiation Endpoints

### `GET /science/catalogs`
Retrieves up to 200 nearby Gaia DR3 sources from VizieR, sorted by G magnitude. Returned catalog positions refer to epoch J2016.0. The separate image projection can approximately propagate positions with known proper motions to the FITS exposure midpoint; it does not model parallax or radial motion. Proper motion and parallax can be missing. An upstream failure returns HTTP 503; no curated fallback is fabricated.

**Query Parameters:**
- `ra` (string/float, required): Right Ascension.
- `dec` (string/float, required): Declination.
- `radius` (float, optional, default: `0.08`): Search cone radius in degrees.
- `catalog` (string, optional, default: `gaia_dr3`): Catalog identifier.

### `GET /science/photometry`
Summarizes cached cutouts among up to 60 search records using circular field apertures and background annulus subtraction. It does not download missing cutouts. A detector-group heuristic does not confirm variability, stability, matching wavelengths or source identity. Response metadata includes `analysis_source`, `observations_considered` and `cutouts_available`. Legacy values named flux are sums of surface-brightness pixels, not calibrated source flux densities.

**Query Parameters:**
- `ra` (string/float, required): Right Ascension.
- `dec` (string/float, required): Declination.
- `collection` (string, optional, default: `spherex_dr1`): Collection filter.
- `detector` (string, optional): Specific detector array.
- `fov` (float, optional, default: `0.04`): Cutout radius.

**Response Schema:**
```json
{
  "total_points": 4,
  "is_variable": true,
  "variability_index": 0.428,
  "mean_flux_mjy_sr": 14.85,
  "std_flux_mjy_sr": 6.35,
  "min_flux_mjy_sr": 7.20,
  "max_flux_mjy_sr": 23.40,
  "amplitude_delta_mjy_sr": 16.20,
  "points": [
    {
      "obs_id": "2025W18_1B_0162_1",
      "frame_id": "spherex_dr1_2025W18_1B_0162_1_SPHEREx_D1",
      "mjd": 60794.59,
      "utc_date": "2025-04-29T14:14:38.141",
      "detector": "SPHEREx-D1",
      "collection": "spherex_dr1",
      "net_flux_mjy_sr": 23.40,
      "peak_flux_mjy_sr": 39.29,
      "aperture_flux_sum": 72.50,
      "background_median": 0.25,
      "snr": 12.5
    }
  ]
}
```

### `POST /science/motion`

Automatic motion measurement is unavailable. The endpoint returns HTTP 422 for registered frames because the same source, wavelength compatibility, image quality and astrometric uncertainties have not been independently validated. Unknown frame IDs return HTTP 404. Use blink or a validated difference for visual investigation; neither establishes proper motion.

### `GET /science/spectrum`

Returns available detector-level field aperture sums from cached cutouts among up to 60 search records for `ra`, `dec`, and optional `fov` in degrees; missing images are not downloaded. The `bands` array contains only available measurements; the legacy `channels_102` and `continuum_curve` arrays are empty. The legacy field named `flux_mjy_sr` is a sum of surface-brightness pixels, not calibrated source flux density; `flux_density_mjy` is null. Source association, a resolved continuum, integrated source flux, and temperature are unavailable. The separately documented `/cube/spectrum` serves actual DR1 cube sky-pixel samples.

### `POST /science/report`
Generates a formal, structured Space Apps scientific discovery report with J2000 sexagesimal formatting, proper motion analysis, light curve statistics, and verified IRSA DOI 10.26131/IRSA678 citations.

**Request Body:**
```json
{
  "target_name": "Barnard's Star",
  "ra": 269.45208,
  "dec": 4.69339,
  "target_type": "High Proper Motion Star",
  "motion_data": { ... },
  "photometry_data": { ... },
  "notes": "Candidate offset requires an independent check."
}
```


Observation records identify search provenance as `irsa_query`, `cached_demo`, or `unknown`; an IRSA search result may still use cached image bytes. Spectrum band `uncertainty_source` distinguishes `variance_propagated`, `background_estimate`, `unknown`, and illustrative model errors. Only valid propagated uncertainties can enter the temperature fit. The `is_variable` light-curve field is a heuristic flag and does not establish variability or stability.


The embedded WCS-WAVE lookup is intended for visualization. Pair validation uses the matching per-pixel maps from the separate spectral calibration FITS files. See the [IRSA explanatory supplement](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf).

Photometry is unavailable if the aperture is clipped, contains invalid or masked pixels, or has no valid source-free background annulus. No area-only correction is applied to missing point-source flux.
