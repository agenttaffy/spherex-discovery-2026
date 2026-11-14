# SPHEREx Discovery — Test Execution Record

**Execution Timestamp:** 2026-11-14T18:05:00Z  
**Platform:** Windows 11 / Python 3.11.4 / Node.js v22.19.0  
**Test Suite Status:** 64 passed in 5.28s | Frontend Build: 0 errors in 2.24s

---

## 1. Automated Backend Test Suite (`pytest -v`)

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\haris\AppData\Local\Programs\Python\Python311\python.exe
cachedir: .pytest_cache
rootdir: C:\SphereX\spherex-discovery-2026\backend
plugins: anyio-4.12.1, zarr-3.1.6
collecting ... collected 64 items

tests/test_comparison.py::test_comparison_eligibility PASSED             [  1%]
tests/test_comparison.py::test_comparison_ra_boundary_wrapping PASSED    [  3%]
tests/test_comparison.py::test_compute_difference_frame PASSED           [  4%]
tests/test_comparison.py::test_compute_difference_frame_nan_handling PASSED [  6%]
tests/test_comparison.py::test_compute_difference_frame_wcs_reproject PASSED [  7%]
tests/test_comparison.py::test_compute_difference_frame_fft_shift_fallback PASSED [  9%]
tests/test_comparison.py::test_compute_difference_frame_spectral_3d_wcs PASSED [ 10%]
tests/test_comparison.py::test_compute_difference_frame_rotated_wcs PASSED [ 12%]
tests/test_coordinates.py::test_parse_decimal_coordinates PASSED         [ 14%]
tests/test_coordinates.py::test_parse_string_decimal PASSED              [ 15%]
tests/test_coordinates.py::test_parse_sexagesimal_hms PASSED             [ 17%]
tests/test_coordinates.py::test_parse_sexagesimal_colon_format PASSED    [ 18%]
tests/test_coordinates.py::test_parse_sexagesimal_space_format PASSED    [ 20%]
tests/test_coordinates.py::test_parse_challenge_prompt_unicode_coordinates PASSED [ 21%]
tests/test_coordinates.py::test_empty_coordinate_input PASSED            [ 23%]
tests/test_coordinates.py::test_ra_wrapping PASSED                       [ 25%]
tests/test_coordinates.py::test_dec_out_of_range PASSED                  [ 26%]
tests/test_coordinates.py::test_invalid_input PASSED                     [ 28%]
tests/test_coordinates.py::test_format_sexagesimal PASSED                [ 29%]
tests/test_demo_resilience.py::test_demo_manifest_endpoint PASSED        [ 31%]
tests/test_demo_resilience.py::test_offline_observation_discovery_fallback PASSED [ 32%]
tests/test_demo_resilience.py::test_diff_on_demo_epochs PASSED           [ 34%]
tests/test_demo_resilience.py::test_webp_frame_and_diff_endpoints PASSED [ 35%]
tests/test_fits_processing.py::test_load_and_extract_image PASSED        [ 37%]
tests/test_fits_processing.py::test_extract_wcs PASSED                   [ 39%]
tests/test_fits_processing.py::test_evaluate_quality_flags PASSED        [ 40%]
tests/test_fits_processing.py::test_calculate_pixel_stats PASSED         [ 42%]
tests/test_fits_processing.py::test_asinh_and_zscale_stretch PASSED      [ 43%]
tests/test_fits_processing.py::test_render_image_to_base64_png PASSED    [ 45%]
tests/test_fits_processing.py::test_render_image_to_base64_webp PASSED   [ 46%]
tests/test_fits_processing.py::test_extract_astropy_wcs_celestial PASSED [ 48%]
tests/test_fits_processing.py::test_render_image_to_base64_float_sanitization PASSED [ 50%]
tests/test_health.py::test_root PASSED                                   [ 51%]
tests/test_health.py::test_health PASSED                                 [ 53%]
tests/test_health.py::test_demo_presets PASSED                           [ 54%]
tests/test_image_registration.py::test_identical_images PASSED           [ 56%]
tests/test_image_registration.py::test_known_shift_recovery PASSED       [ 57%]
tests/test_image_registration.py::test_different_dimensions PASSED       [ 59%]
tests/test_image_registration.py::test_nan_and_inf_robustness PASSED     [ 60%]
tests/test_image_registration.py::test_constant_image PASSED             [ 62%]
tests/test_integration.py::test_full_explorer_flow PASSED                [ 64%]
tests/test_integration.py::test_invalid_coordinates_flow PASSED          [ 65%]
tests/test_irsa_client.py::test_irsa_client_parse PASSED                 [ 67%]
tests/test_irsa_client.py::test_observation_registry_insertion PASSED    [ 68%]
tests/test_science.py::test_aperture_photometry_gaussian_source PASSED   [ 70%]
tests/test_science.py::test_lightcurve_variability_classification PASSED [ 71%]
tests/test_science.py::test_astrometric_motion_measurement PASSED        [ 73%]
tests/test_science.py::test_catalog_endpoint_barnard PASSED              [ 75%]
tests/test_science.py::test_photometry_endpoint_demo PASSED              [ 76%]
tests/test_science.py::test_motion_endpoint_on_demo_epochs PASSED        [ 78%]
tests/test_science.py::test_discovery_report_endpoint PASSED             [ 79%]
tests/test_science.py::test_photometry_preset_differentiation PASSED     [ 81%]
tests/test_stacking_and_spectrum.py::test_compute_coadd_stack_mean_median_sum PASSED [ 82%]
tests/test_stacking_and_spectrum.py::test_compute_coadd_stack_nan_handling PASSED [ 84%]
tests/test_stacking_and_spectrum.py::test_compute_coadd_stack_wcs_reproject PASSED [ 85%]
tests/test_stacking_and_spectrum.py::test_spectrum_generation_102_channels PASSED [ 87%]
tests/test_stacking_and_spectrum.py::test_spectrum_endpoint_barnard PASSED [ 89%]
tests/test_stacking_and_spectrum.py::test_spectrum_endpoint_wise0855_brown_dwarf PASSED [ 90%]
tests/test_stacking_and_spectrum.py::test_spectrum_endpoint_sexagesimal PASSED [ 92%]
tests/test_stacking_and_spectrum.py::test_spectrum_endpoint_invalid_coords PASSED [ 93%]
tests/test_stacking_and_spectrum.py::test_stack_frames_endpoint_on_demo_epochs PASSED [ 95%]
tests/test_stacking_and_spectrum.py::test_stack_frames_endpoint_validation PASSED [ 96%]
tests/test_stacking_and_spectrum.py::test_stack_frames_endpoint_webp_and_median PASSED [ 98%]
tests/test_stacking_and_spectrum.py::test_compute_coadd_stack_edge_cases PASSED [100%]

============================= 64 passed in 5.28s ==============================
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
dist/assets/index-CsyE8zmx.css   29.74 kB │ gzip:  5.91 kB
dist/assets/index-DbKIRbtW.js   263.58 kB │ gzip: 72.98 kB
✓ built in 2.24s
```
