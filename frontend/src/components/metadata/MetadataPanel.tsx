import React, { useState } from 'react';
import { ExternalLink, Info, Activity, ShieldCheck, Tag, FileText, Download, Layers } from 'lucide-react';
import { CatalogSource, FrameResponse, LightCurveSeries, SpectrumResponse } from '../../types/astronomy';
import { LightCurveChart } from '../science/LightCurveChart';
import { SpectrumChart } from '../science/SpectrumChart';
import { QuickSkySpectrum } from '../science/QuickSkySpectrum';
import type { CubeData } from '../science/cubeCsv';
import { imageProvenanceLabel } from '../../services/imageProvenance';

interface MetadataPanelProps {
  namedTarget?: boolean;
  frame: FrameResponse | null;
  catalogSources: CatalogSource[];
  catalogEnabled: boolean;
  loadingCatalog: boolean;
  catalogQueryError: boolean;
  lightCurve?: LightCurveSeries | null;
  loadingPhotometry?: boolean;
  spectrum?: SpectrumResponse | null;
  loadingSpectrum?: boolean;
  onRefreshAnalysis?: () => void;
  onSelectObsId?: (obsId: string) => void;
  onOpenDiscoveryReport?: () => void;
  samplePosition: { ra: number; dec: number } | null;
  analysisEnabled: boolean;
  fieldCube?: CubeData | null;
  onOpenCube: () => void;
}

