import React, { useState } from 'react';
import { ExternalLink, Info, Activity, ShieldCheck, Tag, FileText, Download, Layers } from 'lucide-react';
import { FrameResponse, LightCurveSeries, SpectrumResponse } from '../../types/astronomy';
import { LightCurveChart } from '../science/LightCurveChart';
import { SpectrumChart } from '../science/SpectrumChart';

interface MetadataPanelProps {
  frame: FrameResponse | null;
  lightCurve?: LightCurveSeries | null;
  loadingPhotometry?: boolean;
  spectrum?: SpectrumResponse | null;
  loadingSpectrum?: boolean;
  onSelectObsId?: (obsId: string) => void;
  onOpenDiscoveryReport?: () => void;
}

export const MetadataPanel: React.FC<MetadataPanelProps> = ({
  frame,
  lightCurve = null,
  loadingPhotometry = false,
  spectrum = null,
  loadingSpectrum = false,
  onSelectObsId,
  onOpenDiscoveryReport,
}) => {
  const [telemetryTab, setTelemetryTab] = useState<'lightcurve' | 'spectrum'>('spectrum');

  return (
    <aside
      aria-label="Scientific telemetry and observation metadata"
      className="w-full lg:w-80 lg:shrink-0 bg-slate-900/60 border-t lg:border-t-0 lg:border-l border-slate-800 p-4 flex flex-col gap-4 overflow-y-auto text-xs"
    >
      {/* Telemetry Mode Tabs Switcher */}
      <div
        role="tablist"
        aria-label="Science telemetry view switcher"
        className="flex bg-slate-950/90 p-1 rounded-lg border border-slate-800 gap-1 text-[11px] font-mono"
      >
        <button
          role="tab"
          aria-selected={telemetryTab === 'spectrum'}
          aria-label="Show infrared SED spectrum and estimated continuum"
          onClick={() => setTelemetryTab('spectrum')}
          className={`flex-1 py-1.5 px-2 rounded flex items-center justify-center gap-1.5 transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
            telemetryTab === 'spectrum'
              ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 font-semibold'
              : 'text-slate-300 hover:text-white'
          }`}
        >
          <Layers className="w-3.5 h-3.5 text-indigo-400" />
          <span>Infrared SED</span>
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
          <span>Light Curve</span>
        </button>
      </div>

      {/* Switchable Science Telemetry Chart */}
      {telemetryTab === 'spectrum' ? (
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
                <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 space-y-2 font-mono">
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
                <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 grid grid-cols-2 gap-2 font-mono">
                  <div>
                    <span className="text-[10px] text-slate-400 block">Peak Max</span>
                    <span className="text-amber-300 font-semibold">{pixel_stats.max_mjy_sr.toFixed(3)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Baseline Min</span>
                    <span className="text-slate-200">{pixel_stats.min_mjy_sr.toFixed(3)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Mean Flux</span>
                    <span className="text-slate-200">{pixel_stats.mean_mjy_sr.toFixed(3)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Noise (Std)</span>
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
                <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 space-y-1.5">
                  {flag_summary.quality_state === 'documented_metadata' ? <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-400">Flagged Pixels:</span>
                    <span className={flag_summary.flagged_pixels === 0 ? 'text-emerald-400 font-semibold' : 'text-amber-300 font-semibold'}>
                      {flag_summary.flagged_pixels} / {flag_summary.total_pixels}
                    </span>
                  </div> : <p className="text-[11px] text-amber-300">Quality flags unavailable or their definitions are unknown.</p>}
                  {flag_summary.quality_state === 'documented_metadata' && Object.entries(flag_summary.flag_breakdown).map(([key, val]) => (
                    val > 0 && (
                      <div key={key} className="flex justify-between items-center text-[10px] text-slate-300 pl-2">
                        <span className="capitalize">{key.replace('_', ' ')}:</span>
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
                  <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 font-mono space-y-1 text-[11px]">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Center RA:</span>
                      <span className="text-slate-200">{wcs.crval1.toFixed(5)}°</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Center Dec:</span>
                      <span className="text-slate-200">{wcs.crval2?.toFixed(5)}°</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Scale:</span>
                      <span className="text-slate-300">6.2″/pixel</span>
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
                <a
                  href={frame.provenance_url}
                  target="_blank"
                  rel="noreferrer"
                  aria-label="View raw NASA FITS cutout archive source in new window"
                  className="w-full py-1.5 px-3 bg-slate-950 border border-slate-800 hover:border-cyan-500/50 rounded-lg text-slate-300 hover:text-cyan-300 text-[11px] flex items-center justify-center gap-1.5 transition font-mono focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
                >
                  <span>Raw NASA FITS Cutout</span>
                  <ExternalLink className="w-3 h-3 text-cyan-400" />
                </a>
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
