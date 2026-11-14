import pytest
from app.science.coordinates import parse_coordinates, format_sexagesimal

def test_parse_decimal_coordinates():
    ra, dec = parse_coordinates(133.795129, -7.245147)
    assert pytest.approx(ra, 0.0001) == 133.795129
    assert pytest.approx(dec, 0.0001) == -7.245147

def test_parse_string_decimal():
    ra, dec = parse_coordinates("269.45208", "4.69339")
    assert pytest.approx(ra, 0.0001) == 269.45208
    assert pytest.approx(dec, 0.0001) == 4.69339

def test_parse_sexagesimal_hms():
    # WISE 0855: 08h55m10.831s, -07d14m42.53s
    ra, dec = parse_coordinates("08h55m10.831s", "-07d14m42.53s")
    assert pytest.approx(ra, 0.001) == 133.7951
    assert pytest.approx(dec, 0.001) == -7.2451

def test_parse_sexagesimal_colon_format():
    ra, dec = parse_coordinates("08:55:10.831", "-07:14:42.53")
    assert pytest.approx(ra, 0.001) == 133.7951
    assert pytest.approx(dec, 0.001) == -7.2451

def test_parse_sexagesimal_space_format():
    ra, dec = parse_coordinates("12 30 00", "-07 14 42")
    assert pytest.approx(ra, 0.001) == 187.5
    assert pytest.approx(dec, 0.001) == -7.245

def test_parse_challenge_prompt_unicode_coordinates():
    ra, dec = parse_coordinates("08h55m10.831s", "-07°14′42.53″")
    assert pytest.approx(ra, 0.001) == 133.7951
    assert pytest.approx(dec, 0.001) == -7.2451

def test_empty_coordinate_input():
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_coordinates("", "")

def test_ra_wrapping():
    ra, dec = parse_coordinates(370.0, 10.0)
    assert pytest.approx(ra, 0.0001) == 10.0
    assert dec == 10.0

def test_dec_out_of_range():
    with pytest.raises(ValueError):
        parse_coordinates(120.0, 95.0)
    with pytest.raises(ValueError):
        parse_coordinates(120.0, -95.0)

def test_invalid_input():
    with pytest.raises(ValueError):
        parse_coordinates("invalid_ra", "invalid_dec")

def test_format_sexagesimal():
    formatted = format_sexagesimal(133.795129, -7.245147)
    assert "08h55m" in formatted
    assert "-07d14m" in formatted
