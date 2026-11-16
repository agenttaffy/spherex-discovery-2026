import { useEffect, useState } from 'react';
import type { CubeData } from './cubeCsv';

type ViewState =
  | { key: string; phase: 'loading' }
  | { key: string; phase: 'error'; message: string }
  | { key: string; phase: 'ready'; data: CubeData };

function validMap(data: CubeData, ra: number, dec: number, channel: number): boolean {
  const map = data.channel_map;
  return (data.source === 'cloud_dr1_pinned' || data.source === 'cached_dr1_preview')
    && data.ra === ra && data.dec === dec && Array.isArray(data.channels)
    && !!map && map.channel === channel && Array.isArray(map.pixels)
    && map.pixels.length > 0 && map.pixels.length <= 25
    && Array.isArray(map.pixels[0]) && map.pixels[0].length > 0 && map.pixels[0].length <= 25
    && map.pixels.every(row => Array.isArray(row) && row.length === map.pixels[0].length
      && row.every(value => value === null || (typeof value === 'number' && Number.isFinite(value))))
    && Number.isInteger(map.center_x) && Number.isInteger(map.center_y)
    && map.center_x >= 0 && map.center_x < map.pixels[0].length
    && map.center_y >= 0 && map.center_y < map.pixels.length;
}

/** A small native DR1 cube tile window; this is not a dated exposure. */
export function ExplorerCubePreview({ ra, dec, onOpenCube, onCubeLoaded }: {
  ra: number;
  dec: number;
  onOpenCube: () => void;
  onCubeLoaded: (cube: CubeData) => void;
}) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<ViewState>({ key: '', phase: 'loading' });
  const key = `${ra},${dec}`;

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    let timedOut = false;
    setState({ key, phase: 'loading' });
    const timeout = window.setTimeout(() => { timedOut = true; controller.abort(); }, 45000);
    async function read(channel: number): Promise<CubeData> {
      const params = new URLSearchParams({ ra: String(ra), dec: String(dec), channel: String(channel), source: 'pinned_cloud' });
      const response = await fetch(`/api/cube/spectrum?${params}`, { signal: controller.signal });
      if (!response.ok) throw new Error('The DR1 sky-pixel preview could not be loaded.');
      const result: CubeData = await response.json();
      if (!validMap(result, ra, dec, channel)) throw new Error('The sky-pixel preview returned incomplete or mismatched data.');
      return result;
    }
    async function load() {
      try {
        let data = await read(1);
        // If the first map is completely masked, make at most one additional
        // request for a genuinely measured channel at the same sky position.
        if (!data.channel_map.pixels.some(row => row.some(value => value !== null))) {
          const alternate = data.channels.find(point => point.channel !== 1 && point.status === 'measured'
            && point.surface_brightness_mjy_sr != null && Number.isFinite(point.surface_brightness_mjy_sr));
          if (alternate) data = await read(alternate.channel);
        }
        if (active && !controller.signal.aborted) {
          setState({ key, phase: 'ready', data });
          onCubeLoaded(data);
        }
      } catch (error) {
        if (active && (!controller.signal.aborted || timedOut)) setState({ key, phase: 'error',
          message: timedOut ? 'The sky-pixel preview timed out.' : error instanceof Error ? error.message : 'The sky-pixel preview could not be loaded.' });
      } finally {
        window.clearTimeout(timeout);
      }
    }
    if (Number.isFinite(ra) && ra >= 0 && ra < 360 && Number.isFinite(dec) && dec >= -90 && dec <= 90) void load();
    else { window.clearTimeout(timeout); setState({ key, phase: 'error', message: 'Enter valid sky coordinates to load a preview.' }); }
    return () => { active = false; window.clearTimeout(timeout); controller.abort(); };
  }, [ra, dec, attempt, onCubeLoaded]);

  const current = state.key === key ? state : { key, phase: 'loading' as const };
  const data = current.phase === 'ready' ? current.data : null;
  const map = data?.channel_map;
  const points = map?.pixels.flat().filter((value): value is number => value !== null) ?? [];
  const low = points.length ? Math.min(...points) : 0;
  const high = points.length ? Math.max(...points) : 0;
  const channel = data?.channels.find(point => point.channel === map?.channel);

  return <section className="flex flex-1 flex-col items-center justify-center gap-3 p-4 text-center overflow-y-auto" aria-label="DR1 sky-pixel context preview">
    <div className="max-w-prose space-y-1">
      <h3 className="text-sm font-semibold text-slate-100">DR1 sky-pixel context</h3>
      <p className="text-xs text-slate-300">A fixed window from the DR1 mosaic, combining multiple dates in one infrared channel. Playback requires dated exposures.</p>
    </div>
    {current.phase === 'loading' && <p role="status" className="text-sm text-slate-300">Loading the DR1 cloud sky-pixel preview…</p>}
    {current.phase === 'error' && <div role="alert" className="space-y-2 text-sm text-amber-200">
      <p>{current.message}</p>
      <button type="button" onClick={() => setAttempt(value => value + 1)} className="rounded border border-cyan-600 px-3 py-1 text-cyan-100">Retry preview</button>
    </div>}
    {data && map && (points.length ? <>
      <svg className="w-full max-w-[min(24rem,48vh)] shrink-0 bg-black border border-slate-700" shapeRendering="crispEdges"
        role="img" aria-label={`DR1 co-added sky-pixel context, channel ${map.channel}. Cyan outline marks the sampled pixel; missing and flagged pixels are black.`}
        viewBox={`0 0 ${map.pixels[0].length} ${map.pixels.length}`}>
        {map.pixels.map((row, y) => row.map((value, x) => {
          if (value === null) return null;
          const gray = Math.round(35 + 220 * (value - low) / (high - low || 1));
          return <rect key={`${x},${y}`} x={x} y={map.pixels.length - 1 - y} width="1" height="1" fill={`rgb(${gray},${gray},${gray})`} />;
        }))}
        <rect x={map.center_x} y={map.pixels.length - 1 - map.center_y} width="1" height="1" fill="none" stroke="#67e8f9" strokeWidth="0.14" />
      </svg>
      <p className="text-xs text-slate-300">Channel {map.channel}{channel?.wavelength_um != null ? ` · ${channel.wavelength_um.toFixed(3)} µm` : ''} · tile {data.tile} · display range {low.toPrecision(4)}–{high.toPrecision(4)} MJy/sr</p>
    </> : <p role="status" className="text-sm text-amber-200">No usable pixels were returned in this channel window.</p>)}
    {data && <p className="text-xs text-slate-400">{data.source === 'cached_dr1_preview' ? 'Cached DR1 preview; cloud read unavailable.' : `Public cloud DR1 cube${data.cloud?.pinned_version ? ` · ${data.cloud.pinned_version}` : ''}; it may not be the newest release.`} Masked pixels are blank; grayscale is a display stretch only.</p>}
    <button type="button" onClick={onOpenCube} className="rounded border border-cyan-600 px-3 py-1.5 text-xs font-semibold text-cyan-100 hover:bg-cyan-950">Explore 102 Bands</button>
  </section>;
}
