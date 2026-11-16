import { useEffect, useState } from 'react';
import type { CubeChannel } from './cubeCsv';
import { measuredSkyPixels } from './quickSpectrumModel';

type Preview = {
  source: string;
  tile: number;
  pixel: { ra: number; dec: number };
  preview?: { generated_on?: string };
  channels: CubeChannel[];
};
type State = { key: string; preview?: Preview; error?: string } | null;

/** Lightweight inspector view. It never launches an archive or cloud tile download. */
export function QuickSkySpectrum({ position, enabled, onOpenCube }: {
  position: { ra: number; dec: number } | null;
  enabled: boolean;
  onOpenCube: () => void;
}) {
  const key = position ? `${position.ra},${position.dec}` : '';
  const [state, setState] = useState<State>(null);

  useEffect(() => {
    if (!position || !enabled) return;
    const controller = new AbortController();
    setState(null);
    const params = new URLSearchParams({ ra: String(position.ra), dec: String(position.dec), source: 'preview_only' });
    void fetch(`/api/cube/spectrum?${params}`, { signal: controller.signal })
      .then(async response => {
        if (response.status === 404) throw new Error('No cached sky-pixel preview is stored for these coordinates.');
        if (!response.ok) throw new Error('The cached sky-pixel preview could not be loaded.');
        const result: Preview = await response.json();
        if (result.source !== 'cached_dr1_preview' || !Array.isArray(result.channels) || result.channels.length !== 102
            || !result.channels.every(point => point && typeof point === 'object') || !Number.isFinite(result.tile)
            || !Number.isFinite(result.pixel?.ra) || !Number.isFinite(result.pixel?.dec)) {
          throw new Error('The cached sky-pixel preview has incomplete metadata.');
        }
        if (!controller.signal.aborted) setState({ key, preview: result });
      })
      .catch((problem: unknown) => {
        if (!controller.signal.aborted) setState({ key, error: problem instanceof Error ? problem.message : 'The cached sky-pixel preview could not be loaded.' });
      });
    return () => controller.abort();
  }, [key, enabled]);

  const preview = state?.key === key ? state.preview : undefined;
  const points = preview ? measuredSkyPixels(preview.channels) : [];
  const values = points.map(point => point.surface_brightness_mjy_sr as number);
  const minimum = values.length ? Math.min(...values) : 0;
  const maximum = values.length ? Math.max(...values) : 0;
  const wavelengths = points.map(point => point.wavelength_um as number);
  const minWave = Math.min(0.75, ...wavelengths), maxWave = Math.max(5.0, ...wavelengths);
  const padding = maximum === minimum ? Math.max(Math.abs(maximum) * 0.05, 1e-6) : (maximum - minimum) * 0.08;
  const lower = minimum - padding, upper = maximum + padding;
  const x = (wave: number) => 32 + (wave - minWave) / (maxWave - minWave) * 228;
  const y = (value: number) => 95 - (value - lower) / (upper - lower) * 75;

  return <section className="rounded-lg border border-slate-700 bg-slate-950/90 p-3 space-y-2" aria-label="Cached sky-pixel spectrum">
    <div>
      <h3 className="text-xs font-semibold text-slate-100">DR1 sky-pixel spectrum</h3>
      <p className="text-[11px] text-slate-300">Co-added across dates; this is a sky pixel, not confirmed target photometry or a single observation.</p>
    </div>
    {!position ? <p className="text-xs text-slate-400">Search coordinates to inspect a cached sample.</p>
      : !enabled ? <p className="text-xs text-slate-400">Open analysis to load a cached sample.</p>
      : state?.key !== key ? <p role="status" className="text-xs text-slate-300">Loading cached sample…</p>
      : state.error ? <p role="status" className="text-xs text-amber-200">{state.error} Use 102 Bands to check the archive.</p>
      : preview && points.length === 0 ? <p role="status" className="text-xs text-amber-200">The cached sky-pixel preview has no usable channels at this position. Use 102 Bands to check the archive.</p>
      : preview && <>
        <p className="text-[11px] text-slate-300">{points.length} of 102 channel slots usable · {102 - points.length} gaps or flagged</p>
        <svg viewBox="0 0 280 125" className="block w-full" role="img" aria-label={`Cached sky-pixel spectrum with ${points.length} measured channels. Horizontal axis is wavelength in micrometers; vertical axis is surface brightness in megajanskys per steradian. Missing channels have no points.`}>
          <text x="32" y="11" fill="#94a3b8" fontSize="8">Surface brightness (MJy/sr)</text>
          <line x1="32" y1="20" x2="32" y2="95" stroke="#64748b" />
          <line x1="32" y1="95" x2="260" y2="95" stroke="#64748b" />
          <text x="29" y="23" textAnchor="end" fill="#94a3b8" fontSize="8">{upper.toPrecision(3)}</text>
          <text x="29" y="95" textAnchor="end" fill="#94a3b8" fontSize="8">{lower.toPrecision(3)}</text>
          <text x="32" y="109" fill="#94a3b8" fontSize="8">{minWave.toFixed(2)}</text>
          <text x="260" y="109" textAnchor="end" fill="#94a3b8" fontSize="8">{maxWave.toFixed(2)} µm</text>
          {points.map(point => <circle key={point.channel} cx={x(point.wavelength_um as number)} cy={y(point.surface_brightness_mjy_sr as number)} r="2" fill="#67e8f9" />)}
          <text x="146" y="122" textAnchor="middle" fill="#94a3b8" fontSize="8">Wavelength (µm)</text>
        </svg>
        <p className="text-[10px] text-slate-400">Cached DR1 sample{preview.preview?.generated_on ? ` · saved ${preview.preview.generated_on}` : ''} · HPX tile {preview.tile}. No variance plane is available.</p>
      </>}
    <button type="button" onClick={onOpenCube} className="rounded border border-cyan-700 px-2 py-1 text-xs text-cyan-200 hover:bg-cyan-950">Open 102 Bands</button>
  </section>;
}
