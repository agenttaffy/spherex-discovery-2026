import React, { useState } from 'react';
import { SpectrumResponse, SpectrumBandPoint, SpectralChannel } from '../../types/astronomy';
import { Sparkles, Layers, Eye } from 'lucide-react';

interface SpectrumChartProps {
  spectrum: SpectrumResponse | null;
  loading?: boolean;
}

export const SpectrumChart: React.FC<SpectrumChartProps> = ({
  spectrum,
  loading = false,
}) => {
  const [showChannels102, setShowChannels102] = useState(false);
  const [selectedDetector, setSelectedDetector] = useState<string | null>(null);
  const [hoveredBand, setHoveredBand] = useState<SpectrumBandPoint | null>(null);
  const [hoveredChannel, setHoveredChannel] = useState<SpectralChannel | null>(null);

  if (loading) {
    return (
      <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 flex flex-col items-center justify-center h-52 text-slate-400">
        <Sparkles className="w-6 h-6 animate-pulse text-indigo-400 mb-2" />
        <span className="text-xs font-mono">Extracting on-the-fly SED across 6 detectors...</span>
      </div>
    );
  }

  if (!spectrum || !spectrum.bands || spectrum.bands.length === 0) {
    return (
      <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 flex flex-col items-center justify-center h-48 text-slate-500 text-xs text-center">
        <Layers className="w-6 h-6 opacity-40 mb-2 text-indigo-400" />
        <p>No multi-band spectral coverage available for this coordinate pointing.</p>
      </div>
    );
  }

  const { bands, channels_102, continuum_curve, summary, total_observed_bands } = spectrum;

  // SVG Geometry
  const width = 280;
  const height = 120;
  const padLeft = 32;
  const padRight = 14;
  const padTop = 14;
  const padBottom = 22;

  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  // Wavelength axis: 0.70 to 5.10 µm
  const waveMin = 0.70;
  const waveMax = 5.10;
  const waveRange = waveMax - waveMin;

  const getX = (w: number) => {
    const norm = (w - waveMin) / waveRange;
    return padLeft + norm * plotW;
  };

  // Flux axis
  const allFluxes = bands.map((b) => b.flux_mjy_sr);
  const maxFlux = Math.max(...allFluxes, 1.0);
  const minFlux = Math.min(0.0, Math.min(...allFluxes));
  const yRange = Math.max(1e-4, maxFlux * 1.15 - minFlux);

  const getY = (f: number) => {
    const norm = (f - minFlux) / yRange;
    return padTop + plotH - norm * plotH;
  };

  // Detector Array Wavelength Boundaries for background shading
  const detectorBands = [
    { name: 'D1', min: 0.75, max: 1.12, color: '#06b6d4' },
    { name: 'D2', min: 1.12, max: 1.68, color: '#10b981' },
    { name: 'D3', min: 1.68, max: 2.42, color: '#f59e0b' },
    { name: 'D4', min: 2.42, max: 3.82, color: '#f97316' },
    { name: 'D5', min: 3.82, max: 4.42, color: '#ef4444' },
    { name: 'D6', min: 4.42, max: 5.00, color: '#8b5cf6' },
  ];

  // Smooth continuum polyline path
  const continuumPolyPoints = continuum_curve
    .map((c) => `${getX(c.wavelength_um).toFixed(1)},${getY(c.flux_mjy_sr).toFixed(1)}`)
    .join(' ');

  return (
    <div className="bg-slate-950/90 border border-slate-800 rounded-lg p-3 space-y-2.5">
      {/* Header with 102 channels toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-indigo-400" />
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-300 block">
              Infrared SED (Flux vs. λ)
            </span>
            <span className="text-[9px] font-mono text-slate-500">
              Observed Bands ({total_observed_bands}) · Continuum (Interpolated)
            </span>
          </div>
        </div>
        <button
          onClick={() => setShowChannels102(!showChannels102)}
          className={`flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded border transition ${
            showChannels102
              ? 'bg-indigo-950 text-indigo-300 border-indigo-700 font-semibold'
              : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
          }`}
          title="Toggle display of Estimated Continuum Model (102 Interpolated Channels)"
        >
          <Eye className="w-3 h-3 text-indigo-400" />
          <span>{showChannels102 ? 'Estimated (102 Ch)' : 'Observed Bands'}</span>
        </button>
      </div>

      {/* Detector Array Quick Filter Pills */}
      <div className="flex items-center justify-between gap-1 text-[9px] font-mono">
        {detectorBands.map((db) => {
          const fullName = `SPHEREx-${db.name}`;
          const isSel = selectedDetector === fullName;
          return (
            <button
              key={db.name}
              onClick={() => setSelectedDetector(isSel ? null : fullName)}
              className={`flex-1 py-0.5 rounded text-center transition border ${
                isSel
                  ? 'font-bold border-white/60 shadow-sm'
                  : 'opacity-70 hover:opacity-100 border-slate-800 bg-slate-950/60'
              }`}
              style={{
                color: db.color,
                borderColor: isSel ? db.color : undefined,
                backgroundColor: isSel ? `${db.color}22` : undefined,
              }}
              title={`Filter ${fullName} (${db.min}–${db.max} µm)`}
            >
              {db.name}
            </button>
          );
        })}
      </div>

      {/* SVG Spectrum Plot */}
      <div className="relative">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-32 bg-slate-900/60 rounded border border-slate-800 select-none overflow-hidden"
        >
          {/* Detector Range Color Bands Background */}
          {detectorBands.map((db) => {
            const x1 = getX(db.min);
            const x2 = getX(db.max);
            return (
              <g key={db.name}>
                <rect
                  x={x1}
                  y={padTop}
                  width={x2 - x1}
                  height={plotH}
                  fill={db.color}
                  fillOpacity="0.08"
                />
                <text
                  x={(x1 + x2) / 2}
                  y={padTop + 8}
                  fill={db.color}
                  fontSize="7"
                  textAnchor="middle"
                  fontFamily="monospace"
                  opacity="0.8"
                  fontWeight="bold"
                >
                  {db.name}
                </text>
              </g>
            );
          })}

          {/* Gridlines */}
          <line x1={padLeft} y1={padTop} x2={width - padRight} y2={padTop} stroke="#334155" strokeDasharray="2,2" strokeWidth="0.7" />
          <line x1={padLeft} y1={padTop + plotH} x2={width - padRight} y2={padTop + plotH} stroke="#334155" strokeWidth="1" />
          <line x1={padLeft} y1={padTop} x2={padLeft} y2={padTop + plotH} stroke="#334155" strokeWidth="1" />

          {/* Wavelength Grid Ticks & Labels */}
          {[1.0, 2.0, 3.0, 4.0, 5.0].map((w) => {
            const x = getX(w);
            return (
              <g key={w}>
                <line x1={x} y1={padTop + plotH} x2={x} y2={padTop + plotH + 3} stroke="#64748b" strokeWidth="1" />
                <text x={x} y={padTop + plotH + 11} fill="#64748b" fontSize="7.5" textAnchor="middle" fontFamily="monospace">
                  {w}µm
                </text>
              </g>
            );
          })}

          {/* Y Axis Labels (MJy/sr) */}
          <text x={padLeft - 4} y={padTop + 4} fill="#64748b" fontSize="7.5" textAnchor="end" fontFamily="monospace">
            {maxFlux.toFixed(1)}
          </text>
          <text x={padLeft - 4} y={padTop + plotH} fill="#64748b" fontSize="7.5" textAnchor="end" fontFamily="monospace">
            0.0
          </text>

          {/* Smooth Modeled Continuum Curve */}
          {continuum_curve.length > 1 && (
            <polyline
              points={continuumPolyPoints}
              fill="none"
              stroke="#818cf8"
              strokeWidth="1.8"
              strokeLinejoin="round"
              strokeOpacity="0.8"
            />
          )}

          {/* 102 Individual Channel Bars/Dots if toggled */}
          {showChannels102 &&
            channels_102.map((ch) => {
              const cx = getX(ch.wavelength_um);
              const cy = getY(ch.flux_mjy_sr);
              const isHov = hoveredChannel?.channel_index === ch.channel_index;
              const isDimmed = selectedDetector && ch.detector !== selectedDetector;
              return (
                <g
                  key={ch.channel_index}
                  className="cursor-pointer"
                  onMouseEnter={() => {
                    setHoveredChannel(ch);
                    setHoveredBand(null);
                  }}
                  onMouseLeave={() => setHoveredChannel(null)}
                >
                  <circle cx={cx} cy={cy} r={6} fill="transparent" />
                  <circle
                    cx={cx}
                    cy={cy}
                    r={isHov ? 3.0 : 1.3}
                    fill={ch.color}
                    opacity={isDimmed ? 0.2 : isHov ? 1.0 : 0.75}
                    pointerEvents="none"
                  />
                </g>
              );
            })}

          {/* 6 SPHEREx Detector Band Data Points with Error Bars */}
          {bands.map((b) => {
            const cx = getX(b.wavelength_um);
            const cy = getY(b.flux_mjy_sr);
            const cyErrTop = getY(Math.min(maxFlux * 1.15, b.flux_mjy_sr + b.flux_err_mjy_sr));
            const cyErrBot = getY(Math.max(0, b.flux_mjy_sr - b.flux_err_mjy_sr));
            const isHovered = hoveredBand?.detector === b.detector;
            const isDimmed = selectedDetector && b.detector !== selectedDetector;

            return (
              <g
                key={b.detector}
                className="cursor-pointer"
                opacity={isDimmed ? 0.3 : 1.0}
                onMouseEnter={() => {
                  setHoveredBand(b);
                  setHoveredChannel(null);
                }}
                onMouseLeave={() => setHoveredBand(null)}
                onClick={() => setSelectedDetector(selectedDetector === b.detector ? null : b.detector)}
              >
                {/* Photometric Error Bar */}
                <line
                  x1={cx}
                  y1={cyErrTop}
                  x2={cx}
                  y2={cyErrBot}
                  stroke={b.color}
                  strokeWidth="1.2"
                  opacity="0.8"
                />
                <line
                  x1={cx - 2.5}
                  y1={cyErrTop}
                  x2={cx + 2.5}
                  y2={cyErrTop}
                  stroke={b.color}
                  strokeWidth="1.2"
                  opacity="0.8"
                />
                <line
                  x1={cx - 2.5}
                  y1={cyErrBot}
                  x2={cx + 2.5}
                  y2={cyErrBot}
                  stroke={b.color}
                  strokeWidth="1.2"
                  opacity="0.8"
                />

                {/* Outer ring for observed archive FITS */}
                {b.is_observed && (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={isHovered ? 7.5 : 5.8}
                    fill="none"
                    stroke="#ffffff"
                    strokeWidth="1.2"
                    strokeDasharray="2,2"
                  />
                )}

                {/* Central Photometry Node */}
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 5.5 : 4.0}
                  fill={b.color}
                  stroke="#0f172a"
                  strokeWidth="1.5"
                />
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip: 6 Bands */}
        {hoveredBand && (
          <div className="absolute top-1 right-2 bg-slate-900 border border-slate-700 rounded p-2 text-[10px] text-slate-200 pointer-events-none shadow-xl z-20 font-mono space-y-0.5">
            <div className="flex items-center gap-1.5 font-bold" style={{ color: hoveredBand.color }}>
              <span>{hoveredBand.detector}</span>
              <span className="text-[9px] text-slate-400">({hoveredBand.wavelength_min_um}–{hoveredBand.wavelength_max_um} µm)</span>
            </div>
            <div>
              <span className="text-slate-400">λ_eff:</span> {hoveredBand.wavelength_um.toFixed(3)} µm
              {hoveredBand.calibration_source ? (
                <span className="text-slate-400 text-[8.5px] ml-1">({hoveredBand.calibration_source})</span>
              ) : null}
            </div>
            <div>
              <span className="text-slate-400">Flux:</span> {hoveredBand.flux_mjy_sr.toFixed(2)} MJy/sr ({hoveredBand.flux_density_mjy.toFixed(2)} mJy)
            </div>
            <div>
              <span className="text-slate-400">SNR:</span> {hoveredBand.snr}σ (±{hoveredBand.flux_err_mjy_sr.toFixed(2)})
            </div>
            <div className="pt-0.5 text-[9px]">
              {hoveredBand.is_observed ? (
                <span className="text-emerald-400 font-semibold">
                  ✓ Observed SPHEREx Detector Band (Calibrated WCS)
                </span>
              ) : (
                <span className="text-amber-300">○ Modeled SED Profile Continuum</span>
              )}
            </div>
          </div>
        )}

        {/* Hover Tooltip: 102 Individual Channels */}
        {hoveredChannel && (
          <div className="absolute top-1 right-2 bg-slate-900 border border-slate-700 rounded p-2 text-[10px] text-slate-200 pointer-events-none shadow-xl z-20 font-mono space-y-0.5">
            <div className="text-[9px] text-indigo-400 font-bold uppercase tracking-wider">
              Estimated Continuum Model (Interpolated)
            </div>
            <div className="flex items-center gap-1.5 font-bold" style={{ color: hoveredChannel.color }}>
              <span>Estimated Channel #{hoveredChannel.channel_index} / 102</span>
              <span className="text-[9px] text-slate-400">({hoveredChannel.detector})</span>
            </div>
            <div>
              <span className="text-slate-400">Wavelength λ:</span> {hoveredChannel.wavelength_um.toFixed(4)} µm
            </div>
            <div>
              <span className="text-slate-400">Estimated Flux:</span> {hoveredChannel.flux_mjy_sr.toFixed(2)} MJy/sr (Interpolated)
            </div>
          </div>
        )}
      </div>

      {/* Spectral Classification & Summary Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded p-2 space-y-1.5 font-mono">
        <div className="flex items-center justify-between text-[10px]">
          <span className="text-slate-400">Classification:</span>
          <span className="text-indigo-300 font-semibold text-right truncate max-w-[170px]" title={summary.spectral_class}>
            {summary.spectral_class}
          </span>
        </div>
        <div className="grid grid-cols-3 gap-1 pt-1 text-center">
          <div className="bg-slate-950/60 p-1 rounded border border-slate-800/80">
            <span className="text-[9px] text-slate-500 block">Peak λ</span>
            <span className="text-[11px] text-amber-400 font-bold">{summary.peak_wavelength_um.toFixed(2)} µm</span>
          </div>
          <div className="bg-slate-950/60 p-1 rounded border border-slate-800/80">
            <span className="text-[9px] text-slate-500 block">Peak Band</span>
            <span className="text-[11px] text-cyan-300 font-bold">{summary.peak_detector.replace('SPHEREx-', '')}</span>
          </div>
          <div className="bg-slate-950/60 p-1 rounded border border-slate-800/80">
            <span className="text-[9px] text-slate-500 block">Observed</span>
            <span className="text-[11px] text-emerald-400 font-bold">{total_observed_bands} / 6</span>
          </div>
        </div>
      </div>
    </div>
  );
};
