import type { CubeData } from './cubeCsv';

export type SkyPosition = { ra: number; dec: number };
type CubeQuery = { ra: string; dec: string; channel: number };

/** Auto-load only an explicit cube link with valid decimal-degree coordinates. */
export function parseCubeDeepLink(params: URLSearchParams): SkyPosition | null {
  if (params.get('tab') !== 'cube') return null;
  const rawRa = params.get('ra'), rawDec = params.get('dec');
  if (!rawRa?.trim() || !rawDec?.trim()) return null;
  const ra = Number(rawRa), dec = Number(rawDec);
  if (!Number.isFinite(ra) || !Number.isFinite(dec) || ra < 0 || ra >= 360 || dec < -90 || dec > 90) return null;
  return { ra, dec };
}

/** The last successfully returned spectrum shown for the currently applied query. */
export function displayedCubePosition(data: CubeData | null, query: CubeQuery | null): SkyPosition | null {
  if (!data || !query || !data.channel_map || !Array.isArray(data.channels)
      || !Number.isFinite(data.ra) || !Number.isFinite(data.dec)
      || data.ra !== Number(query.ra) || data.dec !== Number(query.dec)
      || !data.channels.some(point => point.channel === query.channel)) return null;
  return { ra: data.ra, dec: data.dec };
}

/** A cube sample is not a dated exposure; remove unrelated target/observation IDs. */
export function applyCubeSharePosition(url: URL, position: SkyPosition | null): void {
  if (!position) return;
  url.searchParams.set('ra', String(position.ra));
  url.searchParams.set('dec', String(position.dec));
  url.searchParams.delete('target');
  url.searchParams.delete('obs');
  url.searchParams.delete('obs_detector');
}
