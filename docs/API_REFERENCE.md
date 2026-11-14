# Backend API Reference

Base URL: `http://localhost:8000/api`

---

### 1. `GET /health`
Returns system status, software versions, and live NASA IRSA connectivity state.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-11-14T14:20:00Z",
  "version": "1.0.0",
  "irsa_connected": true,
  "cache_entries": 12
}
```

---

### 2. `GET /observations`
Searches IRSA SIA2 for SPHEREx observations matching coordinates and field size.

**Parameters:**
- `ra` (float, required): Right Ascension in decimal degrees ($[0, 360)$).
- `dec` (float, required): Declination in decimal degrees ($[-90, +90]$).
- `fov` (float, optional, default: 0.05): Field of view / search radius in degrees.
- `collection` (string, optional, default: `spherex_dr1`): `spherex_dr1` or `spherex_qr3`.
- `detector` (string, optional): Specific detector filter (e.g. `SPHEREx-D1`).
- `limit` (int, optional, default: 50): Max records to return.

**Response:**
```json
{
  "target": {"ra": 269.45208, "dec": 4.69339, "fov": 0.05},
  "collection": "spherex_dr1",
  "total_found": 255,
  "returned_count": 50,
  "observations": [
    {
      "id": "obs_60898_2025W33_1A_0144_1_D1",
      "obs_id": "2025W33_1A_0144_1",
      "collection": "spherex_dr1",
      "detector": "SPHEREx-D1",
      "mjd": 60898.86471,
      "utc_date": "2025-08-15T20:45:11.376",
      "em_min": 7.455e-07,
      "em_max": 1.1167e-06,
      "access_url": "https://irsa.ipac.caltech.edu/ibe/data/spherex/...",
      "frame_api_url": "/api/frames/obs_60898_2025W33_1A_0144_1_D1"
    }
  ]
}
```

---

### 3. `GET /frames/{frame_id}`
Retrieves metadata and rendered image data for a specific observation frame.

**Parameters:**
- `stretch` (string, optional, default: `asinh`): `asinh`, `zscale`, `linear`, `log`.
- `format` (string, optional, default: `json`): `json` (includes base64 PNG and scientific stats) or `png` (raw image bytes).

**Response (JSON format):**
```json
{
  "frame_id": "obs_60898_2025W33_1A_0144_1_D1",
  "obs_id": "2025W33_1A_0144_1",
  "utc_date": "2025-08-15T20:45:11.376",
  "detector": "SPHEREx-D1",
  "dimensions": [29, 13],
  "pixel_stats": {
    "min_mjy_sr": 0.12,
    "max_mjy_sr": 18.4,
    "mean_mjy_sr": 1.85,
    "std_mjy_sr": 0.94
  },
  "flag_summary": {"flagged_pixels": 0, "total_pixels": 377},
  "wcs": {
    "crval1": 269.45208,
    "crval2": 4.69339,
    "cdelt": [-0.00172, 0.00172]
  },
  "image_base64": "data:image/png;base64,iVBORw0KGgo..."
}
```

---

### 4. `GET /demo`
Returns pre-verified demonstration targets with curated multi-epoch observations for immediate offline or low-latency judging demonstrations.
