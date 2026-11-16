import type { CubeData } from './cubeCsv';

export type SkyPosition = { ra: number; dec: number };
type CubeQuery = { ra: string; dec: string; channel: number };

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
