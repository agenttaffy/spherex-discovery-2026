"""Capture one bounded IRSA SIA query for later review and snapshot import."""
import argparse
import csv
import io
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'scripts'))
from app.services.demo_service import OFFICIAL_PRESETS
from app.services.cloud_cutout import expected_image_identity
from refresh_search_snapshot import IMAGE_COLLECTIONS, usable_row

ENDPOINT = 'https://irsa.ipac.caltech.edu/SIA'
MAX_BYTES = 5 * 1024 * 1024
FIELDS = {'obs_id', 'energy_bandpassname', 't_min', 'access_url'}


def capture(ra, dec, radius, collection, maxrec, opener=urlopen):
    """Return validated data and original request; completeness is not established."""
    if not all(map(math.isfinite, (ra, dec, radius))) or not (0 <= ra < 360 and -90 <= dec <= 90 and 0 < radius <= 0.1):
        raise ValueError('Coordinates or radius outside supported bounds')
    if collection not in IMAGE_COLLECTIONS or not 1 <= maxrec <= 3000:
        raise ValueError('Invalid collection or row limit')
    position = f'circle {ra:.8f} {dec:.8f} {radius:.6f}'
    if float(position.split()[1]) >= 360 or not float(position.split()[-1]):
        raise ValueError('Coordinates or radius cannot be represented at the query precision')
    url = ENDPOINT + '?' + urlencode({'COLLECTION': collection, 'POS': position, 'RESPONSEFORMAT': 'CSV', 'MAXREC': maxrec})
    with opener(Request(url, headers={'User-Agent': 'SPHEREx-Discovery/1.0'}), timeout=20) as response:
        if response.status != 200:
            raise ValueError(f'Archive returned HTTP {response.status}')
        final = urlparse(response.geturl())
        if final.scheme != 'https' or final.hostname != 'irsa.ipac.caltech.edu' or final.path != '/SIA':
            raise ValueError('Archive response came from an unexpected endpoint')
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Archive response exceeded size limit')
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig', errors='strict'), newline=''))
    if not reader.fieldnames or not FIELDS.issubset(reader.fieldnames):
        raise ValueError('Archive response is not a recognizable SIA CSV')
    rows = list(reader)
    if len(rows) > maxrec:
        raise ValueError('Archive returned more rows than requested')
    release = collection.removeprefix('spherex_').removesuffix('_deep')
    for row in rows:
        if None in row or not usable_row(row):
            raise ValueError('Archive returned invalid or incomplete observation metadata')
        band = row['energy_bandpassname'].strip()
        if not band.startswith('SPHEREx-D') or band[-1:] not in '123456' or band != 'SPHEREx-D' + band[-1]:
            raise ValueError('Invalid detector identity')
        if expected_image_identity(row['access_url']) != (row['obs_id'].strip(), band[-1]):
            raise ValueError('Image URL does not match observation and detector identity')
        if not row['access_url'].startswith(f'https://irsa.ipac.caltech.edu/ibe/data/spherex/{release}/'):
            raise ValueError('Image URL does not match collection')
    return url, rows


def write_new(path, payload):
    """Install complete content atomically, refusing to overwrite existing files."""
    path = Path(path)
    if not path.parent.is_dir():
        raise ValueError('Output directory must already exist')
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as f:
            temp = Path(f.name)
            json.dump(payload, f, indent=2, allow_nan=False)
            f.write('\n')
        os.link(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New staging JSON path; existing files are never overwritten')
    parser.add_argument('--preset', choices=[p.id for p in OFFICIAL_PRESETS])
    parser.add_argument('--ra', type=float)
    parser.add_argument('--dec', type=float)
    parser.add_argument('--collection', required=True, choices=IMAGE_COLLECTIONS)
    parser.add_argument('--radius-deg', type=float, default=0.001)
    parser.add_argument('--maxrec', type=int, default=1000)
    args = parser.parse_args(argv)
    if args.preset:
        if args.ra is not None or args.dec is not None:
            parser.error('Use a preset or both coordinates, not both')
        preset = next(p for p in OFFICIAL_PRESETS if p.id == args.preset)
        ra, dec, label = preset.ra, preset.dec, preset.id
    elif args.ra is not None and args.dec is not None:
        ra, dec, label = args.ra, args.dec, 'custom'
    else:
        parser.error('Choose --preset or provide both --ra and --dec')
    try:
        if args.output.exists() or args.output.is_symlink():
            raise FileExistsError('The staging file already exists; choose a new output path')
        if not args.output.parent.is_dir():
            raise ValueError('Output directory must already exist')
        url, rows = capture(ra, dec, args.radius_deg, args.collection, args.maxrec)
        acquired = datetime.now(timezone.utc).isoformat()
        if not rows:
            print(json.dumps({'status': 'empty', 'request': url, 'acquired_utc': acquired, 'completeness': 'unknown'}))
            return 0
        write_new(args.output, [{'job': [label, args.collection], 'request': url, 'acquired_utc': acquired, 'rows': rows}])
        print(json.dumps({'status': 'data', 'rows': len(rows), 'request': url, 'acquired_utc': acquired, 'completeness': 'unknown', 'output': str(args.output)}))
        return 0
    except (OSError, ValueError, UnicodeError, csv.Error) as exc:
        print(json.dumps({'status': 'failure', 'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
