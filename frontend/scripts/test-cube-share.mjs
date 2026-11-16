import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const source = await readFile(new URL('../src/components/science/cubeShare.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2022 } }).outputText;
const { displayedCubePosition, applyCubeSharePosition, parseCubeDeepLink } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);

const oldData = { ra: 331.09813086506205, dec: -56.801144263858404,
  channels: [{ channel: 1 }, { channel: 2 }], channel_map: { channel: 1 } };
const loaded = { ra: String(oldData.ra), dec: String(oldData.dec), channel: 1 };
assert.deepEqual(displayedCubePosition(oldData, loaded), { ra: oldData.ra, dec: oldData.dec });
// Editing input does not alter the applied query or a currently displayed sample.
assert.deepEqual(displayedCubePosition(oldData, loaded), { ra: oldData.ra, dec: oldData.dec });
// A newly submitted/failed different position must never share the old data as if it were new.
assert.equal(displayedCubePosition(oldData, { ra: '1', dec: '2', channel: 1 }), null);
assert.equal(displayedCubePosition(null, { ra: '1', dec: '2', channel: 1 }), null);
assert.equal(displayedCubePosition({ ...oldData, channel_map: null }, loaded), null);
// A loading channel map at the same position may retain the displayed spectrum.
assert.deepEqual(displayedCubePosition(oldData, { ...loaded, channel: 2 }), { ra: oldData.ra, dec: oldData.dec });

const url = new URL('https://example.test/?tab=cube&embed=1&ra=1&dec=2&target=wrong&obs=old&obs_detector=D1&fov=0.04');
applyCubeSharePosition(url, displayedCubePosition(oldData, loaded));
assert.equal(url.searchParams.get('ra'), String(oldData.ra));
assert.equal(url.searchParams.get('dec'), String(oldData.dec));
assert.equal(url.searchParams.get('target'), null);
assert.equal(url.searchParams.get('obs'), null);
assert.equal(url.searchParams.get('obs_detector'), null);
assert.equal(url.searchParams.get('embed'), '1');
assert.equal(url.searchParams.get('fov'), '0.04');
assert.deepEqual(parseCubeDeepLink(url.searchParams), { ra: oldData.ra, dec: oldData.dec });
assert.equal(parseCubeDeepLink(new URLSearchParams('tab=explorer&ra=1&dec=2')), null);
assert.equal(parseCubeDeepLink(new URLSearchParams('tab=cube&ra=360&dec=2')), null);
assert.equal(parseCubeDeepLink(new URLSearchParams('tab=cube&ra=1&dec=-91')), null);
assert.equal(parseCubeDeepLink(new URLSearchParams('tab=cube&ra=&dec=2')), null);
assert.equal(parseCubeDeepLink(new URLSearchParams('tab=cube&target=epsilon_indi_b')), null);
const previous = url.toString();
applyCubeSharePosition(url, null);
assert.equal(url.toString(), previous);
console.log('PASS: cube sharing uses displayed coordinates and removes unrelated exposure identifiers');
