import { useEffect, useState } from 'react';
import { cubeSpectrumCsv, type CubeData } from './cubeCsv';
import { detectorChannels, firstUsefulChannel, nextMeasuredChannel } from './bandNavigation';
import { displayedCubePosition, type SkyPosition } from './cubeShare';

const channelStatuses: Record<string, string> = {
  measured: 'Measured',
  blank_channel: 'Blank in DR1',
  no_coverage: 'No usable coverage',
  flagged: 'Flagged pixel',
  missing_wavelength: 'Wavelength unavailable',
};

export function CubeView({ target, onDisplayedPosition }: {
  target: { ra: number; dec: number } | null;
  onDisplayedPosition: (position: SkyPosition | null) => void;
}) {
  const [editedRa, setRa] = useState<string | null>(null);
  const [editedDec, setDec] = useState<string | null>(null);
  const ra = editedRa ?? String(target?.ra ?? 269.45208);
  const dec = editedDec ?? String(target?.dec ?? 4.69339);
  const [query, setQuery] = useState<{ ra: string; dec: string; channel: number; forceArchive?: boolean; pinnedCloud?: boolean } | null>(null);
  const [data, setData] = useState<CubeData | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    onDisplayedPosition(displayedCubePosition(data, query));
  }, [data, query, onDisplayedPosition]);
  useEffect(() => () => onDisplayedPosition(null), [onDisplayedPosition]);

  useEffect(() => {
    if (!query) return;
    const activeQuery = query;
    const controller = new AbortController();
    const params = new URLSearchParams({ ra: activeQuery.ra, dec: activeQuery.dec, channel: String(activeQuery.channel) });
    if (activeQuery.pinnedCloud) {
      params.set('source', 'pinned_cloud');
    } else if (!activeQuery.forceArchive) {
      params.set('source', 'preview_only');
    }
    setLoading(true);
    setError('');
    async function load() {
      try {
        let response = await fetch(`/api/cube/spectrum?${params}`, { signal: controller.signal });
        if (!activeQuery.forceArchive && !activeQuery.pinnedCloud && (response.status === 404 || response.status === 503)) {
          params.delete('source');
          response = await fetch(`/api/cube/spectrum?${params}`, { signal: controller.signal });
        }
        if (!response.ok) {
          const message = await response.json();
          throw new Error(typeof message.detail === 'string' ? message.detail : 'Could not load this cube tile.');
        }
        const result: CubeData = await response.json();
        if (!controller.signal.aborted) setData(result);
      } catch (cause) {
        if (!controller.signal.aborted) {
          setData(current => current && current.ra === Number(activeQuery.ra) && current.dec === Number(activeQuery.dec) ? current : null);
          setError(cause instanceof Error ? cause.message : 'Could not load the DR1 cube.');
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    // Let a user scrub quickly without launching a cloud read for every click.
    const timer = window.setTimeout(() => { void load(); }, 250);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [query]);

  const measured = data?.channels.filter(point => point.surface_brightness_mjy_sr !== null) ?? [];
  const counts = data?.channels.reduce<Record<string, number>>((total, point) => {
    total[point.status] = (total[point.status] ?? 0) + 1;
    return total;
  }, {}) ?? {};
  const covered = data?.channels.filter(point => point.hits > 0 && point.status !== 'blank_channel').length ?? 0;
  const first = measured[0];
  const last = measured[measured.length - 1];
  const fluxes = measured.flatMap(point => point.surface_brightness_mjy_sr ?? []);
  const low = fluxes.length ? Math.min(...fluxes) : 0;
  const high = fluxes.length ? Math.max(...fluxes) : 1;
  const map = data?.channel_map;
  const mapValues = map?.pixels.flat().filter((value): value is number => value !== null) ?? [];
  const mapLow = mapValues.length ? Math.min(...mapValues) : 0;
  const mapHigh = mapValues.length ? Math.max(...mapValues) : 1;
  const active = query && data?.channels.find(point => point.channel === query.channel);
  const mapReady = !!map && map.channel === query?.channel;
  const samePosition = !!data && !!query && data.ra === Number(query.ra) && data.dec === Number(query.dec);

  const chooseChannel = (channel: number) => {
    if (!query || !data || channel === query.channel) return;
    setQuery({ ...query, channel, forceArchive: data.source !== 'cached_dr1_preview',
               pinnedCloud: data.source === 'cloud_dr1_pinned' });
  };

  useEffect(() => {
    if (!scanning || !data || !query || loading || data.channel_map?.channel !== query.channel) return;
    const next = nextMeasuredChannel(data.channels, query.channel);
    if (next === null) { setScanning(false); return; }
    const timer = window.setTimeout(() => {
      setQuery(previous => previous && previous.channel === query.channel
        ? { ...previous, channel: next, forceArchive: data.source !== 'cached_dr1_preview',
            pinnedCloud: data.source === 'cloud_dr1_pinned' } : previous);
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [scanning, data, query, loading]);

  useEffect(() => { if (error) setScanning(false); }, [error]);

  const downloadSpectrum = () => {
    if (!data) return;
    const url = URL.createObjectURL(new Blob([cubeSpectrumCsv(data)], {type: 'text/csv;charset=utf-8'}));
    const link = document.createElement('a');
    link.href = url;
    link.download = `spherex-dr1-sky-pixel-${data.tile}-${data.pixel.x}-${data.pixel.y}.csv`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  return (
    <section className="spectral-cube overflow-y-auto p-4 sm:p-7 grow">
      <div className="max-w-6xl mx-auto space-y-5">
        <header>
          <h2 className="observatory-title">Spectral Cube</h2>
          <p className="text-sm text-slate-300 mt-1">SPHEREx DR1 · NASA/IPAC IRSA · Co-added sky-pixel surface brightness</p>
          <p className="text-sm text-slate-300 mt-2 max-w-prose">A sky-pixel sample combines observations across dates and has no single target epoch. Preset coordinates are sample locations. Source identity, detection, target flux, motion, and variability remain unconfirmed.</p>
        </header>
        <form className="glass-card flex flex-wrap items-end gap-3 p-3" onSubmit={event => {
          event.preventDefault();
          setScanning(false);
          onDisplayedPosition(null);
          setData(null);
          setQuery({ ra, dec, channel: 1 });
        }}>
          <label className="text-sm">RA (degrees)
            <input className="instrument-input block mt-1 w-40 sm:w-48 max-w-full" type="number" min="0" max="359.999999999"
              step="any" required value={ra} onChange={event => setRa(event.target.value)} />
          </label>
          <label className="text-sm">Dec (degrees)
            <input className="instrument-input block mt-1 w-40 sm:w-48 max-w-full" type="number" min="-90" max="90"
              step="any" required value={dec} onChange={event => setDec(event.target.value)} />
          </label>
          <button className="min-h-[34px] px-4 rounded-lg bg-cyan-300 text-slate-950 font-semibold" type="submit">
            Load spectrum
          </button>
        </form>
        {loading && <p role="status" className="text-sm text-slate-200">{query?.pinnedCloud ? 'Loading the selected channel from the pinned DR1 cloud cube…' : query?.forceArchive ? 'Checking IRSA and the public cloud for the cube…' : 'Checking the cached preview; other positions require an IRSA archive lookup.'}</p>}
        {error && <p role="alert" className="text-sm text-amber-200">{error}</p>}
        {samePosition && data && query && active && map && (
          <>
            {data.source === 'cached_dr1_preview' && data.preview ? (
              <section className="glass-card px-3 py-2 text-sm text-slate-300" aria-label="Cube sample source">
                <h3 className="font-semibold text-amber-200">Cached DR1 sky-pixel preview</h3>
                <p>{data.preview.archive_failure === 'archive_unreadable' ? 'The archive tile could not be read.' : data.preview.archive_failure === 'archive_unreachable' ? 'The archive could not be reached.' : 'This view uses the cached preview; the archive was not checked for this request.'} The offline preview covers five preset coordinates.</p>
                <button type="button" disabled={loading} onClick={() => setQuery({ ...query, forceArchive: true, pinnedCloud: false })} className="mt-2 rounded border border-cyan-500/60 px-3 py-1 text-cyan-200 disabled:opacity-50">Check latest IRSA cube</button>
                <details className="mt-1 break-words">
                  <summary className="cursor-pointer text-cyan-200">Cache provenance</summary>
                  <p>Extracted {data.preview.generated_on} at RA {data.preview.sample_coordinate.ra}°, Dec {data.preview.sample_coordinate.dec}°.</p>
                  <p>IRSA FITS tile {data.tile} · archive ETag {data.preview.provenance.etag_md5}</p>
                  {data.preview.provenance.sha256 && <p>FITS SHA-256 {data.preview.provenance.sha256}</p>}
                </details>
              </section>
            ) : data.source === 'cloud_dr1_pinned' ? (
              <section className="glass-card px-3 py-2 text-sm text-amber-200" aria-label="Cube sample source">
                <p>Cloud DR1 cube · pinned {data.cloud?.pinned_version ?? 'release'}</p>
                <p className="text-slate-300">The IRSA search did not provide a usable tile URL. This dated release was read directly from the public cloud; it may not be the newest product.</p>
                {data.cloud?.cloud_url && <a className="text-cyan-200 underline break-all" href={data.cloud.cloud_url}>Cloud FITS source</a>}
              </section>
            ) : (
              <p className="text-sm font-medium text-cyan-200" aria-label="Cube sample source">IRSA-discovered cube · {data.cloud ? 'read from the public cloud' : 'archive result'}</p>
            )}
            <div className="space-y-1 text-sm text-slate-300">
              <p>Requested sky position · RA {data.ra.toFixed(5)}° · Dec {data.dec.toFixed(5)}°</p>
              <p>Sampled center · RA {data.pixel.ra.toFixed(5)}° · Dec {data.pixel.dec.toFixed(5)}° · HPX tile {data.tile}, pixel ({data.pixel.x}, {data.pixel.y})</p>
              <p>{data.channels.length} DR1 channel slots · {covered} with hits · {measured.length} measured · {counts.flagged ?? 0} flagged · {counts.blank_channel ?? 0} blank · {counts.no_coverage ?? 0} without usable coverage</p>
              {!!counts.missing_wavelength && <p>{counts.missing_wavelength} with wavelength metadata unavailable</p>}
              {first && last && <p>Measured centers {first.wavelength_um?.toFixed(3)}–{last.wavelength_um?.toFixed(3)} µm · first channel {first.channel}, last channel {last.channel}</p>}
              <p>Channel availability varies by position. The plot leaves unavailable channels as gaps.</p>
              <button type="button" onClick={downloadSpectrum} className="mt-2 rounded-lg border border-cyan-500/60 px-3 py-1.5 text-cyan-200 hover:bg-cyan-950 focus-visible:ring-2 focus-visible:ring-cyan-400">Download sky-pixel spectrum as CSV</button>
              <p className="text-xs text-slate-400">CSV includes flags and unfiltered archive values; use the status and filtered brightness column to identify usable samples.</p>
            </div>
            <section className="glass-card p-4 space-y-3" aria-label="Explore the six SPHEREx detectors">
              <div>
                <h3 className="font-semibold text-slate-100">Explore all 102 channels</h3>
                <p className="text-sm text-slate-300">Start with a detector, then choose one of its 17 channels—or click a measured point on the spectrum below.</p>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2" role="group" aria-label="Detector groups">
                {[1, 2, 3, 4, 5, 6].map(detector => {
                  const group = detectorChannels(data.channels, detector);
                  const available = group.filter(point => point.status === 'measured').length;
                  const lowWave = group[0]?.wavelength_um;
                  const highWave = group[group.length - 1]?.wavelength_um;
                  return <button key={detector} type="button" aria-pressed={active.detector === detector}
                    onClick={() => { const next = firstUsefulChannel(data.channels, detector); if (next !== null) chooseChannel(next); }}
                    className={`rounded-lg border px-2 py-2 text-left focus-visible:ring-2 focus-visible:ring-cyan-400 ${active.detector === detector ? 'border-cyan-300 bg-cyan-400/15 text-cyan-100' : 'border-slate-700 bg-slate-950/70 text-slate-200 hover:border-cyan-500'}`}>
                    <span className="block font-semibold">Detector {detector}</span>
                    <span className="block text-xs text-slate-300">{lowWave != null && highWave != null ? `${lowWave.toFixed(2)}–${highWave.toFixed(2)} µm` : 'Wavelengths unavailable'}</span>
                    <span className="block text-xs text-slate-400">{available} / {group.length} measured</span>
                  </button>;
                })}
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="font-medium text-slate-200">Detector {active.detector} · choose a channel</span>
                <span className="text-xs text-slate-400">Cyan: measured · Amber: flagged · Gray: unavailable</span>
              </div>
              <button type="button" aria-pressed={scanning}
                disabled={detectorChannels(data.channels, active.detector).filter(point => point.status === 'measured').length < 2}
                onClick={() => setScanning(value => !value)}
                className="rounded border border-cyan-600 px-3 py-1 text-sm text-cyan-100 hover:bg-cyan-950 disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-cyan-400">
                {scanning ? 'Pause wavelength scan' : 'Scan measured channels'}
              </button>
              <p className="text-xs text-slate-400">Scanning changes wavelength within this detector; it is not a time-lapse. Unavailable channels are skipped.</p>
              <div className="grid grid-cols-9 sm:grid-cols-[repeat(17,minmax(0,1fr))] gap-1" role="group" aria-label={`Detector ${active.detector} channels`}>
                {detectorChannels(data.channels, active.detector).map(point => (
                  <button key={point.channel} type="button" onClick={() => chooseChannel(point.channel)}
                    aria-pressed={point.channel === query.channel}
                    aria-label={`Channel ${point.channel}, detector ${point.detector} channel ${point.subchannel}, ${point.wavelength_um?.toFixed(3) ?? 'unknown wavelength'} micrometers, ${channelStatuses[point.status] ?? point.status}`}
                    title={`Channel ${point.channel} · ${point.wavelength_um?.toFixed(3) ?? '—'} µm · ${channelStatuses[point.status] ?? point.status}`}
                    className={`min-h-9 rounded border text-xs font-mono focus-visible:ring-2 focus-visible:ring-white ${point.channel === query.channel ? 'ring-2 ring-white border-white' : ''} ${point.status === 'measured' ? 'bg-cyan-700/60 text-cyan-50 border-cyan-600' : point.status === 'flagged' ? 'bg-amber-800/60 text-amber-100 border-amber-600' : 'bg-slate-800 text-slate-400 border-slate-700'}`}>
                    {point.subchannel}
                  </button>
                ))}
              </div>
              <p className="text-xs text-slate-400">These are co-added sky-pixel samples, not a time sequence or a confirmed source spectrum.</p>
            </section>
            <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
              <div>
                <label className="text-sm">Channel map
                  <select className="instrument-input block w-full mt-1" value={query.channel}
                    onChange={event => chooseChannel(Number(event.target.value))}>
                    {data.channels.map(point => <option key={point.channel} value={point.channel}>
                      {point.channel} · {point.wavelength_um?.toFixed(3) ?? '—'} µm · {channelStatuses[point.status]}
                    </option>)}
                  </select>
                </label>
                {mapReady ? <><svg className="mt-2 block w-full max-w-80 bg-slate-950" role="img"
                  aria-label={`Native HPX surface brightness map, channel ${map.channel}`}
                  shapeRendering="crispEdges" viewBox={`0 0 ${map.pixels[0].length} ${map.pixels.length}`}>
                  {map.pixels.map((row, y) => row.map((value, x) => {
                    if (value === null) return null;
                    const gray = Math.round(35 + 220 * (value - mapLow) / (mapHigh - mapLow || 1));
                    return <rect key={`${x},${y}`} x={x} y={map.pixels.length - 1 - y}
                      width="1" height="1" fill={`rgb(${gray},${gray},${gray})`} />;
                  }))}
                  <rect x={map.center_x} y={map.pixels.length - 1 - map.center_y} width="1" height="1"
                    fill="none" stroke="#67e8f9" strokeWidth="0.13" />
                </svg>
                <p className="text-sm text-slate-300 mt-2">{mapValues.length
                  ? `Linear range ${mapLow.toPrecision(4)}–${mapHigh.toPrecision(4)} MJy/sr`
                  : 'No usable pixels in this channel map'}</p>
                </> : <div className="mt-2 aspect-square w-full max-w-80 rounded-lg bg-slate-950 p-4 text-sm text-slate-300" role="status">
                  {error ? <><p>Channel {query.channel} map could not be loaded.</p><button type="button" onClick={() => setQuery({ ...query })} className="mt-2 rounded border border-cyan-600 px-2 py-1 text-cyan-200">Retry channel</button></> : `Loading channel ${query.channel} map…`}
                </div>}
                <p className="text-sm text-slate-300">Channel {active.channel} sampled pixel · {channelStatuses[active.status]} · {active.hits} hits · flags 0x{active.flags.toString(16)}</p>
                {active.wavelength_min_um != null && active.wavelength_max_um != null &&
                  <p className="text-sm text-slate-300">Channel bounds {active.wavelength_min_um.toFixed(3)}–{active.wavelength_max_um.toFixed(3)} µm</p>}
                {active.bandwidth_um != null &&
                  <p className="text-sm text-slate-300">Channel bandwidth {active.bandwidth_um.toFixed(3)} µm</p>}
                {mapReady && active.status !== 'measured' && mapValues.length > 0 && (
                  <p className="text-sm text-slate-300">The outline marks the sampled pixel. Surrounding pixels may have coverage.</p>
                )}
                {active.surface_brightness_mjy_sr !== null && (
                  <p className="text-sm text-slate-200">Sampled sky brightness {active.surface_brightness_mjy_sr.toPrecision(6)} MJy/sr</p>
                )}
              </div>
              <div className="min-w-0">
                <h3 className="font-semibold">Measured surface brightness (MJy/sr)</h3>
                {measured.length ? (
                  <svg className="w-full bg-slate-950 rounded-lg mt-2" viewBox="0 0 460 214" role="img"
                    aria-label="Measured DR1 surface brightness by wavelength. Missing channels are gaps.">
                    <path d="M58 18V178H439" stroke="#64748b" fill="none" />
                    <g fill="#cbd5e1" fontSize="12">
                      <text x="52" y="24" textAnchor="end">{high.toPrecision(4)}</text>
                      <text x="52" y="178" textAnchor="end">{low.toPrecision(4)}</text>
                      {[1, 2, 3, 4, 5].map(tick => <text key={tick} textAnchor="middle"
                        x={60 + (tick - 0.7) * 86} y="198">{tick} µm</text>)}
                    </g>
                    {measured.map(point => (
                      <circle key={point.channel} r={point.channel === active.channel ? 5 : 3}
                        cx={60 + ((point.wavelength_um ?? 0) - 0.7) * 86}
                        cy={high === low ? 98 : 174 - ((point.surface_brightness_mjy_sr ?? 0) - low) / (high - low) * 150}
                        className="cursor-pointer" onClick={() => chooseChannel(point.channel)}
                        fill={point.channel === active.channel ? '#f2b85b' : '#67e8f9'}>
                        <title>Channel {point.channel}: {point.surface_brightness_mjy_sr?.toPrecision(6)} MJy/sr</title>
                      </circle>
                    ))}
                  </svg>
                ) : <p className="mt-2 text-amber-200">No usable spectrum at this pixel.</p>}
                <p className="text-sm text-slate-300 mt-2">Uncertainty unavailable. The FITS cube has no variance plane.</p>
              </div>
            </div>
            <a className="text-sm text-cyan-300 underline" href={data.fits_url}>Original IRSA FITS tile</a>
          </>
        )}
        <details className="border-t border-slate-600 pt-3 text-sm text-slate-300">
          <summary className="cursor-pointer font-semibold">Data and limitations</summary>
          <p className="mt-2">The six detector arrays supply dated exposures. The Explorer can summarize up to six detector-level field samples. This view shows the separate DR1 cube with 102 nominal slots.</p>
          <p className="mt-2">Detector groups organize channels; they are not summed together here. Channels represent different wavelengths. Difference &amp; Stack combines dated exposures only where their calibrated passbands are compatible.</p>
          <p className="mt-2">The DR1 cube combines observations over time and has zodiacal light subtracted. The spectrum samples one nearest 12.9″ HEALPix pixel. Maps show native pixels within this tile and may end at a tile boundary.</p>
          <p className="mt-2">Channels 51 and 52 are blank in DR1. The SOURCE flag is informational. Overflow, outlier, or uncovered pixels are excluded. Hit counts describe contributing pixels. Atmospheric emission, especially near 1.083 µm, can produce striping.</p>
          <a className="mt-2 inline-block text-cyan-300 underline" href="https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/#science-data-product-all-sky-cube-dr1-only">IRSA cube documentation</a>
        </details>
      </div>
    </section>
  );
}
