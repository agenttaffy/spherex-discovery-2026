import React from 'react';
import { ExternalLink, Info, Activity, ShieldCheck, Tag, FileText } from 'lucide-react';
import { FrameResponse } from '../../types/astronomy';

interface MetadataPanelProps {
  frame: FrameResponse | null;
}

export const MetadataPanel: React.FC<MetadataPanelProps> = ({ frame }) => {
  if (!frame) {
    return (
      <div className="w-80 bg-slate-900/60 border-l border-slate-800 p-4 text-xs text-slate-500 flex flex-col items-center justify-center text-center">
        <Info className="w-8 h-8 opacity-40 mb-2 text-cyan-400" />
        <p>Select an observation frame to inspect calibrated telemetry, quality bitmasks, and provenance.</p>
      </div>
    );
  }

  const { pixel_stats, flag_summary, wcs } = frame;

  return (
    <div className="w-80 bg-slate-900/60 border-l border-slate-800 p-4 flex flex-col gap-4 overflow-y-auto text-xs">
      <div>
        <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-2">
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
            <span className="text-slate-300">{frame.dimensions.join(' × ')} px</span>
          </div>
        </div>
      </div>

      {/* Scientific Pixel Telemetry */}
      <div>
        <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-2">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          Surface Brightness (MJy/sr)
        </label>
        <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 grid grid-cols-2 gap-2 font-mono">
          <div>
            <span className="text-[10px] text-slate-500 block">Peak Max</span>
            <span className="text-amber-400 font-semibold">{pixel_stats.max_mjy_sr.toFixed(3)}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-500 block">Baseline Min</span>
            <span className="text-slate-300">{pixel_stats.min_mjy_sr.toFixed(3)}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-500 block">Mean Flux</span>
            <span className="text-slate-300">{pixel_stats.mean_mjy_sr.toFixed(3)}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-500 block">Noise (Std)</span>
            <span className="text-slate-400">±{pixel_stats.std_mjy_sr.toFixed(3)}</span>
          </div>
        </div>
      </div>

      {/* Quality Bitmask Evaluation */}
      <div>
        <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-2">
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
          Data Quality Flags
        </label>
        <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 space-y-1.5">
          <div className="flex justify-between items-center text-[11px]">
            <span className="text-slate-400">Flagged Pixels:</span>
            <span className={flag_summary.flagged_pixels === 0 ? 'text-emerald-400 font-semibold' : 'text-amber-400 font-semibold'}>
              {flag_summary.flagged_pixels} / {flag_summary.total_pixels}
            </span>
          </div>
          {Object.entries(flag_summary.flag_breakdown).map(([key, val]) => (
            val > 0 && (
              <div key={key} className="flex justify-between items-center text-[10px] text-slate-400 pl-2">
                <span className="capitalize">{key.replace('_', ' ')}:</span>
                <span className="text-amber-300 font-mono">{val}</span>
              </div>
            )
          ))}
        </div>
      </div>

      {/* WCS Astrometry */}
      {wcs.crval1 !== null && wcs.crval1 !== undefined && (
        <div>
          <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-2">
            <FileText className="w-3.5 h-3.5 text-cyan-400" />
            Celestial WCS
          </label>
          <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 font-mono space-y-1 text-[11px]">
            <div className="flex justify-between">
              <span className="text-slate-500">Center RA:</span>
              <span className="text-slate-300">{wcs.crval1.toFixed(5)}°</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Center Dec:</span>
              <span className="text-slate-300">{wcs.crval2?.toFixed(5)}°</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Scale:</span>
              <span className="text-slate-400">6.2″/pixel</span>
            </div>
          </div>
        </div>
      )}

      {/* Provenance & Citation Link */}
      <div className="mt-auto pt-2">
        <a
          href={frame.provenance_url}
          target="_blank"
          rel="noreferrer"
          className="w-full py-2 px-3 bg-slate-950 border border-slate-800 hover:border-cyan-500/50 rounded-lg text-slate-300 hover:text-cyan-300 text-[11px] flex items-center justify-center gap-1.5 transition"
        >
          <span>Raw NASA FITS Cutout</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
};
