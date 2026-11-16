import {
  ObservationRecord,
  FrameResponse,
  DemoPreset,
  DiffResult,
  CatalogSource,
  LightCurveSeries,
  AstrometricMotion,
  DiscoveryReport,
  SpectrumResponse,
  StackResult,
  CompatiblePartners,
} from '../types/astronomy';

const API_BASE = '/api';

const frameCache = new Map<string, FrameResponse>();
const frameRequests = new Map<string, Promise<FrameResponse>>();
let frameCacheGeneration = 0;

export function clearFrameCache(): void {
  frameCacheGeneration += 1;
  frameCache.clear();
  frameRequests.clear();
}

export async function checkHealth(): Promise<{ status: string; irsa_connected: boolean; demo_cache_only?: boolean; cached_frames: number }> {
  const resp = await fetch(`${API_BASE}/health`);
  if (!resp.ok) throw new Error('Health check failed');
  return resp.json();
}

export type ArchiveSearchStatus = 'available' | 'partial' | 'unavailable' | 'not_checked' | 'unknown';

export async function fetchObservations(
  ra: number | string,
  dec: number | string,
  fov: number = 0.05,
  collection: string = 'spherex_dr1',
  detector?: string,
  limit: number = 60
): Promise<{ target: {ra: number; dec: number; fov: number}; observations: ObservationRecord[]; total_found: number; archive_search_status?: ArchiveSearchStatus }> {
  const params = new URLSearchParams({
    ra: String(ra),
    dec: String(dec),
    fov: String(fov),
    collection,
    limit: String(limit),
  });
  if (detector && detector !== 'ALL') {
    params.set('detector', detector);
  }

  const resp = await fetch(`${API_BASE}/observations?${params.toString()}`);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Failed to fetch observations' }));
    throw new Error(err.detail || 'Failed to fetch observations');
  }
  return resp.json();
}

export async function fetchFrame(
  frameId: string,
  stretch: string = 'asinh',
  fov: number = 0.05,
  format: string = 'webp'
): Promise<FrameResponse> {
  const cacheKey = `${frameId}_${stretch}_${fov}_${format}`;
  const generation = frameCacheGeneration;
  if (frameCache.has(cacheKey)) {
    return frameCache.get(cacheKey)!;
  }
  const existing = frameRequests.get(cacheKey);
  if (existing) return existing;
  const request = (async () => {
    const resp = await fetch(
      `${API_BASE}/frames/${encodeURIComponent(frameId)}?stretch=${stretch}&fov=${fov}&format=${format}`
    );
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Failed to fetch frame' }));
      throw new Error(err.detail || 'Failed to fetch frame');
    }
    const data: FrameResponse = await resp.json();
    if (generation === frameCacheGeneration) frameCache.set(cacheKey, data);
    return data;
  })();
  frameRequests.set(cacheKey, request);
  try {
    return await request;
  } finally {
    if (frameRequests.get(cacheKey) === request) frameRequests.delete(cacheKey);
  }
}

export function prefetchFrame(
  frameId: string,
  stretch: string = 'asinh',
  fov: number = 0.05,
  format: string = 'webp'
): void {
  const cacheKey = `${frameId}_${stretch}_${fov}_${format}`;
  if (!frameCache.has(cacheKey)) {
    fetchFrame(frameId, stretch, fov, format).catch(() => {});
  }
}

export async function fetchDemoPresets(): Promise<DemoPreset[]> {
  const resp = await fetch(`${API_BASE}/demo`);
  if (!resp.ok) throw new Error('Failed to load demo presets');
  return resp.json();
}

export async function fetchDemoComparison(signal: AbortSignal): Promise<ObservationRecord[]> {
  const resp = await fetch(`${API_BASE}/demo/comparison`, { signal });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || 'Eligible D5 pair unavailable in the local cache.');
  }
  return resp.json();
}

export async function computeDiff(
  frameId1: string,
  frameId2: string,
  format: string = 'webp',
  fov: number = 0.04,
): Promise<DiffResult> {
  const resp = await fetch(`${API_BASE}/frames/diff`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ frame_id_1: frameId1, frame_id_2: frameId2, format, fov }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Failed to compute diff' }));
    throw new Error(err.detail || 'Failed to compute diff');
  }
  return resp.json();
}

