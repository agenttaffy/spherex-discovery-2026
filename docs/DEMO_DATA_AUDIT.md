# SPHEREx Demo-Data Audit Tool Guide

`scripts/audit_demo_manifest.py` is an independent, read-only audit tool designed for maintainers to verify manifest coverage, schema integrity, offline cache completeness, FITS file readability, pixel statistics, and WCS coordinate consistency without making network requests or modifying existing data files.

---

## 1. Quickstart & Command Reference

### Default Human-Readable Report
Run the audit against the repository's default manifest (`data/manifests/demo_dataset.json`) and cache (`data/cache`):

```bash
python scripts/audit_demo_manifest.py
```

### Machine-Readable JSON Output
Output structured JSON to stdout for CI pipelines or scripts:

```bash
python scripts/audit_demo_manifest.py --json
```

Or write JSON directly to an output file:

```bash
python scripts/audit_demo_manifest.py --json -o outputs/demo_audit_report.json
```

### Strict CI Mode
Treat all warnings as failures (returns exit code `1` if any warning or failure exists):

```bash
python scripts/audit_demo_manifest.py --strict
```

### Auditing Custom or Staged Datasets
Audit a candidate dataset in temporary staging directories before promoting it to production:

```bash
python scripts/audit_demo_manifest.py --manifest path/to/candidate_manifest.json --cache-dir path/to/candidate_cache/
```

### Command-Line Options

| Flag | Argument | Default | Description |
|---|---|---|---|
| `--manifest` | `PATH` | `data/manifests/demo_dataset.json` | Path to dataset JSON manifest |
| `--cache-dir` | `PATH` | `data/cache` | Path to FITS cutouts cache directory |
| `--format` | `text \| json` | `text` | Report format |
| `--json` | Flag | `False` | Shorthand for `--format json` |
| `-o`, `--output` | `PATH` | `None` (stdout) | Write rendered report to specified file path |
| `--strict` | Flag | `False` | Treat warnings as failures (exit code `1`) |
| `--stat-tolerance` | `FLOAT` | `0.001` | Numerical tolerance for comparing recorded vs fresh pixel stats |

---

## 2. Severity Levels & Exit Codes

The audit tool categorizes all evaluations into three deterministic severity levels:

### `PASS`
- The manifest file and all entries conform to required data types and valid physical ranges.
- Corresponding cache files exist on disk with non-zero size, match the expected SHA-256 key, and open cleanly with Astropy FITS helpers.
- Primary image dimensions match manifest metadata exactly.
- Re-calculated finite-pixel statistics agree with recorded statistics within tolerance.
- A valid celestial WCS is present and projects coordinates consistently.

### `WARN`
- **Non-fatal anomalies or legacy differences** that do not disrupt demo playback or backend processing.
- **Statistical discrepancies from legacy NaN-handling**: Early dataset builds computed summary statistics with legacy NaN sanitization (`min_finite` fill) rather than NaN masking. The audit detects this, reports both fresh finite stats and recorded values, and identifies when the legacy fill accounts for the difference.
- **Edge cutout geometry**: Cutout slices taken near physical detector borders (such as documentation example frames with dimensions $8 \times 20$) may have their search coordinates project near or slightly outside the boundary pixels.
- **Missing release-dependent optional extensions**: If optional SPHEREx extensions such as `FLAGS` (mask planes) or `WCS-WAVE` (wavelength calibration tables) are absent, they are reported as warnings rather than guessed failures.
- **Exit Code:** `0` in standard mode; `1` in `--strict` mode.

### `FAIL`
- **Fatal structural or integrity defects** that break offline operation or represent unrecoverable corruption:
  - Manifest file missing, unreadable, or invalid JSON.
  - Manifest root is not a list or has 0 entries.
  - Required fields missing (`target_name`, `ra`, `dec`, `collection`, `obs_id`, `detector`, `utc_date`, `cutout_url`).
  - Out-of-bounds coordinates ($RA \notin [0, 360]$ or $Dec \notin [-90, +90]$).
  - Malformed ISO timestamps or invalid URLs.
  - Duplicate entries (duplicate `cutout_url` or identical `(target, collection, obs_id, detector)` tuples).
  - Missing cache file on disk for any manifest entry.
  - Zero-byte or corrupted FITS files that fail to parse with `astropy.io.fits`.
  - Missing primary image extension or unreadable image array.
  - Primary image array dimensions disagree with manifest `dimensions`.
- **Exit Code:** `1` (always nonzero).

---

## 3. What the Audit Can and Cannot Establish