export const MetadataPanel: React.FC<MetadataPanelProps> = ({
  namedTarget,
  frame,
  catalogSources,
  catalogEnabled,
  loadingCatalog,
  catalogQueryError,
  lightCurve = null,
  loadingPhotometry = false,
  spectrum = null,
  loadingSpectrum = false,
  onRefreshAnalysis,
  onSelectObsId,
  onOpenDiscoveryReport,
  samplePosition,
  analysisEnabled,
  fieldCube = null,
  onOpenCube,
}) => {
  const [telemetryTab, setTelemetryTab] = useState<'cube' | 'lightcurve' | 'spectrum'>('cube');

  const nearest = catalogEnabled && !loadingCatalog && !catalogQueryError
    ? catalogSources.reduce<CatalogSource | undefined>((best, source) =>
        !best || source.separation_arcsec < best.separation_arcsec ? source : best, undefined)
    : undefined;
  const provenance = nearest?.provenance || nearest?.catalog_source || 'Unknown catalog source';

  return (
    <aside
      aria-label="Scientific telemetry and observation metadata"
      className="inspector-panel w-full lg:w-80 lg:shrink-0 bg-slate-900/60 border-t lg:border-t-0 lg:border-l border-slate-800 p-4 flex flex-col gap-4 overflow-y-auto text-xs"
    >
      <h2 className="text-base font-semibold">Observation inspector</h2>
      {telemetryTab !== 'cube' && <div className="text-slate-300 space-y-1">
        <p>Analysis uses cached cutouts among up to 60 search results. Open observations, then refresh; missing images are not downloaded automatically.</p>
        <button type="button" onClick={onRefreshAnalysis} disabled={loadingPhotometry || loadingSpectrum} className="text-cyan-200 underline disabled:opacity-50">Refresh field analysis</button>
      </div>}
      <details className="border-b border-slate-800 pb-3">
        <summary className="cursor-pointer py-1 text-sm font-medium">Reference catalog</summary>
        <div className="mt-2 space-y-2 text-slate-300">
          <p>Gaia DR3 positions start at J2016.0. Image markers use approximate proper-motion shifts when motion and exposure time are available; parallax and radial motion are not modeled.</p>
          <p>The search adds a 3′ margin for motion and returns up to 200 of the brightest sources. Fast-moving or fainter sources may still be omitted.</p>
          <div role="status">
            {!catalogEnabled && <p>Enable the reference catalog in the image toolbar to load sources.</p>}
            {catalogEnabled && loadingCatalog && <p>Loading reference sources…</p>}
            {catalogEnabled && catalogQueryError && <p>Reference sources could not load. Toggle the overlay to retry.</p>}
            {catalogEnabled && !loadingCatalog && !catalogQueryError && !nearest && <p>No reference sources are available for this position.</p>}
          </div>
          {nearest && (
            <>
              <p className="text-slate-400">Nearest listed J2016.0 position to the search coordinate</p>
              <p className="break-words font-medium text-slate-100">{nearest.designation || nearest.source_id}</p>
              <p className="tabular-nums">{nearest.separation_arcsec.toFixed(2)} arcsec · {provenance}</p>
              <p>{/demo|curated/i.test(provenance)
                ? 'Demo coordinates do not independently confirm identity.'
                : 'Proximity alone does not confirm a match.'}</p>
            </>
          )}
          {catalogEnabled && !loadingCatalog && !catalogQueryError && catalogSources.length > 0 && (
            <details className="pt-1">
              <summary className="cursor-pointer text-cyan-200">View {catalogSources.length} returned Gaia sources</summary>
              <p className="mt-2 text-slate-400">The search region extends beyond the image, so some listed sources are off-frame. Separations use the catalog positions at J2016.0.</p>
              <ol className="mt-2 max-h-48 space-y-2 overflow-y-auto pr-1">
                {catalogSources.map(source => (
                  <li key={source.source_id} className="border-b border-slate-800 pb-1">
                    <span className="block break-all text-slate-100">{source.designation || source.source_id}</span>
                    <span className="tabular-nums">{source.separation_arcsec.toFixed(2)}″ from search center{source.g_mag != null ? ` · G ${source.g_mag.toFixed(2)}` : ''}</span>
                  </li>
                ))}
              </ol>
            </details>
          )}
        </div>
      </details>
      <div
        role="tablist"
        aria-label="Science telemetry view switcher"
        className="grid grid-cols-3 bg-slate-950/90 p-1 rounded-lg border border-slate-800 gap-1 text-[11px] font-mono"
      >
        <button role="tab" aria-selected={telemetryTab === 'cube'} aria-label="Show cached sky-pixel spectrum"
          onClick={() => setTelemetryTab('cube')}
          className={`py-1.5 px-1 rounded transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${telemetryTab === 'cube' ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/40 font-semibold' : 'text-slate-300 hover:text-white'}`}>
          Sky spectrum
        </button>
        <button
          role="tab"
          aria-selected={telemetryTab === 'spectrum'}
          aria-label="Show detector field samples"
          onClick={() => setTelemetryTab('spectrum')}
          className={`flex-1 py-1.5 px-2 rounded flex items-center justify-center gap-1.5 transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
            telemetryTab === 'spectrum'
              ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 font-semibold'
              : 'text-slate-300 hover:text-white'
          }`}
        >
          <Layers className="w-3.5 h-3.5 text-indigo-400" />
          <span>Detector</span>
        </button>
        <button
          role="tab"
          aria-selected={telemetryTab === 'lightcurve'}
          aria-label="Show aperture photometric light curve"
          onClick={() => setTelemetryTab('lightcurve')}
          className={`flex-1 py-1.5 px-2 rounded flex items-center justify-center gap-1.5 transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
            telemetryTab === 'lightcurve'
              ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 font-semibold'
              : 'text-slate-300 hover:text-white'
          }`}
        >
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span>Light curve</span>
        </button>
      </div>

      {/* Switchable Science Telemetry Chart */}
      {namedTarget && telemetryTab !== 'cube' && <p className="text-xs text-amber-200">Aperture results describe the search field. Target association and variability are unconfirmed.</p>}
      {telemetryTab === 'cube' ? <QuickSkySpectrum position={samplePosition} enabled={analysisEnabled} fieldCube={fieldCube} onOpenCube={onOpenCube} /> : telemetryTab === 'spectrum' ? (
        <SpectrumChart spectrum={spectrum} loading={loadingSpectrum} />
      ) : (
        <LightCurveChart
          series={lightCurve}
          loading={loadingPhotometry}
          selectedObsId={frame?.obs_id}
          onSelectObsId={onSelectObsId}
        />
      )}

      {frame ? (
        (() => {
          const { pixel_stats, flag_summary, wcs } = frame;
          return (
            <>
              <div>
                <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 mb-2">
                  <Tag className="w-3.5 h-3.5 text-cyan-400" />
                  Observation Metadata
                </label>
                <div className="border-t border-slate-800 pt-2 space-y-2 font-mono">
                  <div>
                    <span className="block text-slate-400">Image source</span>
                    <span className="text-slate-200 break-words">{imageProvenanceLabel(frame.image_provenance)}</span>
                  </div>
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-400">Obs ID:</span>
                    <span className="text-cyan-300 font-semibold">{frame.obs_id}</span>
                  </div>
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-400">Release:</span>
                    <span className="text-slate-200 uppercase">{frame.collection}</span>
                  </div>
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-400">Detector:</span>
                    <span className="text-indigo-300 font-semibold">{frame.detector}</span>
                  </div>
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-400">UTC Date:</span>
                    <span className="text-slate-200">{frame.utc_date || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-400">Dimensions:</span>
                    <span className="text-slate-200">{frame.dimensions.join(' × ')} px</span>
                  </div>
                </div>
              </div>

              {/* Scientific Pixel Telemetry */}
              <div>
                <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 mb-2">
                  <Activity className="w-3.5 h-3.5 text-cyan-400" />
                  Surface Brightness (MJy/sr)
                </label>
                <div className="border-t border-slate-800 pt-2 grid grid-cols-2 gap-2 font-mono">
                  <div>
                    <span className="text-[10px] text-slate-400 block">Peak Max</span>
                    <span className="text-amber-300 font-semibold">{pixel_stats.max_mjy_sr.toFixed(3)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Baseline Min</span>
                    <span className="text-slate-200">{pixel_stats.min_mjy_sr.toFixed(3)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Mean brightness</span>
                    <span className="text-slate-200">{pixel_stats.mean_mjy_sr.toFixed(3)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Pixel standard deviation</span>
                    <span className="text-slate-300">±{pixel_stats.std_mjy_sr.toFixed(3)}</span>
                  </div>
                </div>
              </div>

              {/* Quality Bitmask Evaluation */}
              <div>
                <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 mb-2">
                  <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                  Data Quality Flags
                </label>
                <p className="text-[11px] text-slate-300 mb-2">The exclusion count uses the app’s quality mask. Other flags, including source detection, are shown separately; counts can overlap and do not identify an object.</p>
                <div className="border-t border-slate-800 pt-2 space-y-1.5">
                  {flag_summary.quality_state === 'documented_metadata' ? <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-400">Pixels with exclusion flags:</span>
                    <span className={flag_summary.flagged_pixels === 0 ? 'text-emerald-400 font-semibold' : 'text-amber-300 font-semibold'}>
                      {flag_summary.flagged_pixels} / {flag_summary.total_pixels}
                    </span>
                  </div> : <p className="text-[11px] text-amber-300">Quality flags unavailable or their definitions are unknown.</p>}
                  {flag_summary.quality_state === 'documented_metadata' && Object.entries(flag_summary.flag_breakdown).map(([key, val]) => (
                    val > 0 && (
                      <div key={key} className="flex justify-between items-center text-[10px] text-slate-300 pl-2">
                        <span className="capitalize">{key.replace(/_/g, ' ')}:</span>
                        <span className="text-amber-200 font-mono">{val}</span>
                      </div>
                    )
                  ))}
                </div>
              </div>

              {/* WCS Astrometry */}
              {wcs.crval1 !== null && wcs.crval1 !== undefined && (
                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 mb-2">
                    <FileText className="w-3.5 h-3.5 text-cyan-400" />
                    Celestial WCS
                  </label>
                  <div className="border-t border-slate-800 pt-2 font-mono space-y-1 text-[11px]">
                    <div className="flex justify-between">
                      <span className="text-slate-400">WCS reference RA:</span>
                      <span className="text-slate-200">{wcs.crval1.toFixed(5)}°</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">WCS reference Dec:</span>
                      <span className="text-slate-200">{wcs.crval2?.toFixed(5)}°</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Discovery Report Action Button */}
              {onOpenDiscoveryReport && (
                <button
                  onClick={onOpenDiscoveryReport}
                  aria-label="Export Scientific Discovery Report modal"
                  className="w-full py-2 px-3 bg-gradient-to-r from-cyan-600/30 to-indigo-600/30 hover:from-cyan-600/50 hover:to-indigo-600/50 border border-cyan-500/40 rounded-lg text-cyan-200 font-semibold text-xs flex items-center justify-center gap-2 transition shadow-md shadow-cyan-950/40 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
                >
                  <Download className="w-3.5 h-3.5 text-cyan-300" />
                  <span>Export Discovery Report</span>
                </button>
              )}

              {/* Provenance & Citation Link */}
              <div className="mt-auto pt-1">
                {/^https?:\/\//i.test(frame.provenance_url) && !frame.is_synthetic ? <a
                  href={frame.provenance_url}
                  target="_blank"
                  rel="noreferrer"
                  aria-label="View the NASA archive product in a new window"
                  className="w-full py-1.5 px-3 bg-slate-950 border border-slate-800 hover:border-cyan-500/50 rounded-lg text-slate-300 hover:text-cyan-300 text-[11px] flex items-center justify-center gap-1.5 transition font-mono focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
                >
                  <span>View archive product</span>
                  <ExternalLink className="w-3 h-3 text-cyan-400" />
                </a> : <p className="text-slate-300">No archive product link is available for this image.</p>}
              </div>
            </>
          );
        })()
      ) : (
        <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 text-xs text-slate-400 flex flex-col items-center justify-center text-center mt-2">
          <Info className="w-6 h-6 opacity-40 mb-2 text-cyan-400" />
          <p>Select an observation frame from the timeline to inspect calibrated pixel stats, quality bitmasks, and WCS header.</p>
        </div>
      )}
    </aside>
  );
};
