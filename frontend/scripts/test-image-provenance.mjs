import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const source = await readFile(new URL('../src/services/imageProvenance.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2022 } }).outputText;
const { imageProvenanceLabel } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
assert.equal(imageProvenanceLabel('live_cloud_cutout'), 'IRSA public AWS cloud image cutout');
assert.equal(imageProvenanceLabel('cached_cloud_cutout'), 'cached IRSA AWS cloud image cutout');
assert.equal(imageProvenanceLabel('cached_demo_cutout'), 'cached demonstration cutout');
assert.equal(imageProvenanceLabel('unexpected_new_source'), 'unknown');
assert.equal(imageProvenanceLabel(undefined), 'unknown');
console.log('PASS: live and cached cloud provenance remains distinct');