For a fresh checkout of the ten-frame preview, first install the dependencies and run the [pinned IRSA bootstrap](../README.md#preview-a-refreshed-demo-cache). Run `python scripts/bootstrap_demo_data.py --check-only --with-comparisons` to verify the complete preview and optional comparison inputs without writing or contacting IRSA. The FITS audit below checks a selected, prepared manifest. By default it examines the separate original demo.

To prevent misinterpreting offline verification as astrophysical confirmation, maintainers must understand the precise boundaries of this audit:

### What the Audit CAN Establish
1. **Prepared FITS cache completeness:** The audit checks whether every cutout in the selected manifest already exists locally. It covers those FITS files. Aladin remote surveys, live queries, and cube positions outside the five cached presets can still require network access.
2. **Schema & Cache Key Alignment**: Manifest keys, types, and URLs compute to the exact SHA-256 filenames expected by `CacheService`.
3. **Format & Array Integrity**: FITS headers and multi-extension HDUs are compliant with FITS standards; array shapes and data types are valid.
4. **Finite-Pixel Flux Coverage**: Finite vs. non-finite (NaN/Inf) pixel counts are accurately quantified and verified.
5. **Fresh Flux Statistics**: True scientific summary statistics ($\text{min}, \text{max}, \text{mean}, \text{std}, \text{median}$ in $\text{MJy/sr}$) are computed on finite pixels.
6. **Internal WCS Geometry**: Astropy celestial WCS can be initialized and projects image centers and pixel coordinates consistently.

### What the Audit CANNOT Establish (Scientific Limitations)
1. **Astrophysical Object Identity**: Passing the audit does **not** prove that the source in the image is the named astronomical object. It only proves that the FITS file downloaded from that IRSA query exists and is internally consistent.
2. **Proper Motion & Source Location**: For high-proper-motion objects (e.g., Barnard's Star with $\sim 10.3\text{ arcsec/yr}$ motion), the audit calculates coordinate separation against the query coordinates, but does **not** model astronomical epoch propagation or verify that the star is centered in the aperture.
3. **Astrophysical Variability**: Flux differences across epochs are reported as raw statistics, not verified as authentic stellar pulsations (e.g., R Draconis) or accretion events.
4. **Calibration Quality**: The audit verifies that units are recorded as $\text{MJy/sr}$ and data arrays are parseable; it does not evaluate photometric zero-points, flat-field residuals, or cosmic ray removal accuracy.
5. **Per-Pixel Spectral Compatibility**: Having valid multi-detector cutouts does not confirm that multi-band spectra can be extracted without sub-pixel spatial re-registration or point-spread-function (PSF) homogenization.

---

## 4. How to Interpret WCS Offsets

The audit calculates the angular offset between the manifest's target coordinate $(\alpha_{\text{target}}, \delta_{\text{target}})$ and the world coordinate of the cutout center pixel $(x_c, y_c) = \left(\frac{W-1}{2}, \frac{H-1}{2}\right)$ using Astropy:

$$\Delta\theta = \text{Separation}\left(\text{SkyCoord}(\alpha_{\text{target}}, \delta_{\text{target}}), \text{WCS}.\text{pixel\_to\_world}(x_c, y_c)\right)$$

### Typical Values
- **Nominal Square Cutouts ($20 \times 20$):** Typical offsets are **$0.9\text{ arcsec}$ to $3.9\text{ arcsec}$**. With the SPHEREx pixel scale of approximately $6.2\text{ arcsec/pixel}$, an offset of $\sim 2\text{ arcsec}$ is less than a third of a pixel, demonstrating that the IRSA cutout service centered the requested coordinates in the extracted sub-array.
- **Edge / Boundary Cutouts ($8 \times 20$):** When an observation lies near the edge of a Level 2 detector array, IRSA crops the cutout to available pixels. For example, Entry #1 (Documentation Example, D1) has shape $8 \times 20$, and the target coordinate projects to $(x=9.05, y=9.41)$, just outside row 7. The center offset is reported as $36.74\text{ arcsec}$.
- **Diagnostic Role:** This offset is strictly an **internal geometric diagnostic**. Maintainers should **not** impose arbitrary tight tolerances or assume a non-zero offset indicates a defect; it reflects the true projection geometry of the cutout.

---

## 5. Safe Future Refresh Sequence

When refreshing or extending the offline demo dataset with new targets, data releases, or detectors, maintainers must follow this safe staging sequence to prevent invalidating the offline demo:

```
[1. Build Staging] ────> [2. Audit Staging] ────> [3. Review Report] ────> [4. Atomic Promotion]
(new manifest & cutouts)  (audit_demo_manifest)   (ensure 0 FAILs)         (replace live assets)
```

### Step 1: Create Staging Directories
Never write unverified data directly into `data/cache` or overwrite `data/manifests/demo_dataset.json`.

```bash
mkdir -p data/staging_cache
mkdir -p data/staging_manifests
```

### Step 2: Download Cutouts into Staging
Configure your download script (or `scripts/build_demo_dataset.py`) to output to staging paths:
- Cache directory: `data/staging_cache/`
- Manifest file: `data/staging_manifests/demo_dataset_candidate.json`

### Step 3: Audit Candidate Dataset in Staging
Run the audit tool pointing explicitly to the staged manifest and staging cache:

```bash
python scripts/audit_demo_manifest.py \
  --manifest data/staging_manifests/demo_dataset_candidate.json \
  --cache-dir data/staging_cache/ \
  --json \
  -o outputs/staging_audit.json
```

### Step 4: Evaluate Audit Findings
- If **FAIL** findings exist: **DO NOT PROMOTE**. Fix the download script, correct coordinates, or re-fetch missing files.
- If **WARN** findings exist: Verify whether they are acceptable edge cutouts or legacy statistic variations.
- Run tests against candidate:
  ```bash
  pytest backend/tests/test_demo_manifest_audit.py
  ```

### Step 5: Atomic Promotion
Once the candidate dataset passes the audit:

```bash
# 1. Copy new cached FITS files into data/cache (preserving existing files)
cp -n data/staging_cache/*.fits data/cache/

# 2. Back up existing manifest
cp data/manifests/demo_dataset.json data/manifests/demo_dataset.json.bak

# 3. Promote validated candidate manifest
cp data/staging_manifests/demo_dataset_candidate.json data/manifests/demo_dataset.json

# 4. Final verification against live paths
python scripts/audit_demo_manifest.py
```

### Step 6: Clean Up Staging
Remove temporary staging assets once the live audit reports clean status.
