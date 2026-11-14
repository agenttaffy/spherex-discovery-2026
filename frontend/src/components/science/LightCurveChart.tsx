import React, { useState } from 'react';
import { LightCurveSeries, PhotometryPoint } from '../../types/astronomy';
import { Activity, Flame, CheckCircle, Table } from 'lucide-react';

interface LightCurveChartProps {
  series: LightCurveSeries | null;
  loading?: boolean;
  selectedObsId?: string;
  onSelectObsId?: (obsId: string) => void;
}

export const LightCurveChart: React.FC<LightCurveChartProps> = ({
  series,
  loading = false,
  selectedObsId,
  onSelectObsId,
}) => {
  const [hoveredPoint, setHoveredPoint] = useState<PhotometryPoint | null>(null);

  if (loading) {
    return (
      <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 flex flex-col items-center justify-center h-48 text-slate-300">
        <Activity className="w-6 h-6 animate-pulse text-cyan-400 mb-2" />
        <span className="text-xs">Extracting aperture photometry...</span>
      </div>
    );
  }

  if (!series || series.points.length === 0) {
    return (
      <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 flex flex-col items-center justify-center h-44 text-slate-400 text-xs text-center">
        <Activity className="w-6 h-6 opacity-40 mb-2 text-cyan-400" />
        <p>No multi-epoch photometry available for current coordinates.</p>
      </div>
    );
  }

  const { points, is_variable, variability_index, mean_flux_mjy_sr, min_flux_mjy_sr, max_flux_mjy_sr, amplitude_delta_mjy_sr } = series;

  // SVG Geometry
  const width = 280;
  const height = 110;
  const padLeft = 32;
  const padRight = 16;
  const padTop = 14;
  const padBottom = 22;

  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const paddingFlux = Math.max(0.5, (max_flux_mjy_sr - min_flux_mjy_sr) * 0.1);
  const yMin = min_flux_mjy_sr - paddingFlux;
  const yMax = max_flux_mjy_sr + paddingFlux;
  const yRange = Math.max(1e-4, yMax - yMin);

  const xCoords = points.map((_, i) => {
    return points.length === 1 ? padLeft + plotW / 2 : padLeft + (i / (points.length - 1)) * plotW;
  });

  const yCoords = points.map((p) => {
    const norm = (p.net_flux_mjy_sr - yMin) / yRange;
    return padTop + plotH - norm * plotH;
  });

  const meanY = padTop + plotH - ((mean_flux_mjy_sr - yMin) / yRange) * plotH;

  // SVG Polyline Path
  const polyPoints = points.map((_, i) => `${xCoords[i]},${yCoords[i]}`).join(' ');

  return (
    <div className="bg-slate-950/90 border border-slate-800 rounded-lg p-3 space-y-2">
      {/* Header & Variability Flag */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-200">
            Light Curve (Aperture Flux)
          </span>
        </div>
        <div>
          {is_variable ? (
            <span className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-950/80 text-amber-300 border border-amber-800/80 animate-pulse">
              <Flame className="w-3 h-3 text-amber-400" />
              Variable (Var={variability_index})
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-950/60 text-emerald-300 border border-emerald-800/60">
              <CheckCircle className="w-3 h-3 text-emerald-400" />
              Stable Flux
            </span>
          )}
        </div>
      </div>

      {/* SVG Plot */}
      <div className="relative">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={`SPHEREx Multi-Epoch Photometric Light Curve across ${points.length} epochs. Mean flux is ${mean_flux_mjy_sr.toFixed(2)} MegaJanskys per steradian with amplitude variation ${amplitude_delta_mjy_sr.toFixed(2)}.`}
          className="w-full h-28 bg-slate-900/60 rounded border border-slate-800/70 select-none"
        >
          {/* Y Axis Gridlines */}
          <line x1={padLeft} y1={padTop} x2={width - padRight} y2={padTop} stroke="#475569" strokeDasharray="2,2" strokeWidth="0.8" />
          <line x1={padLeft} y1={padTop + plotH} x2={width - padRight} y2={padTop + plotH} stroke="#475569" strokeWidth="1" />
          
          {/* Y-axis labels */}
          <text x={padLeft - 4} y={padTop + 3} fill="#94a3b8" fontSize="8" textAnchor="end" fontFamily="monospace">
            {yMax.toFixed(1)}
          </text>
          <text x={padLeft - 4} y={padTop + plotH + 3} fill="#94a3b8" fontSize="8" textAnchor="end" fontFamily="monospace">
            {yMin.toFixed(1)}
          </text>

          {/* Mean flux dashed line */}
          <line
            x1={padLeft}
            y1={meanY}
            x2={width - padRight}
            y2={meanY}
            stroke="#38bdf8"
            strokeDasharray="3,3"
            strokeWidth="0.9"
            opacity="0.7"
          />

          {/* Connecting line */}
          {points.length > 1 && (
            <polyline
              points={polyPoints}
              fill="none"
              stroke="#06b6d4"
              strokeWidth="1.8"
              strokeLinejoin="round"
            />
          )}

          {/* Data Points */}
          {points.map((p, i) => {
            const isSelected = selectedObsId === p.obs_id;
            const isHovered = hoveredPoint?.obs_id === p.obs_id;
            return (
              <g
                key={p.obs_id + i}
                className="cursor-pointer"
                tabIndex={0}
                role="button"
                aria-label={`Epoch ${i + 1}, observation ${p.obs_id}, date ${p.utc_date?.slice(0, 10) || 'N/A'}, net flux ${p.net_flux_mjy_sr.toFixed(2)} MegaJanskys per steradian`}
                onMouseEnter={() => setHoveredPoint(p)}
                onMouseLeave={() => setHoveredPoint(null)}
                onFocus={() => setHoveredPoint(p)}
                onBlur={() => setHoveredPoint(null)}
                onClick={() => onSelectObsId && onSelectObsId(p.obs_id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    onSelectObsId && onSelectObsId(p.obs_id);
                  }
                }}
              >
                <circle
                  cx={xCoords[i]}
                  cy={yCoords[i]}
                  r={isSelected ? 5.5 : isHovered ? 4.5 : 3.5}
                  fill={isSelected ? '#38bdf8' : is_variable ? '#fbbf24' : '#22d3ee'}
                  stroke="#0f172a"
                  strokeWidth="1.5"
                />
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip */}
        {hoveredPoint && (
          <div className="absolute top-1 right-2 bg-slate-900 border border-slate-700 rounded p-1.5 text-[10px] text-slate-200 pointer-events-none shadow-lg z-10 font-mono">
            <div><span className="text-cyan-400">Obs:</span> {hoveredPoint.obs_id}</div>
            <div><span className="text-slate-400">Date:</span> {hoveredPoint.utc_date?.slice(0, 10) || 'N/A'}</div>
            <div><span className="text-slate-400">Net:</span> {hoveredPoint.net_flux_mjy_sr.toFixed(2)} MJy/sr</div>
            <div><span className="text-slate-400">Band:</span> {hoveredPoint.detector}</div>
          </div>
        )}
      </div>

      {/* Accessible Tabular Data View (USWDS & WCAG 2.2 compliant) */}
      <details className="text-[10px] font-mono group border border-slate-800 rounded bg-slate-950/70 p-2">
        <summary className="cursor-pointer text-slate-300 hover:text-cyan-300 font-sans font-medium flex items-center justify-between select-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded px-1 py-0.5 outline-none">
          <span className="flex items-center gap-1.5">
            <Table className="w-3.5 h-3.5 text-cyan-400" />
            <span>View Accessible Data Table</span>
          </span>
          <span className="text-[9px] text-slate-400 font-mono">({points.length} epochs)</span>
        </summary>
        <div className="mt-2 overflow-x-auto max-h-48 overflow-y-auto">
          <table className="w-full text-left border-collapse" role="table" aria-label="SPHEREx Photometric Light Curve Multi-Epoch Time Series">
            <caption className="sr-only">SPHEREx Multi-epoch photometric aperture fluxes and timestamps</caption>
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 text-[9px] uppercase tracking-wider">
                <th scope="col" className="py-1 px-1.5 font-semibold">Obs ID</th>
                <th scope="col" className="py-1 px-1.5 font-semibold">Date (UTC)</th>
                <th scope="col" className="py-1 px-1.5 font-semibold">Band</th>
                <th scope="col" className="py-1 px-1.5 font-semibold text-right">Net Flux (MJy/sr)</th>
                <th scope="col" className="py-1 px-1.5 font-semibold text-right">SNR</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {points.map((p, i) => (
                <tr
                  key={p.obs_id + i}
                  className={`hover:bg-slate-900/60 transition cursor-pointer ${selectedObsId === p.obs_id ? 'bg-cyan-950/50 text-cyan-200' : ''}`}
                  onClick={() => onSelectObsId && onSelectObsId(p.obs_id)}
                >
                  <td className="py-1 px-1.5 font-semibold text-cyan-300 font-mono">
                    <button
                      type="button"
                      className="text-left font-semibold text-cyan-300 hover:text-cyan-200 hover:underline focus-visible:ring-2 focus-visible:ring-cyan-400 rounded outline-none"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectObsId && onSelectObsId(p.obs_id);
                      }}
                      aria-label={`Select observation ${p.obs_id}, date ${p.utc_date?.slice(0, 10) || 'N/A'}`}
                    >
                      {p.obs_id}
                    </button>
                  </td>
                  <td className="py-1 px-1.5 text-slate-300 font-mono">{p.utc_date?.slice(0, 10) || 'N/A'}</td>
                  <td className="py-1 px-1.5 text-indigo-300 font-mono">{p.detector}</td>
                  <td className="py-1 px-1.5 text-right font-medium text-slate-100 font-mono">{p.net_flux_mjy_sr.toFixed(2)}</td>
                  <td className="py-1 px-1.5 text-right text-cyan-300 font-mono font-semibold">{p.snr.toFixed(1)}σ</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      {/* Summary Metrics */}
      <div className="grid grid-cols-3 gap-1.5 pt-1 text-center font-mono">
        <div className="bg-slate-900/60 p-1.5 rounded border border-slate-800">
          <span className="text-[9px] text-slate-400 block">Mean Flux</span>
          <span className="text-[11px] text-slate-200">{mean_flux_mjy_sr.toFixed(2)}</span>
        </div>
        <div className="bg-slate-900/60 p-1.5 rounded border border-slate-800">
          <span className="text-[9px] text-slate-400 block">Delta (ΔF)</span>
          <span className="text-[11px] text-cyan-400 font-semibold">{amplitude_delta_mjy_sr.toFixed(2)}</span>
        </div>
        <div className="bg-slate-900/60 p-1.5 rounded border border-slate-800">
          <span className="text-[9px] text-slate-400 block">Peak Max</span>
          <span className="text-[11px] text-amber-400 font-semibold">{max_flux_mjy_sr.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
};