/** Bounded cache-only search; a match is revalidated by the normal comparison. */
export async function findCompatiblePartners(frameId: string, candidates: string[], fov: number, signal: AbortSignal): Promise<CompatiblePartners> {
  const response = await fetch(`${API_BASE}/frames/compatible-partners`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, signal,
    body: JSON.stringify({ frame_id: frameId, candidate_ids: candidates, fov }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : 'Could not check cached comparison partners.');
  }
  return response.json();
}

export async function fetchCatalogs(
  ra: number | string,
  dec: number | string,
  radius: number = 0.08,
  catalog: string = 'gaia_dr3'
): Promise<{ total_sources: number; sources: CatalogSource[] }> {
  const params = new URLSearchParams({
    ra: String(ra),
    dec: String(dec),
    radius: String(radius),
    catalog,
  });
  const resp = await fetch(`${API_BASE}/science/catalogs?${params.toString()}`);
  if (!resp.ok) {
    throw new Error('Reference catalog request failed');
  }
  return resp.json();
}

export async function projectCatalog(frameId: string, fov: number, sources: CatalogSource[]): Promise<({x: number; y: number; motion_applied: boolean} | null)[]> {
  const response = await fetch(`${API_BASE}/frames/project-catalog`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ frame_id: frameId, fov, coordinates: sources.map(source => [source.ra, source.dec]), proper_motions: sources.map(source => [source.pm_ra, source.pm_dec]) }),
  });
  if (!response.ok) throw new Error('Catalog positions could not be projected onto this image.');
  return (await response.json()).positions;
}

export async function fetchPhotometry(
  ra: number | string,
  dec: number | string,
  collection: string = 'spherex_dr1',
  detector?: string,
  fov: number = 0.04
): Promise<LightCurveSeries> {
  const params = new URLSearchParams({
    ra: String(ra),
    dec: String(dec),
    collection,
    fov: String(fov),
  });
  if (detector && detector !== 'ALL') {
    params.set('detector', detector);
  }
  const resp = await fetch(`${API_BASE}/science/photometry?${params.toString()}`);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Failed to load photometry' }));
    throw new Error(err.detail || 'Failed to load photometry');
  }
  return resp.json();
}

export async function computeMotion(
  frameId1: string,
  frameId2: string,
  pixelScale: number = 6.2
): Promise<{ eligible: boolean; motion: AstrometricMotion }> {
  const resp = await fetch(`${API_BASE}/science/motion`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ frame_id_1: frameId1, frame_id_2: frameId2, pixel_scale_arcsec: pixelScale }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Motion calculation failed' }));
    throw new Error(err.detail || 'Motion calculation failed');
  }
  return resp.json();
}

export async function generateDiscoveryReport(data: {
  target_name: string;
  ra: number;
  dec: number;
  target_type?: string;
  motion_data?: any;
  photometry_data?: any;
  observations?: any[];
  notes?: string;
  spectrum_data?: any;
}): Promise<DiscoveryReport> {
  const resp = await fetch(`${API_BASE}/science/report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!resp.ok) {
    throw new Error('Failed to generate discovery report');
  }
  return resp.json();
}

export async function fetchSpectrum(
  ra: number | string,
  dec: number | string,
  collection?: string,
  fov: number = 0.04
): Promise<SpectrumResponse> {
  const params = new URLSearchParams({
    ra: String(ra),
    dec: String(dec),
    fov: String(fov),
  });
  if (collection && collection !== 'ALL') {
    params.set('collection', collection);
  }
  const resp = await fetch(`${API_BASE}/science/spectrum?${params.toString()}`);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Failed to load spectrum' }));
    throw new Error(err.detail || 'Failed to load spectrum');
  }
  return resp.json();
}

export async function stackFrames(
  frameIds: string[],
  method: 'mean' | 'median' | 'sum' = 'mean',
  format: string = 'png',
  stretch: string = 'asinh',
  fov: number = 0.04,
): Promise<StackResult> {
  const resp = await fetch(`${API_BASE}/frames/stack`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      frame_ids: frameIds,
      method,
      format,
      stretch,
      fov,
    }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Failed to stack frames' }));
    throw new Error(err.detail || 'Failed to stack frames');
  }
  return resp.json();
}
