import asyncio
import io
import re
from contextlib import nullcontext
from unittest.mock import AsyncMock, patch

import httpx
import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from app.services.cloud_cutout import CloudRangeReader, cloud_cutout, cloud_url_from_irsa
from app.services.cutout_service import CutoutService

URL = ("https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W33_2C/"
       "l2b-v27-2026-228/6/level2_2025W33_2C_0321_2D6_spx_l2b-v27-2026-228.fits")


def source_image():
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [51., 51.]
    wcs.wcs.cdelt = [-.001, .001]
    wcs.wcs.crval = [10., 20.]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    header = wcs.to_header()
    header["OBSID"] = "2025W33_2C_0321_2"
    header["DETECTOR"] = 6
    for axis in (1, 2):
        header[f"CRPIX{axis}A"] = 1.
        header[f"CRPIX{axis}W"] = 1.
    base = np.arange(10000, dtype=np.float32).reshape(100, 100)
    hdus = [fits.PrimaryHDU()]
    for name, data in (("IMAGE", base), ("FLAGS", base.astype(np.int32)),
                       ("VARIANCE", base + 1), ("ZODI", base + 2)):
        hdus.append(fits.ImageHDU(data, header=header, name=name))
    hdus.append(fits.BinTableHDU.from_columns([fits.Column(name="X", format="J", array=[1])], name="WCS-WAVE"))
    output = io.BytesIO()
    fits.HDUList(hdus).writeto(output)
    return output.getvalue()


def range_response(payload):
    def get(client, method, url, headers):
        match = re.fullmatch(r"bytes=(\d+)-(\d+)", headers["Range"])
        start, end = map(int, match.groups())
        data = payload[start:end + 1]
        return nullcontext(httpx.Response(206, headers={"Content-Range": f"bytes {start}-{end}/{len(payload)}",
                                                       "ETag": '"unchanged"'}, content=data,
                                         request=httpx.Request("GET", url)))
    return get


def test_cloud_cutout_preserves_native_planes_and_mapping():
    with patch.object(httpx.Client, "stream", new=range_response(source_image())):
        data = cloud_cutout(URL, 10., 20., .02)
    with fits.open(io.BytesIO(data)) as output:
        assert set(["IMAGE", "FLAGS", "VARIANCE", "ZODI", "WCS-WAVE"]).issubset(h.name for h in output)
        image = output["IMAGE"]
        x0, y0 = 1 - int(image.header["CRPIX1A"]), 1 - int(image.header["CRPIX2A"])
        assert image.header["CRPIX1W"] == image.header["CRPIX1A"]
        assert image.header["CRPIX2W"] == image.header["CRPIX2A"]
        assert image.header["CRPIX1"] == 51 - x0
        original = np.arange(10000, dtype=np.float32).reshape(100, 100)
        expected = original[y0:y0 + image.shape[0], x0:x0 + image.shape[1]]
        np.testing.assert_array_equal(image.data, expected)
        np.testing.assert_array_equal(output["FLAGS"].data, expected.astype(np.int32))
        np.testing.assert_array_equal(output["VARIANCE"].data, expected + 1)


def test_cloud_url_allowlist_rejects_untrusted_paths():
    assert cloud_url_from_irsa(URL).startswith("https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/dr1/")
    assert cloud_url_from_irsa(URL.replace("l2b-v", "l2b_retry-v"))
    for value in (URL + "?x=1", URL.replace("irsa.ipac.caltech.edu", "example.com"),
                  URL.replace("/level2/", "/../level2/"), URL.replace("https://", "http://")):
        assert cloud_url_from_irsa(value) is None


def test_range_reader_rejects_changed_object():
    first = httpx.Response(206, headers={"Content-Range": "bytes 0-2879/5760", "ETag": '"a"'},
                           content=b"a" * 2880, request=httpx.Request("GET", "https://example.test"))
    changed = httpx.Response(206, headers={"Content-Range": "bytes 0-5759/5760", "ETag": '"b"'},
                             content=b"b" * 5760, request=httpx.Request("GET", "https://example.test"))
    with patch.object(httpx.Client, "stream", side_effect=[nullcontext(first), nullcontext(changed)]):
        with httpx.Client() as client:
            reader = CloudRangeReader(client, "https://example.test")
            with pytest.raises(ValueError, match="identity changed"):
                reader.read(1)


