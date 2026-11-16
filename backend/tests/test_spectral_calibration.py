import hashlib
import io

import httpx
import numpy as np
import pytest
from astropy.io import fits

from app.science.calibrated_comparison import prepare_calibrated_exposure
from app.science.spectral_calibration import map_calibration_to_cutout, spectral_calibration_plane_id
from app.services.spectral_calibration_service import find_calibration_artifact
from app.services import spectral_calibration_service as calibration


@pytest.mark.parametrize(("detector", "plane_id", "checksum"), [
    ("3", "019f4f99-19af-763f-8f2e-b7dc6cd00055", "327f973e59efeaa101bf1fe9ac7c354e"),
    ("5", "019f4f99-48fc-73a4-b778-eb25bf616d6b", "d59bd98b5d1d14ae8d74499b1c1ccb3f"),
])
def test_pinned_artifact_requires_exact_identity_and_cache_checksum(detector, plane_id, checksum, tmp_path, monkeypatch):
    artifact = calibration.verified_artifact("dr1", detector, plane_id)
    assert artifact is not None and artifact.checksum == checksum
    assert f"/dr1/spectral_wcs/cal-swcs-v5-2026-191/{detector}/" in artifact.url
    # A QR3 image citing the exact same TAP-verified plane UUID can use the
    # identical DR1 calibration; a different or legacy release cannot.
    assert calibration.verified_artifact("qr3", detector, plane_id) == artifact
    assert calibration.verified_artifact("qr2", detector, plane_id) is None
    assert calibration.verified_artifact("dr1", "6", plane_id) is None
    assert calibration.verified_artifact("dr1", detector, "unresolved") is None

    monkeypatch.setattr(calibration, "CACHE_DIR", tmp_path)
    destination = tmp_path / "spectral-calibration"
    destination.mkdir()
    (destination / f"spectral-{checksum}.fits").write_bytes(b"corrupt")
    assert calibration.verified_cached_bytes(artifact) is None
    monkeypatch.setattr(calibration, "DEMO_CACHE_ONLY", True)
    image = fits.ImageHDU(name="IMAGE")
    image.header["DETECTOR"] = int(detector)
    image.header.add_history(f"[CALIB] spectral_wcs {plane_id}")
    with pytest.raises(ValueError, match="calibration bytes are missing"):
        calibration.load_calibrated_exposure(fits.HDUList([fits.PrimaryHDU(), image]), "dr1")


def test_calibration_mapping_requires_verified_identity_and_maps_exact_pixels():
    plane_id = "019f4f98-edf0-744b-9600-424841d46dc0"
    image = fits.ImageHDU(data=np.ones((2, 3)), name="IMAGE")
    for key, value in {"CRPIX1A": -1, "CRPIX2A": 0, "CRVAL1A": 0, "CRVAL2A": 0,
                       "CTYPE1A": "LINEAR", "CTYPE2A": "LINEAR", "CDELT1A": 1,
                       "CDELT2A": 1, "DETECTOR": 1}.items():
        image.header[key] = value
    image.header.add_history(f"[CALIB] spectral_wcs {plane_id}")
    science = fits.HDUList([fits.PrimaryHDU(), image])
    wave = np.arange(30, dtype=np.float32).reshape(5, 6) + 1
    band = np.ones((5, 6), dtype=np.float32) * 0.1
    wave_hdu = fits.ImageHDU(wave, name="CWAVE")
    band_hdu = fits.ImageHDU(band, name="CBAND")
    for hdu in (wave_hdu, band_hdu):
        hdu.header["DETECTOR"] = 1
        hdu.header["BUNIT"] = "um"
    output = io.BytesIO()
    fits.HDUList([fits.PrimaryHDU(), wave_hdu, band_hdu]).writeto(output)
    content = output.getvalue()
    checksum = "md5:" + hashlib.md5(content).hexdigest()

    actual_wave, actual_band = map_calibration_to_cutout(science, content, plane_id=plane_id, checksum=checksum)
    np.testing.assert_array_equal(actual_wave, wave[1:3, 2:5])
    np.testing.assert_allclose(actual_band, band[1:3, 2:5])
    with pytest.raises(ValueError, match="checksum mismatch"):
        map_calibration_to_cutout(science, content, plane_id=plane_id, checksum="0" * 32)
    with pytest.raises(ValueError, match="does not match"):
        map_calibration_to_cutout(science, content, plane_id="0" * 36, checksum=checksum)
    image.header["BUNIT"] = "MJy / sr"
    image.header["CTYPE1"] = "RA---TAN"
    image.header["CTYPE2"] = "DEC--TAN"
    with pytest.raises(ValueError, match="requires a documented quality mask"):
        prepare_calibrated_exposure(science, content, plane_id=plane_id, checksum=checksum)
    flags = fits.ImageHDU(np.array([[0, 1, 0], [0, 0, 0]], dtype=np.int32), name="FLAGS")
    flags.header["MSKN0000"] = "TRANSIENT"
    flags.header["MSKM0000"] = 1
    variance = fits.ImageHDU(np.ones((2, 3)), name="VARIANCE")
    variance.header["BUNIT"] = "MJy2 / sr2"
    science.extend((flags, variance))
    exposure = prepare_calibrated_exposure(science, content, plane_id=plane_id, checksum=checksum)
    np.testing.assert_array_equal(exposure.wavelength, actual_wave)
    assert not exposure.usable()[0, 1]
    assert exposure.usable().sum() == 5
    image.header["PC1_2A"] = 0.1
    with pytest.raises(ValueError, match="matrix"):
        map_calibration_to_cutout(science, content, plane_id=plane_id, checksum=checksum)


