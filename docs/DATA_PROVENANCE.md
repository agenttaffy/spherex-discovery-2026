# Data Provenance & Citation Standards

## 1. NASA / IPAC IRSA Citations
This application accesses public data products provided by the NASA/IPAC Infrared Science Archive (IRSA), operated by the Jet Propulsion Laboratory, California Institute of Technology, under contract with the National Aeronautics and Space Administration.

### Official Citations
- **SPHEREx DR1 Spectral Images:**
  - Archive: NASA/IPAC Infrared Science Archive
  - DOI: `10.26131/IRSA678`
  - URL: `https://doi.org/10.26131/IRSA678`
- **SPHEREx DR1 All-Sky Cube:**
  - Archive: NASA/IPAC Infrared Science Archive
  - DOI: `10.26131/IRSA679`
  - URL: `https://doi.org/10.26131/IRSA679`
- **SPHEREx QR3 Data:**
  - Quick Release 3 (Surveys 3 and 4, 2026), Caltech/IPAC.

## 2. Provenance Tracking within the Application
Every astronomical frame retrieved and rendered retains its full pedigree:
1. `source_url`: Full remote URL at `irsa.ipac.caltech.edu`.
2. `obs_id`: Original mission observation identifier (e.g., `2025W18_1B_0162_1`).
3. `utc_time`: Converted UTC ISO-8601 timestamp from MJD.
4. `detector`: Detector focal plane array (SPHEREx-D1 through D6).
5. `processing_steps`: Logged transformations (sub-array cutout -> quality flag filtering -> asinh stretch normalization).
6. Direct clickable link for users to download the raw FITS product directly from NASA IRSA.
