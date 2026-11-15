# SPHEREx Discovery — Test Execution Record

**Execution Timestamp:** 2026-11-14T23:27:00Z  
**Platform:** Windows 11 / Python 3.11.4 / Node.js v22.19.0  
**Test Suite Status:** 93 backend pytest tests passed (with 2 Astropy FITSFixedWarnings) in 10.11s | 41 automated UI accessibility checks passed | Frontend Build: 1,497 modules transformed, 0 errors in 2.55s | Demo Assets: 22/22 verified | NASA/IPAC IRSA SIA: 200 OK

---

## 1. Automated Backend Test Suite (`python -m pytest -v`)

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\haris\AppData\Local\Programs\Python\Python311\python.exe
cachedir: .pytest_cache
rootdir: C:\SphereX\spherex-discovery-2026
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
  C:\Users\haris\AppData\Local\Programs\Python\Python311\Lib\site-packages\astropy\wcs\wcs.py:695: FITSFixedWarning: The WCS transformation has more axes (3) than the image it is associated with (2)
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
