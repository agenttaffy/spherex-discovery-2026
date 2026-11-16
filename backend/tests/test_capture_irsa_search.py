import importlib.util
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('capture_irsa_search', ROOT / 'scripts/capture_irsa_search.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

URL = 'https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W19_1B/l2b-v27-2026-197/3/level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits'
HEADER = 'obs_id,energy_bandpassname,t_min,access_url\n'
CSV = (HEADER + f'2025W19_1B_0116_1,SPHEREx-D3,60800.700028,{URL}\n').encode()

class Response:
    status = 200
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, limit): return self.body[:limit]
    def geturl(self): return module.ENDPOINT

def test_capture_verified_row_and_explicit_bounded_query():
    calls = []
    def opener(request, timeout):
        calls.append((request.full_url, timeout))
        return Response(CSV)
    request, rows = module.capture(248.16723, 66.75502, .001, 'spherex_dr1', 10, opener)
    assert len(rows) == 1
    assert calls == [(request, 20)]
    assert parse_qs(urlparse(request).query)['MAXREC'] == ['10']
    assert parse_qs(urlparse(request).query)['POS'] == ['circle 248.16723000 66.75502000 0.001000']


def test_deep_capture_keeps_collection_but_validates_release_path():
    request, rows = module.capture(248.16723, 66.75502, .001, 'spherex_dr1_deep', 10,
                                   lambda *a, **k: Response(CSV))
    assert parse_qs(urlparse(request).query)['COLLECTION'] == ['spherex_dr1_deep']
    assert rows[0]['access_url'] == URL
    with pytest.raises(ValueError, match='does not match collection'):
        module.capture(248.16723, 66.75502, .001, 'spherex_qr3_deep', 10,
                       lambda *a, **k: Response(CSV))

@pytest.mark.parametrize('body', [b'<html>unavailable</html>', CSV.replace(b'60800.700028', b'NaN'), CSV.replace(b'SPHEREx-D3', b'SPHEREx-D4'), b'x' * (module.MAX_BYTES + 1)])
def test_bad_responses_are_rejected(body):
    with pytest.raises(ValueError):
        module.capture(1, 2, .001, 'spherex_dr1', 10, lambda *a, **k: Response(body))

def test_empty_is_distinct_and_creates_no_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(module, 'capture', lambda *a: ('https://irsa.ipac.caltech.edu/SIA?x', []))
    out = tmp_path / 'capture.json'
    assert module.main([str(out), '--preset', 'epsilon_indi_b', '--collection', 'spherex_dr1']) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'empty'
    assert not out.exists()

def test_success_is_importable_and_existing_file_untouched(tmp_path, monkeypatch, capsys):
    req, rows = module.capture(248.16723, 66.75502, .001, 'spherex_dr1', 10, lambda *a, **k: Response(CSV))
    monkeypatch.setattr(module, 'capture', lambda *a: (req, rows))
    out = tmp_path / 'capture.json'
    args = [str(out), '--preset', 'r_draconis', '--collection', 'spherex_dr1']
    assert module.main(args) == 0
    job = json.loads(out.read_text(encoding='utf-8'))[0]
    assert job['request'] == req and job['rows'] == rows and job['acquired_utc'].endswith('+00:00')
    previous = out.read_bytes()
    assert module.main(args) == 1
    assert out.read_bytes() == previous
    assert json.loads(capsys.readouterr().err)['status'] == 'failure'

def test_network_failure_has_no_output(tmp_path, monkeypatch, capsys):
    def fail(*args): raise OSError('archive unavailable')
    monkeypatch.setattr(module, 'capture', fail)
    out = tmp_path / 'capture.json'
    assert module.main([str(out), '--ra', '1', '--dec', '2', '--collection', 'spherex_dr1']) == 1
    assert json.loads(capsys.readouterr().err)['status'] == 'failure'
    assert not out.exists()
