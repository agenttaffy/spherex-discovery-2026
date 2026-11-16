import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { gunzipSync } from 'node:zlib';
import ts from 'typescript';

const source = await readFile(new URL('../src/components/science/bandNavigation.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2022 } }).outputText;
const { detectorChannels, firstUsefulChannel, nextMeasuredChannel } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
const preview = JSON.parse(gunzipSync(await readFile(new URL('../../data/manifests/cube_preview.json.gz', import.meta.url))));
const epsilon = preview.samples.epsilon_indi_b.channels;
for (let detector = 1; detector <= 6; detector++) {
  const group = detectorChannels(epsilon, detector);
  assert.equal(group.length, 17);
  assert.equal(group[0].detector, detector);
  assert.equal(group[0].subchannel, 1);
  assert.equal(group[16].subchannel, 17);
  assert.equal(epsilon[firstUsefulChannel(epsilon, detector) - 1].status, 'measured');
}
const rDra = preview.samples.r_draconis.channels;
assert.equal(rDra.filter(row => row.status === 'measured').length, 0);
assert.equal(firstUsefulChannel(rDra, 3), 35);
assert.equal(firstUsefulChannel([], 1), null);
assert.equal(nextMeasuredChannel(epsilon, 50), 35); // skips blank channel 51 and loops within D3
assert.equal(nextMeasuredChannel(epsilon, 51), 35); // starting on a blank chooses the first measured
assert.equal(nextMeasuredChannel(rDra, 35), null);
console.log('PASS: six detector groups, 17 channels each, measured and unavailable selection');
