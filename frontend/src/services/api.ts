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
} from '../types/astronomy';

const API_BASE = '/api';

const frameCache = new Map<string, FrameResponse>();

export async function checkHealth(): Promise<{ status: string; irsa_connected: boolean; cached_frames: number }> {
  const resp = await fetch(`${API_BASE}/health`);
  if (!resp.ok) throw new Error('Health check failed');
  return resp.json();
}

export async function fetchObservations(
  ra: number | string,
  dec: number | string,
  fov: number = 0.05,
  collection: string = 'spherex_dr1',
  detector?: string,
  limit: number = 60
): Promise<{ observations: ObservationRecord[]; total_found: number }> {
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
  if (frameCache.has(cacheKey)) {
    return frameCache.get(cacheKey)!;
  }
  const resp = await fetch(
    `${API_BASE}/frames/${encodeURIComponent(frameId)}?stretch=${stretch}&fov=${fov}&format=${format}`
  );
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Failed to fetch frame' }));
    throw new Error(err.detail || 'Failed to fetch frame');
  }
  const data: FrameResponse = await resp.json();
  frameCache.set(cacheKey, data);
  return data;
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

export async function computeDiff(
  frameId1: string,
  frameId2: string,
  format: string = 'webp'
): Promise<DiffResult> {
  const resp = await fetch(`${API_BASE}/frames/diff`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ frame_id_1: frameId1, frame_id_2: frameId2, format }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Failed to compute diff' }));
    throw new Error(err.detail || 'Failed to compute diff');
  }
  return resp.json();
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
    return { total_sources: 0, sources: [] };
  }
  return resp.json();
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
  stretch: string = 'asinh'
): Promise<StackResult> {
  const resp = await fetch(`${API_BASE}/frames/stack`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      frame_ids: frameIds,
      method,
      format,
      stretch,
    }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Failed to stack frames' }));
    throw new Error(err.detail || 'Failed to stack frames');
  }
  return resp.json();
}
