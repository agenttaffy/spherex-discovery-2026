import asyncio
from unittest.mock import AsyncMock

from app.api import science
from app.models.schemas import ObservationRecord


def test_analysis_does_not_download_unloaded_observations(monkeypatch):
    observation = ObservationRecord(id="cache-test", obs_id="example", collection="spherex_dr1", detector="SPHEREx-D1", access_url="https://example.invalid/image.fits", ra=5.0, dec=6.0)
    monkeypatch.setattr(science.irsa_client, "query_observations", AsyncMock(return_value=[observation]))
    monkeypatch.setattr(science.cutout_service, "fetch_cutout_fits", AsyncMock(side_effect=AssertionError("analysis must not download")))
    monkeypatch.setattr("app.services.cache_service.cache_service.get", lambda key: None)
    photo = asyncio.run(science.get_photometry(ra="5", dec="6", collection="spherex_dr1", detector="ALL", fov=0.04))
    spectrum = asyncio.run(science.get_spectrum(ra="5", dec="6", collection="spherex_dr1", fov=0.04))
    assert photo["analysis_source"] == "cached_cutouts_only"
    assert photo["observations_considered"] == 1 and photo["cutouts_available"] == 0
    assert spectrum["analysis_source"] == "cached_cutouts_only"
    assert spectrum["bands"] == [] and spectrum["channels_102"] == []
    science.cutout_service.fetch_cutout_fits.assert_not_awaited()


def test_analysis_uses_cached_cloud_cutout_without_network(monkeypatch):
    import io
    import numpy as np
    import pytest
    from astropy.io import fits
    from astropy.wcs import WCS
    from app.services.cache_service import cache_service
    from app.services.cutout_service import cutout_cache_key

    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [5.0, 6.0]
    wcs.wcs.crpix = [11.0, 11.0]
    wcs.wcs.cdelt = [-6.2 / 3600, 6.2 / 3600]
    pixels = np.zeros((21, 21))
    pixels[10, 10] = 5.0
    out = io.BytesIO()
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(pixels, header=wcs.to_header(), name="IMAGE"),
                  fits.ImageHDU(np.ones_like(pixels), name="VARIANCE")]).writeto(out)
    observation = ObservationRecord(id="cloud-only", obs_id="cloud-only", collection="spherex_dr1",
        detector="SPHEREx-D1", access_url="https://example.invalid/cloud-only.fits", ra=5.0, dec=6.0, mjd=60000)
    key = cutout_cache_key(observation.access_url, observation.ra, observation.dec, .04)
    looked_up = []
    def cached(key_requested):
        looked_up.append(key_requested)
        return out.getvalue() if key_requested == f"cloud-{key}" else None
    monkeypatch.setattr(cache_service, "get", cached)
    monkeypatch.setattr(science.irsa_client, "query_observations", AsyncMock(return_value=[observation]))
    monkeypatch.setattr(science.cutout_service, "fetch_cutout_fits", AsyncMock(side_effect=AssertionError("unexpected network")))
    photo = asyncio.run(science.get_photometry(ra="5", dec="6", collection="spherex_dr1", detector="ALL", fov=.04))
    spectrum = asyncio.run(science.get_spectrum(ra="5", dec="6", collection="spherex_dr1", fov=.04))
    assert photo["cutouts_available"] == 1
    assert photo["points"][0]["net_flux_mjy_sr"] == pytest.approx(5.0)
    assert spectrum["bands"][0]["flux_mjy_sr"] == pytest.approx(5.0)
    assert looked_up.count(f"cloud-{key}") == 2
    science.cutout_service.fetch_cutout_fits.assert_not_awaited()


def test_flat_background_without_variance_does_not_invent_noise():
    import numpy as np
    from app.science.photometry import compute_aperture_photometry
    image = np.full((21, 21), 10.0)
    image[10, 10] = 20.0
    result = compute_aperture_photometry(image, center_x=10, center_y=10)
    assert not result["valid"]
    assert result["flux_err"] is None
    assert "uncertainty" in result["reason"]


def test_negative_background_subtracted_measurement_keeps_signed_snr():
    import numpy as np
    from app.science.photometry import compute_aperture_photometry
    image = np.full((21, 21), 10.0)
    image[10, 10] = 0.0
    result = compute_aperture_photometry(image, center_x=10, center_y=10, variance=np.ones_like(image))
    assert result["valid"] and result["net_flux"] < 0 and result["snr"] < 0


def test_small_valid_uncertainty_is_not_rounded_to_zero():
    import numpy as np
    import pytest
    from app.science.photometry import compute_aperture_photometry
    image = np.zeros((21, 21))
    image[10, 10] = 0.00001
    result = compute_aperture_photometry(image, center_x=10, center_y=10,
                                          variance=np.full_like(image, 1e-14))
    assert result["valid"]
    assert 0 < result["flux_err"] < 1e-6
    assert result["net_flux"] == pytest.approx(1e-5)
    assert result["snr"] == pytest.approx(result["net_flux"] / result["flux_err"])


def test_detector_field_sample_preserves_small_flux_and_uncertainty(monkeypatch):
    import io
    import numpy as np
    import pytest
    from astropy.io import fits
    from app.science import spectrum
    from app.services.cache_service import cache_service

    buffer = io.BytesIO()
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(np.ones((21, 21)), name="IMAGE")]).writeto(buffer)
    monkeypatch.setattr(cache_service, "get", lambda key: buffer.getvalue())
    monkeypatch.setattr(spectrum, "compute_aperture_photometry", lambda **kwargs: {
        "valid": True, "net_flux": 1e-5, "peak_flux": 2e-5, "flux_err": 1e-7,
        "background_std": 1e-7, "snr": 100.0, "uncertainty_source": "variance_propagated",
    })
    observation = ObservationRecord(id="small", obs_id="small", collection="spherex_dr1",
        detector="SPHEREx-D1", access_url="https://example.invalid/image", ra=5.0, dec=6.0)
    result = spectrum.generate_spectrum_for_target(5.0, 6.0, [observation], None)
    assert len(result["bands"]) == 1
    assert result["bands"][0]["flux_mjy_sr"] == pytest.approx(1e-5)
    assert result["bands"][0]["flux_err_mjy_sr"] == pytest.approx(1e-7)
