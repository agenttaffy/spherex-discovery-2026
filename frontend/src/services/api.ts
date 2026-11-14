import { ObservationRecord, FrameResponse, DemoPreset, DiffResult } from '../types/astronomy';

const API_BASE = '/api';

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
  fov: number = 0.05
): Promise<FrameResponse> {
  const resp = await fetch(`${API_BASE}/frames/${encodeURIComponent(frameId)}?stretch=${stretch}&fov=${fov}`);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Failed to fetch frame' }));
    throw new Error(err.detail || 'Failed to fetch frame');
  }
  return resp.json();
}

export async function fetchDemoPresets(): Promise<DemoPreset[]> {
  const resp = await fetch(`${API_BASE}/demo`);
  if (!resp.ok) throw new Error('Failed to load demo presets');
  return resp.json();
}

export async function computeDiff(frameId1: string, frameId2: string): Promise<DiffResult> {
  const resp = await fetch(`${API_BASE}/frames/diff`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ frame_id_1: frameId1, frame_id_2: frameId2 }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Failed to compute diff' }));
    throw new Error(err.detail || 'Failed to compute diff');
  }
  return resp.json();
}