def test_calibration_catalog_requires_unique_release_detector_and_checksum():
    plane_id = "019f4f98-edf0-744b-9600-424841d46dc0"
    image = fits.ImageHDU(name="IMAGE")
    image.header["DETECTOR"] = 1
    image.header.add_history(f"[CALIB] spectral_wcs {plane_id}")
    image.header.add_history(f"[CALIB] spectral_wcs {plane_id}")
    science = fits.HDUList([fits.PrimaryHDU(), image])
    path = "ibe/data/spherex/dr1/spectral_wcs/cal-wcs-v2.2-2026-190/1/calibration.fits"
    md5 = "c" * 32

    def tap(request):
        assert f"planeid='{plane_id}'" in request.url.params["QUERY"]
        return httpx.Response(200, text="uri,contentchecksum\n" + "\n".join([
            f"https://other.example/{path},md5:{md5}",
            f"{path.replace('/dr1/', '/qr3/')},md5:{md5}",
            f"{path.replace('/1/', '/2/')},md5:{md5}",
            f"{path},md5:{md5}",
        ]))

    with httpx.Client(transport=httpx.MockTransport(tap)) as client:
        result = find_calibration_artifact(client, science, "dr1")
        assert result.plane_id == plane_id
        assert result.url == "https://irsa.ipac.caltech.edu/" + path
        assert result.checksum == md5
        with pytest.raises(ValueError, match="No unique"):
            find_calibration_artifact(client, science, "qr2")

    image.header.add_history("[CALIB] spectral_wcs 00000000-0000-0000-0000-000000000000")
    with pytest.raises(ValueError, match="Exactly one"):
        spectral_calibration_plane_id(science)


def test_missing_and_ambiguous_calibration_do_not_substitute_a_map():
    image = fits.ImageHDU(name="IMAGE")
    image.header["DETECTOR"] = 5
    science = fits.HDUList([fits.PrimaryHDU(), image])
    with pytest.raises(ValueError, match="Exactly one"):
        spectral_calibration_plane_id(science)
    image.header.add_history("[CALIB] spectral_wcs 019f4f99-48fc-73a4-b778-eb25bf616d6b")
    base = "ibe/data/spherex/dr1/spectral_wcs/cal-swcs-v5-2026-191/5/"
    header = "uri,contentchecksum\n"
    first = f"{base}one.fits,md5:{'a' * 32}\n"
    for payload in (header, header + first + f"{base}two.fits,md5:{'b' * 32}\n"):
        transport = httpx.MockTransport(lambda request: httpx.Response(200, text=payload))
        with httpx.Client(transport=transport) as client:
            with pytest.raises(ValueError, match="No unique"):
                find_calibration_artifact(client, science, "qr3")


def test_calibration_cloud_mirror_requires_verified_checksum_and_falls_back():
    body = b"verified calibration bytes"
    artifact = calibration.CalibrationArtifact("plane", "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/spectral_wcs/cal-swcs-v5-2026-191/1/spectral_wcs_D1.fits", hashlib.md5(body).hexdigest())
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, content=b"corrupt" if request.url.host.endswith("amazonaws.com") else body)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert calibration.download_verified_bytes(client, artifact) == body
    assert len(calls) == 2
    assert calls[0].startswith("https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/dr1/")
    assert calls[1] == artifact.url


def test_calibration_never_accepts_unverified_download_or_arbitrary_source():
    artifact = calibration.CalibrationArtifact("plane", "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/spectral_wcs/cal-swcs-v5-2026-191/1/spectral_wcs_D1.fits", "0" * 32)
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"wrong"))) as client:
        with pytest.raises(ValueError, match="could not be downloaded"):
            calibration.download_verified_bytes(client, artifact)
        with pytest.raises(ValueError, match="Unsupported"):
            calibration.download_verified_bytes(client, calibration.CalibrationArtifact("plane", "https://evil.example/file", "0" * 32))
