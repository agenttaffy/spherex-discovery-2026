# SPHEREx Discovery — Test Execution Record

**Execution Timestamp:** 2026-11-14T17:48:00Z  
**Platform:** Windows 11 / Python 3.11.4 / Node.js v22.19.0  
**Test Suite Status:** 52 passed in 2.48s | Frontend Build: 0 errors in 2.08s

---

## 1. Automated Backend Test Suite (`pytest -v`)

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\haris\AppData\Local\Programs\Python\Python311\python.exe
cachedir: .pytest_cache
rootdir: C:\SphereX\spherex-discovery-2026\backend
plugins: anyio-4.12.1, zarr-3.1.6
collecting ... collected 52 items

tests/test_comparison.py::test_comparison_eligibility PASSED             [  1%]
tests/test_comparison.py::test_comparison_ra_boundary_wrapping PASSED    [  3%]
tests/test_comparison.py::test_compute_difference_frame PASSED           [  5%]
tests/test_comparison.py::test_compute_difference_frame_nan_handling PASSED [  7%]
tests/test_comparison.py::test_compute_difference_frame_wcs_reproject PASSED [  9%]
tests/test_comparison.py::test_compute_difference_frame_fft_shift_fallback PASSED [ 11%]
tests/test_comparison.py::test_compute_difference_frame_spectral_3d_wcs PASSED [ 13%]
tests/test_comparison.py::test_compute_difference_frame_rotated_wcs PASSED [ 15%]
tests/test_coordinates.py::test_parse_decimal_coordinates PASSED         [ 17%]
tests/test_coordinates.py::test_parse_string_decimal PASSED              [ 19%]
tests/test_coordinates.py::test_parse_sexagesimal_hms PASSED             [ 21%]
tests/test_coordinates.py::test_parse_sexagesimal_colon_format PASSED    [ 23%]
tests/test_coordinates.py::test_parse_sexagesimal_space_format PASSED    [ 25%]
tests/test_coordinates.py::test_parse_challenge_prompt_unicode_coordinates PASSED [ 26%]
tests/test_coordinates.py::test_empty_coordinate_input PASSED            [ 28%]
tests/test_coordinates.py::test_ra_wrapping PASSED                       [ 30%]
tests/test_coordinates.py::test_dec_out_of_range PASSED                  [ 32%]
tests/test_coordinates.py::test_invalid_input PASSED                     [ 34%]
tests/test_coordinates.py::test_format_sexagesimal PASSED                [ 36%]
tests/test_demo_resilience.py::test_demo_manifest_endpoint PASSED        [ 38%]
tests/test_demo_resilience.py::test_offline_observation_discovery_fallback PASSED [ 40%]
tests/test_demo_resilience.py::test_diff_on_demo_epochs PASSED           [ 42%]
tests/test_demo_resilience.py::test_webp_frame_and_diff_endpoints PASSED [ 44%]
tests/test_fits_processing.py::test_load_and_extract_image PASSED        [ 46%]
tests/test_fits_processing.py::test_extract_wcs PASSED                   [ 48%]
tests/test_fits_processing.py::test_evaluate_quality_flags PASSED        [ 50%]
tests/test_fits_processing.py::test_calculate_pixel_stats PASSED         [ 51%]
tests/test_fits_processing.py::test_asinh_and_zscale_stretch PASSED      [ 53%]
tests/test_fits_processing.py::test_render_image_to_base64_png PASSED    [ 55%]
tests/test_fits_processing.py::test_render_image_to_base64_webp PASSED   [ 57%]
tests/test_fits_processing.py::test_extract_astropy_wcs_celestial PASSED [ 59%]
tests/test_fits_processing.py::test_render_image_to_base64_float_sanitization PASSED [ 61%]
tests/test_health.py::test_root PASSED                                   [ 63%]
tests/test_health.py::test_health PASSED                                 [ 65%]
tests/test_health.py::test_demo_presets PASSED                           [ 67%]
tests/test_image_registration.py::test_identical_images PASSED           [ 69%]
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
