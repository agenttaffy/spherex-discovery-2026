# SPHEREx Discovery — REST API Reference

Base URL: `http://localhost:8000/api`  
Interactive OpenAPI / Swagger UI: `http://localhost:8000/docs`

---

## 1. System & Health

### `GET /health`
Returns system status, software versions, cached frame count, and live NASA IRSA connectivity state.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-11-14T16:30:00Z",
  "version": "1.0.0",
  "irsa_connected": true,
  "cached_frames": 22
}
```

---

## 2. Observations & Demonstrations

### `GET /demo`
Returns list of the 5 official challenge demonstration target presets with verified celestial coordinates and notable features.

### `GET /demo/manifest`
Returns complete verification manifest of all 22 verified DR1/QR3 Level 2 FITS cutouts cached locally for guaranteed presentation uptime.

### `GET /observations`
Queries NASA IRSA SIA2 service (with automatic local manifest fallback) for SPHEREx observations matching coordinates.

**Query Parameters:**
- `ra` (string/float, required): Right Ascension in decimal degrees ($[0, 360)$) or sexagesimal (`17h57m48.5s`).
- `dec` (string/float, required): Declination in decimal degrees ($[-90, +90]$) or sexagesimal (`+04d41m36s`).
- `fov` (float, optional, default: `0.04`): Search cone radius in degrees ($0.001$ to $0.5$).
- `collection` (string, optional, default: `spherex_dr1`): Data release (`spherex_dr1` or `spherex_qr3`).
- `detector` (string, optional): Filter by detector array (e.g. `SPHEREx-D1` to `SPHEREx-D6`).
- `limit` (int, optional, default: `50`): Max observations returned.

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

### `POST /frames/diff`
Temporarily returns HTTP 422: per-pixel wavelength compatibility has not been validated with separate spectral WCS products. Same-detector labels and broad wavelength ranges are insufficient.

**Request Body:**
```json
{
  "frame_id_1": "spherex_dr1_2025W33_1A_0144_1_SPHEREx_D3",
  "frame_id_2": "spherex_qr3_2026W33_1A_0144_2_SPHEREx_D3"
}
```

### `POST /frames/stack`
Computes astronomical image co-addition across multi-epoch or multi-detector observation frames using celestial WCS registration via `reproject_interp` with sub-pixel 2D FFT shift fallback.

**Request Body:**
```json
{
  "frame_ids": [
    "spherex_dr1_2025W33_1A_0144_1_SPHEREx_D3",
    "spherex_qr3_2026W33_1A_0144_2_SPHEREx_D3"
  ],
  "method": "mean",
  "format": "webp"
}
```

**Response Schema:**
```json
{
  "success": true,
  "method": "mean",
  "frame_count": 2,
  "frame_ids": ["spherex_dr1_...", "spherex_qr3_..."],
  "dimensions": [20, 20],
  "snr_improvement_factor": 1.41,
  "snr_gain_status": "measured",
  "theoretical_snr_gain": 1.414,
  "theoretical_gain_model": "sqrt(N)",
  "noise_stats": {
    "reference_noise_sigma": 0.428,
    "stacked_noise_sigma": 0.303,
    "mean_flux_mjy_sr": 2.145
  },
  "stacked_image_base64": "data:image/webp;base64,...",
  "wcs": { ... }
}
```

---

## 4. Scientific Differentiation Endpoints

### `GET /science/catalogs`
Retrieves nearby reference stars from Gaia DR3 & SIMBAD with high-precision proper motions, parallaxes, and G-magnitudes.

**Query Parameters:**
- `ra` (string/float, required): Right Ascension.
- `dec` (string/float, required): Declination.
- `radius` (float, optional, default: `0.08`): Search cone radius in degrees.
- `catalog` (string, optional, default: `gaia_dr3`): Catalog identifier.

### `GET /science/photometry`
Extracts multi-epoch circular aperture photometry with background annulus subtraction, returning time-series flux measurements and a heuristic variation flag (not confirmation of variability or stability).

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
Measures candidate astrometric displacement and annual proper motion rate ($\mu$ in arcsec/year and mas/year) between two observation epochs.

**Request Body:**
```json
{
  "frame_id_1": "spherex_dr1_2025W33_1A_0144_1_SPHEREx_D3",
  "frame_id_2": "spherex_qr3_2026W33_1A_0144_2_SPHEREx_D3",
  "pixel_scale_arcsec": 6.2
}
```

**Response Schema:**
```json
{
  "eligible": true,
  "frame_1": "spherex_dr1_2025W33_1A_0144_1_SPHEREx_D3",
  "frame_2": "spherex_qr3_2026W33_1A_0144_2_SPHEREx_D3",
  "motion": {
    "dx_pixels": -0.32,
    "dy_pixels": 1.63,
    "displacement_pixels": 1.66,
    "displacement_arcsec": 10.31,
    "position_angle_deg": 355.6,
    "delta_time_days": 365.25,
    "delta_time_years": 1.0,
    "proper_motion_arcsec_yr": 10.31,
    "proper_motion_mas_yr": 10310.0,
    "motion_class": "High Proper Motion Candidate",
    "centroid_detected": true,
    "confidence_score": 0.94
  }
}
```

### `GET /science/spectrum`
Computes Spectral Energy Distribution (SED) by extracting circular aperture photometry across up to six SPHEREx detector arrays (D1: 0.75–1.12 µm, D2: 1.12–1.68 µm, D3: 1.68–2.42 µm, D4: 2.42–3.82 µm, D5: 3.82–4.42 µm, D6: 4.42–5.00 µm) with approximate WCS-WAVE visualization wavelengths and propagated `VARIANCE` uncertainties where available; otherwise nominal wavelengths or background-estimated uncertainties are labeled. Accompanied by an illustrative/interpolated 102-point continuum model.

> [!IMPORTANT]
> **Spectrophotometry Truthfulness:**
> - There are up to six measured detector-band points (D1–D6) plus an illustrative/interpolated 102-point continuum; this is **not 102 observed resolved SPHEREx channels**.
> - `continuum_shape` is a neutral broadband descriptor (e.g. *"flux rises toward longer measured bands"* or *"peak among measured detector bands"*), not an astrophysical or spectral classification. `spectral_class` was removed from the API.
> - `estimated_temperature_k` / `temperature_fit` is strictly an optional single-temperature blackbody continuum fit requiring at least 3 distinct measured detector bands with valid propagated uncertainties ($\text{dof} \ge 1$). It is not an object's known physical temperature.
> - When zero archive bands exist, `peak_wavelength_um`, `peak_detector`, `peak_flux_mjy_sr`, `estimated_temperature_k`, and `integrated_flux_mjy_sr_um` are `null` (`unavailable`), with `peak_is_measured: false`.

**Query Parameters:**
- `ra` (string/float, required): Right Ascension.
- `dec` (string/float, required): Declination.
- `fov` (float, optional, default: `0.04`): Search field of view in degrees.

**Response Schema:**
```json
{
  "target": { "ra": 269.45208, "dec": 4.69339 },
  "total_observed_bands": 2,
  "bands": [
    {
      "detector": "SPHEREx-D3",
      "wavelength_um": 2.050,
      "flux_mjy_sr": 12.45,
      "flux_err_mjy_sr": 0.35,
      "snr": 35.6,
      "is_observed": true,
      "measurement_status": "measured",
      "calibration_source": "WCS-WAVE"
    }
  ],
  "channels_102": [
    {
      "channel_index": 1,
      "detector": "SPHEREx-D1",
      "wavelength_um": 0.75,
      "flux_mjy_sr": 0.05,
      "is_observed": false,
      "is_interpolated": true,
      "model_label": "Estimated Continuum Model (Interpolated) - Illustrative Continuum, Never Observed Resolution"
    }
  ],
  "summary": {
    "peak_wavelength_um": 2.050,
    "peak_detector": "SPHEREx-D3",
    "peak_flux_mjy_sr": 12.45,
    "peak_is_measured": true,
    "estimated_temperature_k": null,
    "continuum_shape": "flux rises toward longer measured bands",
    "integrated_flux_mjy_sr_um": 18.25,
    "temperature_fit": {
      "status": "unavailable",
      "temperature_k": null,
      "reason": "Insufficient observed detector bands (minimum 3 distinct bands required for dof >= 1)"
    }
  }
}
```

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
  "notes": "Verified displacement across DR1 (2025) and QR3 (2026)."
}
```


Observation records identify search provenance as `irsa_query`, `cached_demo`, or `unknown`; an IRSA search result may still use cached image bytes. Spectrum band `uncertainty_source` distinguishes `variance_propagated`, `background_estimate`, `unknown`, and illustrative model errors. Only valid propagated uncertainties can enter the temperature fit. The `is_variable` light-curve field is a heuristic flag and does not establish variability or stability.


**Current comparison limitation:** `/api/frames/diff` and `/api/frames/stack` return HTTP 422 for otherwise eligible frames until per-pixel spectral compatibility can be validated. Blink remains available. The embedded WCS-WAVE lookup is approximate and intended for visualization; see the [IRSA explanatory supplement](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf).
