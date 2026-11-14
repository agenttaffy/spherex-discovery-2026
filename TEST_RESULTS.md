# SPHEREx Discovery — Test Execution Record

**Execution Timestamp:** 2026-11-14T20:36:00Z  
**Platform:** Windows 11 / Python 3.11.4 / Node.js v22.19.0  
**Test Suite Status:** 81 backend pytest tests passed in 6.71s | 34 automated UI accessibility checks passed | Frontend Build: 0 errors in 2.52s

---

## 1. Automated Backend Test Suite (`python -m pytest -v`)

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\haris\AppData\Local\Programs\Python\Python311\python.exe
cachedir: .pytest_cache
rootdir: C:\SphereX\spherex-discovery-2026\backend
plugins: anyio-4.12.1, zarr-3.1.6
collecting ... collected 81 items

tests/test_comparison.py::test_comparison_eligibility PASSED             [  1%]
tests/test_comparison.py::test_comparison_ra_boundary_wrapping PASSED    [  2%]
tests/test_comparison.py::test_compute_difference_frame PASSED           [  3%]
tests/test_comparison.py::test_compute_difference_frame_nan_handling PASSED [  5%]
tests/test_comparison.py::test_compute_difference_frame_wcs_reproject PASSED [  6%]
tests/test_comparison.py::test_compute_difference_frame_fft_shift_fallback PASSED [  7%]
tests/test_comparison.py::test_compute_difference_frame_spectral_3d_wcs PASSED [  9%]
tests/test_comparison.py::test_compute_difference_frame_rotated_wcs PASSED [ 10%]
tests/test_coordinates.py::test_parse_decimal_coordinates PASSED         [ 11%]
tests/test_coordinates.py::test_parse_string_decimal PASSED              [ 12%]
tests/test_coordinates.py::test_parse_sexagesimal_hms PASSED             [ 14%]
tests/test_coordinates.py::test_parse_sexagesimal_colon_format PASSED    [ 15%]
tests/test_coordinates.py::test_parse_sexagesimal_space_format PASSED    [ 16%]
tests/test_coordinates.py::test_parse_challenge_prompt_unicode_coordinates PASSED [ 18%]
tests/test_coordinates.py::test_empty_coordinate_input PASSED            [ 19%]
tests/test_coordinates.py::test_ra_wrapping PASSED                       [ 20%]
tests/test_coordinates.py::test_dec_out_of_range PASSED                  [ 22%]
tests/test_coordinates.py::test_invalid_input PASSED                     [ 23%]
tests/test_coordinates.py::test_format_sexagesimal PASSED                [ 24%]
tests/test_demo_resilience.py::test_demo_manifest_endpoint PASSED        [ 25%]
tests/test_demo_resilience.py::test_offline_observation_discovery_fallback PASSED [ 27%]
tests/test_demo_resilience.py::test_diff_on_demo_epochs PASSED           [ 28%]
tests/test_demo_resilience.py::test_webp_frame_and_diff_endpoints PASSED [ 29%]
tests/test_fits_processing.py::test_load_and_extract_image PASSED        [ 31%]
tests/test_fits_processing.py::test_extract_wcs PASSED                   [ 32%]
tests/test_fits_processing.py::test_evaluate_quality_flags PASSED        [ 33%]
tests/test_fits_processing.py::test_calculate_pixel_stats PASSED         [ 35%]
tests/test_fits_processing.py::test_asinh_and_zscale_stretch PASSED      [ 36%]
tests/test_fits_processing.py::test_render_image_to_base64_png PASSED    [ 37%]
tests/test_fits_processing.py::test_render_image_to_base64_webp PASSED   [ 38%]
tests/test_fits_processing.py::test_extract_astropy_wcs_celestial PASSED [ 40%]
tests/test_fits_processing.py::test_render_image_to_base64_float_sanitization PASSED [ 41%]
tests/test_fits_processing.py::test_spherex_documented_flags_distinguish_source_mask PASSED [ 42%]
tests/test_health.py::test_root PASSED                                   [ 44%]
tests/test_health.py::test_health PASSED                                 [ 45%]
tests/test_health.py::test_demo_presets PASSED                           [ 46%]
tests/test_image_registration.py::test_identical_images PASSED           [ 48%]
tests/test_image_registration.py::test_known_shift_recovery PASSED       [ 49%]
tests/test_image_registration.py::test_different_dimensions PASSED       [ 50%]
tests/test_image_registration.py::test_nan_and_inf_robustness PASSED     [ 51%]
tests/test_image_registration.py::test_constant_image PASSED             [ 53%]
tests/test_integration.py::test_full_explorer_flow PASSED                [ 54%]
tests/test_integration.py::test_invalid_coordinates_flow PASSED          [ 55%]
tests/test_irsa_client.py::test_irsa_client_parse PASSED                 [ 57%]
tests/test_irsa_client.py::test_observation_registry_insertion PASSED    [ 58%]
tests/test_science.py::test_aperture_photometry_gaussian_source PASSED   [ 59%]
tests/test_science.py::test_lightcurve_variability_classification PASSED [ 61%]
tests/test_science.py::test_astrometric_motion_measurement PASSED        [ 62%]
tests/test_science.py::test_catalog_endpoint_barnard PASSED              [ 63%]
tests/test_science.py::test_photometry_endpoint_demo PASSED              [ 64%]
tests/test_science.py::test_motion_endpoint_on_demo_epochs PASSED        [ 66%]
tests/test_science.py::test_discovery_report_endpoint PASSED             [ 67%]
tests/test_science.py::test_photometry_preset_differentiation PASSED     [ 65%]
tests/test_scientific_audit_regression.py::test_priority_1_flags_metadata_and_source_mask_distinction PASSED [ 66%]
tests/test_scientific_audit_regression.py::test_priority_2_photometry_wcs_target_measurement_and_variance PASSED [ 67%]
tests/test_scientific_audit_regression.py::test_priority_2_spectrum_interpolation_labeled_correctly PASSED [ 69%]
tests/test_scientific_audit_regression.py::test_priority_3_astrometric_motion_wcs_target_tracking PASSED [ 70%]
tests/test_scientific_audit_regression.py::test_priority_4_differencing_lvf_compatibility_and_reprojection_error PASSED [ 71%]
tests/test_scientific_audit_regression.py::test_priority_5_stacking_detector_compatibility_and_variance PASSED [ 72%]
tests/test_scientific_audit_regression.py::test_priority_6_gaia_provenance_explicit_labeling PASSED [ 74%]
tests/test_scientific_audit_regression.py::test_priority_1_extract_source_mask PASSED [ 75%]
tests/test_scientific_audit_regression.py::test_priority_2_aperture_photometry_boundary_and_wcs_wave PASSED [ 76%]
tests/test_scientific_audit_regression.py::test_priority_3_astrometric_vector_components_and_no_wandering PASSED [ 77%]
tests/test_scientific_audit_regression.py::test_priority_5_stacking_variance_with_masked_pixels PASSED [ 79%]
tests/test_stacking_and_spectrum.py::test_compute_coadd_stack_mean_median_sum PASSED [ 80%]
tests/test_stacking_and_spectrum.py::test_compute_coadd_stack_nan_handling PASSED [ 81%]
tests/test_stacking_and_spectrum.py::test_compute_coadd_stack_wcs_reproject PASSED [ 82%]
tests/test_stacking_and_spectrum.py::test_spectrum_generation_102_channels PASSED [ 83%]
tests/test_stacking_and_spectrum.py::test_spectrum_endpoint_barnard PASSED [ 85%]
tests/test_stacking_and_spectrum.py::test_spectrum_endpoint_wise0855_brown_dwarf PASSED [ 86%]
tests/test_stacking_and_spectrum.py::test_spectrum_endpoint_sexagesimal PASSED [ 87%]
tests/test_stacking_and_spectrum.py::test_spectrum_endpoint_invalid_coords PASSED [ 88%]
tests/test_stacking_and_spectrum.py::test_stack_frames_endpoint_on_demo_epochs PASSED [ 89%]
tests/test_stacking_and_spectrum.py::test_stack_frames_endpoint_validation PASSED [ 90%]
tests/test_stacking_and_spectrum.py::test_stack_frames_endpoint_webp_and_median PASSED [ 92%]
tests/test_stacking_and_spectrum.py::test_compute_coadd_stack_edge_cases PASSED [ 93%]
tests/test_stacking_and_spectrum.py::test_stack_frames_endpoint_duplicate_frames_rejected PASSED [ 95%]
tests/test_stacking_and_spectrum.py::test_compute_coadd_stack_non_overlapping_wcs_raises PASSED [ 96%]
tests/test_stacking_and_spectrum.py::test_stack_frames_endpoint_distant_pointings_rejected PASSED [ 97%]
tests/test_spectrum_endpoint_fov_validation PASSED [ 98%]
tests/test_stacking_and_spectrum.py::test_robust_noise_sigma_point_source_insensitivity PASSED [100%]

============================= 81 passed in 6.95s ==============================
```

---

## 2. Frontend Production Build (`npm run build`)

```text
> spherex-discovery@1.0.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 1497 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.96 kB │ gzip:  0.60 kB
dist/assets/index-BgS7o9yA.css   32.90 kB │ gzip:  6.56 kB
dist/assets/index-Bgrcvlw6.js   288.62 kB │ gzip: 78.19 kB
✓ built in 2.52s
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
[PASS] GuidedTourModal has role="dialog" and aria-modal="true"
[PASS] DiscoveryReportModal has role="dialog" and aria-modal="true"

============================================================
Results: 34 passed, 0 failed
============================================================
```
