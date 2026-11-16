import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const source = await readFile(new URL('../src/services/api.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2022 } }).outputText;
const api = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);

function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}
const ok = value => ({ ok: true, json: async () => value });

// A foreground frame request shares an already-started prefetch.
api.clearFrameCache();
let requests = 0;
const first = deferred();
globalThis.fetch = () => { requests++; return first.promise; };
api.prefetchFrame('a');
const foreground = api.fetchFrame('a');
assert.equal(requests, 1);
first.resolve(ok({ frame_id: 'a' }));
assert.equal((await foreground).frame_id, 'a');
assert.equal((await api.fetchFrame('a')).frame_id, 'a');
assert.equal(requests, 1);

// A previous search's delayed response cannot overwrite a new request or cache.
api.clearFrameCache();
const stale = deferred(), current = deferred();
requests = 0;
globalThis.fetch = () => (++requests === 1 ? stale.promise : current.promise);
const staleResult = api.fetchFrame('same');
api.clearFrameCache();
const currentResult = api.fetchFrame('same');
stale.resolve(ok({ frame_id: 'old' }));
assert.equal((await staleResult).frame_id, 'old');
const sharedCurrent = api.fetchFrame('same');
assert.equal(requests, 2);
current.resolve(ok({ frame_id: 'new' }));
assert.equal((await currentResult).frame_id, 'new');
assert.equal((await sharedCurrent).frame_id, 'new');
assert.equal((await api.fetchFrame('same')).frame_id, 'new');

// Failed requests do not poison the cache and can be retried.
api.clearFrameCache();
requests = 0;
globalThis.fetch = async () => ++requests === 1
  ? { ok: false, json: async () => ({ detail: 'Archive unavailable' }) }
  : ok({ frame_id: 'recovered' });
await assert.rejects(api.fetchFrame('retry'), /Archive unavailable/);
assert.equal((await api.fetchFrame('retry')).frame_id, 'recovered');
assert.equal(requests, 2);
console.log('PASS: frame request deduplication, stale-search isolation, and retry');
