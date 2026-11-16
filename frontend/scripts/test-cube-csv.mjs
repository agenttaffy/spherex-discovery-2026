import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { gunzipSync } from 'node:zlib';
import ts from 'typescript';

const source = await readFile(new URL('../src/components/science/cubeCsv.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2022 } }).outputText;
const { cubeSpectrumCsv } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
const preview = JSON.parse(gunzipSync(await readFile(new URL('../../data/manifests/cube_preview.json.gz', import.meta.url))));
const sample = preview.samples.epsilon_indi_b;
const input = { ...sample, source: 'cached_dr1_preview', fits_url: 'https://example.test/tile,"quoted"',
  preview: { generated_on: preview.generated_on, provenance: { etag_md5: 'abc', sha256: null } } };
input.channels[1] = { ...input.channels[1], status: 'flagged', flags: 2,
  surface_brightness_mjy_sr: null, archive_brightness_mjy_sr: 42.5 };

// Parse CSV quoting, including commas and double quotes in a field.
function parseLine(line) {
  const result = [];
  let value = '', quoted = false;
  for (let i = 0; i < line.length; i++) {
    if (line[i] === '"' && quoted && line[i + 1] === '"') { value += '"'; i++; }
    else if (line[i] === '"') quoted = !quoted;
    else if (line[i] === ',' && !quoted) { result.push(value); value = ''; }
    else value += line[i];
  }
  assert.equal(quoted, false);
  return [...result, value];
}
const rows = cubeSpectrumCsv(input).split('\r\n').map(parseLine);
const headers = rows.shift();
const records = rows.map(row => Object.fromEntries(headers.map((key, i) => [key, row[i]])));
assert.equal(records.length, 102);
assert.equal(records[0].detector, '1');
assert.equal(records[50].detector, '3');
assert.equal(records[50].detector_channel, '17');
assert.equal(records[50].status, 'blank_channel');
assert.equal(records[50].surface_brightness_mjy_sr, '');
assert.equal(records[1].status, 'flagged');
assert.equal(records[1].surface_brightness_mjy_sr, '');
assert.equal(records[1].archive_brightness_unfiltered_mjy_sr, '42.5');
assert.equal(records[0].sample_kind, 'coadded_sky_pixel_not_target_photometry');
assert.equal(records[0].fits_url, input.fits_url);
console.log('PASS: 102 cached sky-pixel slots, provenance, quality gaps, and CSV quoting');
