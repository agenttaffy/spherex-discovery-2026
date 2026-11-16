import astropy.units as u
import httpx
import numpy as np
import pytest
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS

from app.science.spectral_cube import CubeCoverageError, SOURCE_FLAG, sample_channel_map, sample_cube
from app.services.cube_service import resolve_tile

URL = "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/hips5_cube/hips_20261026/Norder5/Dir0/Npix7945_cube.fits"
TARGET = SkyCoord(269.45208 * u.deg, 4.69339 * u.deg, frame="icrs")


@pytest.fixture
def tile():
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---HPX", "DEC--HPX"]
    wcs.wcs.crpix = [2, 2]
    wcs.wcs.crval = [TARGET.ra.deg, TARGET.dec.deg]
    wcs.wcs.cdelt = [-12.9 / 3600, 12.9 / 3600]
    header = wcs.to_header()
    header["BUNIT"] = "MJy/sr"
    values = np.zeros((102, 3, 3), dtype=np.float32)
    values[:, 1, 1] = np.arange(102) + 0.25
    values[0, 0, 2], values[0, 2, 0] = 7, 13
    values[3, 1, 1] = np.nan
    hits = np.full((102, 3, 3), 4, dtype=np.int32)
    hits[4, 1, 1] = 0
    flags = np.zeros_like(hits)
    flags[0, 1, 1] = SOURCE_FLAG
    flags[5, 1, 1] = np.int32(-2147483648)
    centers = np.linspace(0.75, 5.0, 102)
    columns = [
        fits.Column(name="DETECTOR", format="I", array=np.repeat(np.arange(1, 7), 17)),
        fits.Column(name="SUBCHAN", format="I", array=np.tile(np.arange(1, 18), 6)),
    ]
    for name, data in (
        ("WAVELENGTH", centers), ("WL_MIN", centers - 0.01),
        ("WL_MAX", centers + 0.01), ("BANDWIDTH", np.full(102, 0.02)),
    ):
        columns.append(fits.Column(name=name, format="E", unit="um", array=data))
    return fits.HDUList([
        fits.PrimaryHDU(),
        fits.ImageHDU(values, header=header, name="IMAGE"),
        fits.ImageHDU(hits, name="NHITS"),
        fits.ImageHDU(flags, name="FLAGS"),
        fits.BinTableHDU.from_columns(columns, name="SPECTRAL_CHANNELS"),
    ])


def test_sample_native_pixel_and_preserve_channel_metadata(tile, tmp_path):
    tile.writeto(tmp_path / "tile.fits")
    with fits.open(tmp_path / "tile.fits", memmap=True) as on_disk:
        result = sample_cube(on_disk, TARGET)
        native = sample_channel_map(on_disk, 1, 1, 1)["pixels"]
        assert native == [[0, 0, 7], [0, .25, 0], [13, 0, 0]]
        assert sample_channel_map(on_disk, 1, 1, 6)["pixels"][1][1] is None
        assert sample_channel_map(on_disk, 1, 1, 51)["pixels"] == [[None] * 3] * 3
    assert (result["pixel"]["x"], result["pixel"]["y"]) == (1, 1)
    channels = result["channels"]
    assert [c["channel"] for c in channels] == list(range(1, 103))
    assert channels[0]["wavelength_um"] == pytest.approx(0.75)
    assert channels[-1]["wavelength_max_um"] == pytest.approx(5.01)
    assert channels[-1]["bandwidth_um"] == pytest.approx(0.02)
    assert channels[0]["surface_brightness_mjy_sr"] == 0.25
    assert channels[0]["hits"] == 4
    assert channels[0]["flags"] == SOURCE_FLAG
    for index, status in ((3, "no_coverage"), (4, "no_coverage"), (5, "flagged"),
                          (50, "blank_channel"), (51, "blank_channel")):
        assert channels[index]["status"] == status
        assert channels[index]["surface_brightness_mjy_sr"] is None
    assert channels[5]["flags"] == 0x80000000
    assert channels[5]["archive_brightness_mjy_sr"] == 5.25


def test_position_outside_tile(tile):
    with pytest.raises(CubeCoverageError):
        sample_cube(tile, SkyCoord(270 * u.deg, 5 * u.deg, frame="icrs"))


def test_missing_wavelength_preserves_raw_brightness_as_diagnostic(tile, tmp_path):
    tile["SPECTRAL_CHANNELS"].data["WAVELENGTH"][6] = np.nan
    path = tmp_path / "missing_wavelength.fits"
    tile.writeto(path)
    with fits.open(path) as on_disk:
        record = sample_cube(on_disk, TARGET)["channels"][6]
    assert record["channel"] == 7
    assert record["wavelength_um"] is None
    assert record["bandwidth_um"] == pytest.approx(.02)
    assert record["hits"] == 4
    assert record["status"] == "missing_wavelength"
    assert record["surface_brightness_mjy_sr"] is None
    assert record["archive_brightness_mjy_sr"] == 6.25


def test_wrong_detector_subchannel_order_is_rejected(tile, tmp_path):
    tile["SPECTRAL_CHANNELS"].data["SUBCHAN"][17] = 2
    path = tmp_path / "out_of_order.fits"
    tile.writeto(path)
    with fits.open(path) as on_disk, pytest.raises(ValueError, match="Unexpected spectral channel order"):
        sample_cube(on_disk, TARGET)


@pytest.mark.parametrize("include_tile", [True, False])
@pytest.mark.parametrize(("position", "tile_index", "archive_url"), [
    (TARGET, 7945, URL),
    (SkyCoord(133.75896227492004, -7.242116064321349, unit="deg"), 10226,
     URL.replace("Dir0/Npix7945", "Dir10000/Npix10226")),
])
def test_tile_resolution_uses_nested_index_and_archive_host(include_tile, position, tile_index, archive_url):
    def sia(request):
        assert request.url.params["COLLECTION"] == "spherex_dr1_cube"
        urls = [archive_url.replace(f"Npix{tile_index}", f"Npix{tile_index - 1}"),
                archive_url.replace("irsa.ipac.caltech.edu", "example.org")]
        if include_tile:
            urls.append(archive_url)
        return httpx.Response(200, text="access_url\n" + "\n".join(urls))

    with httpx.Client(transport=httpx.MockTransport(sia)) as client:
        if include_tile:
            assert resolve_tile(client, position) == (tile_index, archive_url)
        else:
            with pytest.raises(CubeCoverageError):
                resolve_tile(client, position)
