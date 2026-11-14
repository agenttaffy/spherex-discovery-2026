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
Computes scientific calibrated difference image ($I_2 - I_1$) with 2D sub-pixel registration and NaN-safe mid-gray mapping.

**Request Body:**
```json
{
  "frame_id_1": "spherex_dr1_2025W33_1A_0144_1_SPHEREx_D3",
  "frame_id_2": "spherex_qr3_2026W33_1A_0144_2_SPHEREx_D3"
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
Extracts multi-epoch circular aperture photometry with background annulus subtraction, returning time-series flux measurements and automated variability classification.

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