def test_range_reader_rejects_full_object_response_before_reading_body():
    class ForbiddenBody(httpx.SyncByteStream):
        def __iter__(self):
            raise AssertionError("A full object response must never be read")
    response = httpx.Response(200, stream=ForbiddenBody(), request=httpx.Request("GET", "https://example.test"))
    with patch.object(httpx.Client, "stream", return_value=nullcontext(response)):
        with httpx.Client() as client, pytest.raises(ValueError, match="invalid FITS byte range"):
            CloudRangeReader(client, "https://example.test")


def test_range_reader_stops_when_overall_deadline_is_exceeded():
    with patch("app.services.cloud_cutout.time.monotonic", side_effect=[0, 40]), \
         patch.object(httpx.Client, "stream") as stream:
        with httpx.Client() as client, pytest.raises(ValueError, match="time limit"):
            CloudRangeReader(client, "https://example.test")
        stream.assert_not_called()


def test_cloud_preferred_then_cached_and_ibe_fallback():
    service = CutoutService()
    store = {}
    valid = source_image()
    with patch("app.services.cutout_service.DEMO_CACHE_ONLY", False), \
         patch("app.services.cutout_service.cache_service.get", side_effect=lambda key: store.get(key)), \
         patch("app.services.cutout_service.cache_service.set", side_effect=lambda key, value: store.update({key: value})), \
         patch("app.services.cutout_service.cloud_cutout", return_value=valid) as make:
        assert asyncio.run(service.fetch_cutout_with_source(URL, 10, 20, .02)) == (valid, "live_cloud_cutout")
        assert asyncio.run(service.fetch_cutout_with_source(URL, 10, 20, .02)) == (valid, "cached_cloud_cutout")
        assert make.call_count == 1
    with patch("app.services.cutout_service.DEMO_CACHE_ONLY", False), \
         patch("app.services.cutout_service.cache_service.get", return_value=None), \
         patch("app.services.cutout_service.cache_service.set"), \
         patch("app.services.cutout_service.cloud_cutout", side_effect=ValueError("no cloud")), \
         patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(200, content=valid))):
        assert asyncio.run(service.fetch_cutout_with_source(URL, 10, 20, .02)) == (valid, "live_archive_cutout")


def test_cache_only_mode_never_fetches_missing_cutout():
    service = CutoutService()
    with patch("app.services.cutout_service.DEMO_CACHE_ONLY", True), \
         patch("app.services.cutout_service.cache_service.get", return_value=None), \
         patch("app.services.cutout_service.cloud_cutout") as cloud, \
         patch("httpx.AsyncClient.get", new=AsyncMock()) as archive:
        with pytest.raises(ValueError, match="local demo cache"):
            asyncio.run(service.fetch_cutout_with_source(URL, 10, 20, .02))
    cloud.assert_not_called()
    archive.assert_not_awaited()


@pytest.mark.parametrize("payload", [b"<html>maintenance</html>", b"not FITS" * 360])
def test_http_200_error_page_is_not_cached(payload):
    service = CutoutService()
    with patch("app.services.cutout_service.DEMO_CACHE_ONLY", False), \
         patch("app.services.cutout_service.cache_service.get", return_value=None), \
         patch("app.services.cutout_service.cache_service.set") as save, \
         patch("app.services.cutout_service.cloud_cutout", side_effect=ValueError("cloud unavailable")), \
         patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(200, content=payload))):
        with pytest.raises(ValueError, match="FITS"):
            asyncio.run(service.fetch_cutout_with_source(URL, 10, 20, .02))
    save.assert_not_called()


def test_wrong_observation_and_invalid_cached_bytes_do_not_survive():
    from app.services.cutout_service import cutout_cache_key
    valid = source_image()
    wrong = URL.replace("0321_2D6", "0321_3D6")
    service = CutoutService()
    store = {cutout_cache_key(wrong, 10, 20, .02): b"invalid old cached HTML"}
    with patch("app.services.cutout_service.DEMO_CACHE_ONLY", False), \
         patch("app.services.cutout_service.cache_service.get", side_effect=lambda key: store.get(key)), \
         patch("app.services.cutout_service.cache_service.set") as save, \
         patch("app.services.cutout_service.cloud_cutout", side_effect=ValueError("cloud unavailable")), \
         patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(200, content=valid))):
        with pytest.raises(ValueError, match="identity"):
            asyncio.run(service.fetch_cutout_with_source(wrong, 10, 20, .02))
    save.assert_not_called()
