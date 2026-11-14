# SPHEREx Discovery — Test Execution Record

**Execution Timestamp:** 2026-11-14T17:10:00Z  
**Platform:** Windows 11 / Python 3.11.4 / Node.js v22.19.0  
**Test Suite Status:** 44 passed in 1.87s | Frontend Build: 0 errors in 1.93s

---

## 1. Automated Backend Test Suite (`pytest -v`)

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\SphereX\spherex-discovery-2026\backend
plugins: anyio-4.12.1
collected 43 items

tests/test_comparison.py::test_comparison_eligibility PASSED             [  2%]
tests/test_comparison.py::test_comparison_ra_boundary_wrapping PASSED    [  4%]
tests/test_comparison.py::test_compute_difference_frame PASSED           [  6%]
tests/test_comparison.py::test_compute_difference_frame_nan_handling PASSED [  9%]
tests/test_coordinates.py::test_parse_decimal_coordinates PASSED         [ 11%]
tests/test_coordinates.py::test_parse_string_decimal PASSED              [ 13%]
tests/test_coordinates.py::test_parse_sexagesimal_hms PASSED             [ 16%]
tests/test_coordinates.py::test_parse_sexagesimal_colon_format PASSED    [ 18%]
tests/test_coordinates.py::test_parse_sexagesimal_space_format PASSED    [ 20%]
tests/test_coordinates.py::test_parse_challenge_prompt_unicode_coordinates PASSED [ 23%]
tests/test_coordinates.py::test_empty_coordinate_input PASSED            [ 25%]
tests/test_coordinates.py::test_ra_wrapping PASSED                       [ 27%]
tests/test_coordinates.py::test_dec_out_of_range PASSED                  [ 30%]
tests/test_coordinates.py::test_invalid_input PASSED                     [ 32%]
tests/test_coordinates.py::test_format_sexagesimal PASSED                [ 34%]
tests/test_demo_resilience.py::test_demo_manifest_endpoint PASSED        [ 37%]
tests/test_demo_resilience.py::test_offline_observation_discovery_fallback PASSED [ 39%]
tests/test_demo_resilience.py::test_diff_on_demo_epochs PASSED           [ 41%]
tests/test_fits_processing.py::test_load_and_extract_image PASSED        [ 44%]
tests/test_fits_processing.py::test_extract_wcs PASSED                   [ 46%]
tests/test_fits_processing.py::test_evaluate_quality_flags PASSED        [ 48%]
tests/test_fits_processing.py::test_calculate_pixel_stats PASSED         [ 51%]
tests/test_fits_processing.py::test_asinh_and_zscale_stretch PASSED      [ 53%]
tests/test_fits_processing.py::test_render_image_to_base64_png PASSED    [ 55%]
tests/test_health.py::test_root PASSED                                   [ 58%]
tests/test_health.py::test_health PASSED                                 [ 60%]
tests/test_health.py::test_demo_presets PASSED                           [ 62%]
tests/test_image_registration.py::test_identical_images PASSED           [ 65%]
tests/test_image_registration.py::test_known_shift_recovery PASSED       [ 67%]
tests/test_image_registration.py::test_different_dimensions PASSED       [ 69%]
tests/test_image_registration.py::test_nan_and_inf_robustness PASSED     [ 72%]
tests/test_image_registration.py::test_constant_image PASSED             [ 74%]
tests/test_integration.py::test_full_explorer_flow PASSED                [ 76%]
tests/test_integration.py::test_invalid_coordinates_flow PASSED          [ 79%]
tests/test_irsa_client.py::test_irsa_client_parse PASSED                 [ 81%]
tests/test_irsa_client.py::test_observation_registry_insertion PASSED    [ 83%]
tests/test_science.py::test_aperture_photometry_gaussian_source PASSED   [ 86%]
tests/test_science.py::test_lightcurve_variability_classification PASSED [ 88%]
tests/test_science.py::test_astrometric_motion_measurement PASSED        [ 90%]
tests/test_science.py::test_catalog_endpoint_barnard PASSED              [ 93%]
tests/test_science.py::test_photometry_endpoint_demo PASSED              [ 95%]
tests/test_science.py::test_motion_endpoint_on_demo_epochs PASSED        [ 95%]
tests/test_science.py::test_discovery_report_endpoint PASSED             [ 97%]
tests/test_science.py::test_photometry_preset_differentiation PASSED     [100%]

============================= 44 passed in 1.87s ==============================
```

---

## 2. Frontend Production Compilation (`npm run build`)

```text
> spherex-discovery@1.0.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 1495 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.79 kB │ gzip:  0.51 kB
dist/assets/index-zcSGku4F.css   27.52 kB │ gzip:  5.55 kB
dist/assets/index-CZNo6Ct5.js   232.43 kB │ gzip: 66.51 kB
✓ built in 1.94s
```

---

## 3. Demonstration Assets Verification (`python scripts/verify_demo.py`)
- Verified all 22 cached multi-extension FITS cutouts across all 5 official challenge targets.
- Integrity: 100% valid FITS dimensions, valid WCS headers, and finite pixel statistics.
