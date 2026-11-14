# SPHEREx Discovery — Test Execution Record

**Execution Timestamp:** 2026-11-14T17:35:00Z  
**Platform:** Windows 11 / Python 3.11.4 / Node.js v22.19.0  
**Test Suite Status:** 48 passed in 3.87s | Frontend Build: 0 errors in 2.70s

---

## 1. Automated Backend Test Suite (`pytest -v`)

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\haris\AppData\Local\Programs\Python\Python311\python.exe
cachedir: .pytest_cache
rootdir: C:\SphereX\spherex-discovery-2026\backend
plugins: anyio-4.12.1, zarr-3.1.6
collecting ... collected 48 items

tests/test_comparison.py::test_comparison_eligibility PASSED             [  2%]
tests/test_comparison.py::test_comparison_ra_boundary_wrapping PASSED    [  4%]
tests/test_comparison.py::test_compute_difference_frame PASSED           [  6%]
tests/test_comparison.py::test_compute_difference_frame_nan_handling PASSED [  8%]
tests/test_comparison.py::test_compute_difference_frame_wcs_reproject PASSED [ 10%]
tests/test_comparison.py::test_compute_difference_frame_fft_shift_fallback PASSED [ 12%]
tests/test_coordinates.py::test_parse_decimal_coordinates PASSED         [ 14%]
tests/test_coordinates.py::test_parse_string_decimal PASSED              [ 16%]
tests/test_coordinates.py::test_parse_sexagesimal_hms PASSED             [ 18%]
tests/test_coordinates.py::test_parse_sexagesimal_colon_format PASSED    [ 20%]
tests/test_coordinates.py::test_parse_sexagesimal_space_format PASSED    [ 22%]
tests/test_coordinates.py::test_parse_challenge_prompt_unicode_coordinates PASSED [ 25%]
tests/test_coordinates.py::test_empty_coordinate_input PASSED            [ 27%]
tests/test_coordinates.py::test_ra_wrapping PASSED                       [ 29%]
tests/test_coordinates.py::test_dec_out_of_range PASSED                  [ 31%]
tests/test_coordinates.py::test_invalid_input PASSED                     [ 33%]
tests/test_coordinates.py::test_format_sexagesimal PASSED                [ 35%]
tests/test_demo_resilience.py::test_demo_manifest_endpoint PASSED        [ 37%]
tests/test_demo_resilience.py::test_offline_observation_discovery_fallback PASSED [ 39%]
tests/test_demo_resilience.py::test_diff_on_demo_epochs PASSED           [ 41%]
tests/test_demo_resilience.py::test_webp_frame_and_diff_endpoints PASSED [ 43%]
tests/test_fits_processing.py::test_load_and_extract_image PASSED        [ 45%]
tests/test_fits_processing.py::test_extract_wcs PASSED                   [ 47%]
tests/test_fits_processing.py::test_evaluate_quality_flags PASSED        [ 50%]
tests/test_fits_processing.py::test_calculate_pixel_stats PASSED         [ 52%]
tests/test_fits_processing.py::test_asinh_and_zscale_stretch PASSED      [ 54%]
tests/test_fits_processing.py::test_render_image_to_base64_png PASSED    [ 56%]
tests/test_fits_processing.py::test_render_image_to_base64_webp PASSED   [ 58%]
tests/test_health.py::test_root PASSED                                   [ 60%]
tests/test_health.py::test_health PASSED                                 [ 62%]
tests/test_health.py::test_demo_presets PASSED                           [ 64%]
tests/test_image_registration.py::test_identical_images PASSED           [ 66%]
tests/test_image_registration.py::test_known_shift_recovery PASSED       [ 68%]
tests/test_image_registration.py::test_different_dimensions PASSED       [ 70%]
tests/test_image_registration.py::test_nan_and_inf_robustness PASSED     [ 72%]
tests/test_image_registration.py::test_constant_image PASSED             [ 75%]
tests/test_integration.py::test_full_explorer_flow PASSED                [ 77%]
tests/test_integration.py::test_invalid_coordinates_flow PASSED          [ 79%]
tests/test_irsa_client.py::test_irsa_client_parse PASSED                 [ 81%]
tests/test_irsa_client.py::test_observation_registry_insertion PASSED    [ 83%]
tests/test_science.py::test_aperture_photometry_gaussian_source PASSED   [ 85%]
tests/test_science.py::test_lightcurve_variability_classification PASSED [ 87%]
tests/test_science.py::test_astrometric_motion_measurement PASSED        [ 89%]
tests/test_science.py::test_catalog_endpoint_barnard PASSED              [ 91%]
tests/test_science.py::test_photometry_endpoint_demo PASSED              [ 93%]
tests/test_science.py::test_motion_endpoint_on_demo_epochs PASSED        [ 95%]
tests/test_discovery_report_endpoint PASSED                              [ 97%]
tests/test_science.py::test_photometry_preset_differentiation PASSED     [100%]

============================= 48 passed in 3.87s ==============================
```

---

## 2. Frontend Production Build (`npm run build`)

```text
> spherex-discovery@1.0.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 1496 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.96 kB │ gzip:  0.60 kB
dist/assets/index-BOxgsc3s.css   27.93 kB │ gzip:  5.63 kB
dist/assets/index--bF5XyNV.js   245.86 kB │ gzip: 69.81 kB
✓ built in 2.70s
```

---

## 3. Test Coverage Summary
- **Coordinates Parsing & Sanitization:** 11 tests (Unicode minus signs, HMS/DMS, wrapping, range enforcement)
- **FITS Processing & Radiometry:** 7 tests (HDU extraction, quality bitmasks, arcsinh/zscale contrast stretches, PNG and WebP encoding)
- **Celestial Differencing & Reprojection:** 6 tests (eligibility, RA wrapping, NaN handling, WCS reprojection with `reproject_interp`, 2D FFT shift fallback)
- **Sub-pixel Image Registration:** 5 tests (FFT phase cross-correlation, shift recovery, dimension tolerance, NaN robustness)
- **Photometry & Lightcurve Classification:** 2 tests (aperture flux integration, variability index differentiation)
- **Astrometric Motion Measurement:** 2 tests (proper motion vector calculation, confidence scoring)
- **API Endpoints & Integration:** 15 tests (health, demo presets, catalog overlay, discovery report, full explorer flow, WebP endpoints)
- **Total Test Count:** 48 passing automated tests (100% pass rate)
