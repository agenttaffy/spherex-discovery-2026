import io
import re

import httpx
import pytest
from astropy.io import fits

from app.science.spectral_cube import sample_channel_map, sample_cube
from app.services import cube_service
from app.services.cloud_cube import CloudCube, sample_cloud_cube, _range_cache
from test_spectral_cube import TARGET, URL, tile


def test_range_sample_matches_native_fits(tile):
    _range_cache.clear()
    buffer = io.BytesIO()
    tile.writeto(buffer)
    content = buffer.getvalue()
    seen = []

    def respond(request):
        assert request.url.host == "nasa-irsa-spherex.s3.us-east-1.amazonaws.com"
        match = re.fullmatch(r"bytes=(\d+)-(\d+)", request.headers["range"])
        assert match
        start, end = map(int, match.groups())
        if seen:
            assert request.headers["if-match"] == '"test-etag"'
        seen.append((start, end))
        return httpx.Response(206, headers={"Content-Range": f"bytes {start}-{end}/{len(content)}",
                                          "ETag": '"test-etag"'}, content=content[start:end + 1])

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result, provenance = sample_cloud_cube(client, URL, TARGET, 1)
    with fits.open(io.BytesIO(content)) as source:
        expected = sample_cube(source, TARGET)
        expected["channel_map"] = sample_channel_map(source, 1, 1, 1)
    assert result == expected
    assert provenance["etag"] == '"test-etag"' and len(seen) > 3


def test_switching_channels_reuses_only_etag_validated_ranges(tile):
    _range_cache.clear()
    buffer = io.BytesIO()
    tile.writeto(buffer)
    content = buffer.getvalue()
    calls = []
    etag = ['"version-1"']
    def respond(request):
        calls.append(request.headers["range"])
        start, end = map(int, re.fullmatch(r"bytes=(\d+)-(\d+)", request.headers["range"]).groups())
        return httpx.Response(206, headers={"Content-Range": f"bytes {start}-{end}/{len(content)}",
                                          "ETag": etag[0]}, content=content[start:end + 1])
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        first, _ = sample_cloud_cube(client, URL, TARGET, 1)
        initial = len(calls)
        second, _ = sample_cloud_cube(client, URL, TARGET, 2)
        reused = len(calls) - initial
        assert second["channels"] == first["channels"]
        assert second["channel_map"]["channel"] == 2
        assert reused < initial // 4
        etag[0] = '"version-2"'
        before = len(calls)
        sample_cloud_cube(client, URL, TARGET, 2)
        assert len(calls) - before > reused * 4


@pytest.mark.parametrize("mode", ["bad_range", "changed_etag", "full_response"])
def test_cloud_reader_rejects_unverifiable_or_changed_bytes(mode):
    calls = 0
    def respond(request):
        nonlocal calls
        calls += 1
        start, end = map(int, re.fullmatch(r"bytes=(\d+)-(\d+)", request.headers["range"]).groups())
        etag = '"changed"' if mode == "changed_etag" and calls > 1 else '"original"'
        header = f"bytes {start}-{end}/5760"
        if mode == "bad_range":
            header = "bytes 0-1/5760"
        return httpx.Response(200 if mode == "full_response" else 206,
                              headers={"Content-Range": header, "ETag": etag},
                              content=b"x" * (end - start + 1))
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        if mode == "changed_etag":
            obj = CloudCube(client, URL)
            with pytest.raises(ValueError, match="changed"):
                obj.read(2880, 2880)
        else:
            with pytest.raises(ValueError, match="invalid byte range"):
                CloudCube(client, URL)


def test_sia_outage_uses_explicitly_pinned_cloud_cube(monkeypatch):
    def offline(*_):
        raise httpx.ConnectError("SIA unavailable")
    monkeypatch.setattr(cube_service, "resolve_tile", offline)
    seen = {}
    def sample(_client, url, position, channel):
        seen["url"], seen["channel"] = url, channel
        return {"pixel": {}, "channels": []}, {"cloud_url": "test", "etag": '"etag"', "bytes_transferred": 1}
    monkeypatch.setattr(cube_service, "sample_cloud_cube", sample)
    result = cube_service.load_cube_spectrum(TARGET.ra.deg, TARGET.dec.deg, 75)
    assert result["source"] == "cloud_dr1_pinned"
    assert result["cloud"]["discovery"] == "pinned_dr1_release"
    assert result["cloud"]["pinned_version"] == "hips_20261026"
    assert seen["url"].endswith("/Npix7945_cube.fits") and seen["channel"] == 75


def test_explicit_pinned_cube_skips_sia_discovery(monkeypatch):
    def unexpected(*_):
        raise AssertionError("Pinned channel navigation must not query SIA")
    monkeypatch.setattr(cube_service, "resolve_tile", unexpected)
    monkeypatch.setattr(cube_service, "sample_cloud_cube", lambda *_: (
        {"pixel": {}, "channels": []}, {"cloud_url": "test", "etag": '"etag"', "bytes_transferred": 1}))
    result = cube_service.load_cube_spectrum(TARGET.ra.deg, TARGET.dec.deg, 2, use_pinned=True)
    assert result["source"] == "cloud_dr1_pinned"
