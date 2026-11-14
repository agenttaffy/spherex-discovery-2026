import React, { useState, useEffect } from 'react';
import { ObservationRecord, DiffResult, FrameResponse, AstrometricMotion, StackResult } from '../../types/astronomy';
import { computeDiff, fetchFrame, computeMotion, stackFrames } from '../../services/api';
import { ArrowRight, Sparkles, Loader2, AlertCircle, Move, Layers, Plus, Minus, TrendingUp } from 'lucide-react';

interface ComparisonViewProps {
  observations: ObservationRecord[];
}

export const ComparisonView: React.FC<ComparisonViewProps> = ({ observations }) => {
  const [index1, setIndex1] = useState(0);
  const [index2, setIndex2] = useState(1);
  const [opMode, setOpMode] = useState<'diff' | 'stack'>('diff');
  const [stackMethod, setStackMethod] = useState<'mean' | 'median' | 'sum'>('mean');
  const [stackScope, setStackScope] = useState<'pair' | 'all'>('pair');

  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);
  const [stackResult, setStackResult] = useState<StackResult | null>(null);
  const [motionResult, setMotionResult] = useState<AstrometricMotion | null>(null);
  const [frame1, setFrame1] = useState<FrameResponse | null>(null);
  const [frame2, setFrame2] = useState<FrameResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Safely clamp indices to current observations array
  const safeIndex1 = Math.min(Math.max(0, index1), Math.max(0, observations.length - 1));
  const safeIndex2 = Math.min(Math.max(0, index2), Math.max(0, observations.length - 1));

  const obs1 = observations[safeIndex1];
  const obs2 = observations[safeIndex2];

  // Load preview thumbnails for both epochs
  useEffect(() => {
    if (obs1) {
      fetchFrame(obs1.id, 'asinh', 0.04)
        .then(setFrame1)
        .catch(() => setFrame1(null));
    }
  }, [obs1?.id]);

  useEffect(() => {
    if (obs2) {
      fetchFrame(obs2.id, 'asinh', 0.04)
        .then(setFrame2)
        .catch(() => setFrame2(null));
    }
  }, [obs2?.id]);

  // Compute differential image or co-addition stack
  useEffect(() => {
    if (observations.length < 2 || !obs1 || !obs2) return;

    if (opMode === 'diff' && obs1.id === obs2.id) {
      setDiffResult(null);
      setStackResult(null);
      setMotionResult(null);
      setError('Please select two different epochs for comparison differencing.');
      return;
    }

    if (opMode === 'stack' && stackScope === 'pair' && obs1.id === obs2.id) {
      setDiffResult(null);
      setStackResult(null);
      setMotionResult(null);
      setError('Please select two different epochs for pairwise co-addition.');
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    if (opMode === 'diff') {
      Promise.all([
        computeDiff(obs1.id, obs2.id),
        computeMotion(obs1.id, obs2.id).catch(() => null),
      ])
        .then(([diff, motion]) => {
          if (active) {
            setDiffResult(diff);
            if (motion) setMotionResult(motion.motion);
          }
        })
        .catch((err) => {
          if (active) setError(err.message);
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    } else {
      // Co-Add Stacking Mode
      const idsToStack =
        stackScope === 'all'
          ? Array.from(new Set(observations.map((o) => o.id)))
          : [obs1.id, obs2.id];

      stackFrames(idsToStack, stackMethod)
        .then((res) => {
          if (active) setStackResult(res);
        })
        .catch((err) => {
          if (active) setError(err.message);
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }

    return () => {
      active = false;
    };
  }, [obs1?.id, obs2?.id, observations, opMode, stackMethod, stackScope]);

  if (observations.length < 2) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
        <Sparkles className="w-12 h-12 text-cyan-500/40 mb-3" />
        <h3 className="text-base font-semibold text-slate-200">Insufficient Epochs</h3>
        <p className="text-xs text-slate-400 max-w-md mt-1">
          Astronomical comparison requires at least two epochs from the same or compatible detector band.
        </p>
      </div>
    );
  }

  // Calculate baseline delta days if MJD available
  let deltaDays: number | null = null;
  if (obs1?.mjd && obs2?.mjd) {
    deltaDays = Math.abs(obs2.mjd - obs1.mjd);
  }

  return (
    <div className="flex-1 flex flex-col p-3 sm:p-6 bg-slate-950 overflow-y-auto max-w-full">
      {/* Top Header & Mode Switcher */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-4 border-b border-slate-800 gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-base font-bold text-slate-100 flex flex-wrap items-center gap-2">
              {opMode === 'diff' ? (
                <span>Differential Image Analysis (I₂ − I₁)</span>
              ) : (
                <span>Astronomical Image Co-Addition & Stacking (I₁ + I₂)</span>
              )}
              {deltaDays !== null && (
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/60 font-normal">
                  Δt = {deltaDays.toFixed(1)}d ({(deltaDays / 365.25).toFixed(2)}y)
                </span>
              )}
            </h2>

            {/* Mode Switcher Tabs */}
            <div role="tablist" aria-label="Comparison operation mode" className="flex bg-slate-900 border border-slate-800 rounded-lg p-0.5 text-xs font-mono">
              <button
                role="tab"
                aria-selected={opMode === 'diff'}
                aria-label="Differential Image Mode"
                onClick={() => setOpMode('diff')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                  opMode === 'diff'
                    ? 'bg-amber-500/20 text-amber-200 border border-amber-500/40 font-semibold'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                <Minus className="w-3.5 h-3.5 text-amber-400" />
                <span>Difference (I₂ − I₁)</span>
              </button>
              <button
                role="tab"
                aria-selected={opMode === 'stack'}
                aria-label="Co-Addition Stacking Mode"
                onClick={() => setOpMode('stack')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                  opMode === 'stack'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                <Plus className="w-3.5 h-3.5 text-cyan-400" />
                <span>Co-Add Stack (I₁ + I₂)</span>
              </button>
            </div>
          </div>

          <p className="text-xs text-slate-300 mt-1">
            {opMode === 'diff'
              ? 'Sub-pixel scientific differencing to isolate astrometric movement, high proper motion dipoles, and transients.'
              : 'WCS-aligned co-addition to suppress uncorrelated read noise and sky background, unveiling faint static sources.'}
          </p>
        </div>

        {/* Epoch & Stacking Selectors */}
        <div className="flex items-center flex-wrap gap-3 text-xs" role="toolbar" aria-label="Epoch comparison and co-addition settings">
          {opMode === 'stack' && (
            <>
              <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded px-2 py-1">
                <span className="text-slate-300 text-[11px] font-medium">Scope:</span>
                <select
                  value={stackScope}
                  aria-label="Co-addition stacking scope"
                  onChange={(e) => setStackScope(e.target.value as 'pair' | 'all')}
                  className="bg-transparent text-cyan-300 font-mono text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                >
                  <option value="pair" className="bg-slate-900 text-slate-200">Selected Pair (2)</option>
                  <option value="all" className="bg-slate-900 text-slate-200">All Epochs ({observations.length})</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded px-2 py-1">
                <span className="text-slate-300 text-[11px] font-medium">Method:</span>
                <select
                  value={stackMethod}
                  aria-label="Co-addition stacking statistical algorithm"
                  onChange={(e) => setStackMethod(e.target.value as any)}
                  className="bg-transparent text-cyan-300 font-mono text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                >
                  <option value="mean" className="bg-slate-900 text-slate-200">Mean (Max SNR)</option>
                  <option value="median" className="bg-slate-900 text-slate-200">Median (Reject Outliers)</option>
                  <option value="sum" className="bg-slate-900 text-slate-200">Sum (Total Counts)</option>
                </select>
              </div>
            </>
          )}

          <div className="flex items-center gap-2">
            <label htmlFor="epoch1-select" className="text-slate-300 font-medium">Epoch 1:</label>
            <select
              id="epoch1-select"
              value={safeIndex1}
              aria-label="Select first epoch for comparison"
              onChange={(e) => setIndex1(Number(e.target.value))}
              className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-slate-200 font-mono text-xs focus:outline-none focus:border-cyan-500 focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              {observations.map((o, idx) => (
                <option key={o.id} value={idx}>
                  {idx + 1}. {o.utc_date?.split('T')[0]} ({o.detector})
                </option>
              ))}
            </select>
          </div>

          <ArrowRight className="w-4 h-4 text-slate-500 hidden sm:block" />

          <div className="flex items-center gap-2">
            <label htmlFor="epoch2-select" className="text-slate-300 font-medium">Epoch 2:</label>
            <select
              id="epoch2-select"
              value={safeIndex2}
              aria-label="Select second epoch for comparison"
              onChange={(e) => setIndex2(Number(e.target.value))}
              className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-slate-200 font-mono text-xs focus:outline-none focus:border-cyan-500 focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              {observations.map((o, idx) => (
                <option key={o.id} value={idx}>
                  {idx + 1}. {o.utc_date?.split('T')[0]} ({o.detector})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="mt-4 p-3 bg-amber-950/40 border border-amber-800/60 rounded-lg text-xs text-amber-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-amber-400" />
          <span>{error}</span>
        </div>
      )}

      {loading && (
        <div className="flex-1 flex flex-col items-center justify-center p-12 text-cyan-400 gap-2">
          <Loader2 className="w-8 h-8 animate-spin" />
          <span className="text-xs font-mono">
            {opMode === 'diff'
              ? 'Computing calibrated differential frame & astrometric vectors...'
              : 'Registering celestial WCS grids & computing co-add stack...'}
          </span>
        </div>
      )}

      {/* Main Analysis Display */}
      {!loading && (opMode === 'diff' ? diffResult : stackResult) && (
        <div className="mt-6 flex flex-col gap-6 flex-1">
          {/* Side-by-Side Comparison: Epoch 1, Epoch 2, [Difference | Co-Add] */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Epoch 1 Thumbnail */}
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-3 flex flex-col items-center">
              <div className="w-full flex items-center justify-between text-[11px] font-mono text-slate-400 mb-2">
                <span className="text-cyan-400 font-semibold">Epoch 1 (I₁)</span>
                <span>{obs1?.utc_date?.split('T')[0]}</span>
              </div>
              <div className="w-full aspect-square bg-black rounded-lg border border-slate-800 overflow-hidden flex items-center justify-center">
                {frame1 ? (
                  <img
                    src={frame1.image_base64}
                    alt="Epoch 1"
                    className="w-full h-full object-contain [image-rendering:pixelated]"
                  />
                ) : (
                  <span className="text-xs text-slate-600 font-mono">Loading...</span>
                )}
              </div>
              <span className="text-[10px] text-slate-500 font-mono mt-2">{obs1?.detector}</span>
            </div>

            {/* Epoch 2 Thumbnail */}
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-3 flex flex-col items-center">
              <div className="w-full flex items-center justify-between text-[11px] font-mono text-slate-400 mb-2">
                <span className="text-indigo-400 font-semibold">Epoch 2 (I₂)</span>
                <span>{obs2?.utc_date?.split('T')[0]}</span>
              </div>
              <div className="w-full aspect-square bg-black rounded-lg border border-slate-800 overflow-hidden flex items-center justify-center">
                {frame2 ? (
                  <img
                    src={frame2.image_base64}
                    alt="Epoch 2"
                    className="w-full h-full object-contain [image-rendering:pixelated]"
                  />
                ) : (
                  <span className="text-xs text-slate-600 font-mono">Loading...</span>
                )}
              </div>
              <span className="text-[10px] text-slate-500 font-mono mt-2">{obs2?.detector}</span>
            </div>

            {/* Third Card: Difference or Co-Add Stack */}
            {opMode === 'diff' && diffResult ? (
              <div className="bg-slate-900/60 border border-amber-800/40 rounded-xl p-3 flex flex-col items-center shadow-lg shadow-amber-950/20">
                <div className="w-full flex items-center justify-between text-[11px] font-mono mb-2">
                  <span className="text-amber-300 font-semibold">Difference (I₂ − I₁)</span>
                  <span className="text-slate-400">RMS: {diffResult.diff_stats.rms_diff_mjy_sr}</span>
                </div>
                <div className="w-full aspect-square bg-black rounded-lg border border-slate-700 overflow-hidden flex items-center justify-center relative">
                  <img
                    src={diffResult.image_base64}
                    alt="Difference Frame"
                    className="w-full h-full object-contain [image-rendering:pixelated]"
                  />
                  {/* Visual Dipole Vector Overlay */}
                  {motionResult && motionResult.displacement_pixels >= 0.1 && (
                    <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                      {(() => {
                        const imgW = diffResult.dimensions?.[1] || 20;
                        const imgH = diffResult.dimensions?.[0] || 20;
                        const hasCentroids = motionResult.centroid_1 && motionResult.centroid_2;
                        const x1 = hasCentroids ? motionResult.centroid_1![0] : imgW / 2 - motionResult.dx_pixels / 2;
                        const y1 = hasCentroids ? motionResult.centroid_1![1] : imgH / 2 - motionResult.dy_pixels / 2;
                        const x2 = hasCentroids ? motionResult.centroid_2![0] : imgW / 2 + motionResult.dx_pixels / 2;
                        const y2 = hasCentroids ? motionResult.centroid_2![1] : imgH / 2 + motionResult.dy_pixels / 2;

                        return (
                          <svg className="w-full h-full" viewBox={`0 0 ${imgW} ${imgH}`}>
                            <line
                              x1={x1}
                              y1={y1}
                              x2={x2}
                              y2={y2}
                              stroke="#38bdf8"
                              strokeWidth="0.7"
                              strokeDasharray="1,1"
                            />
                            <circle cx={x1} cy={y1} r="0.7" fill="#f43f5e" />
                            <circle cx={x2} cy={y2} r="0.7" fill="#10b981" />
                          </svg>
                        );
                      })()}
                    </div>
                  )}
                </div>
                <span className="text-[10px] text-slate-400 font-mono mt-2">
                  {motionResult?.displacement_pixels ? `Displacement: ${motionResult.displacement_pixels} px` : 'Mid-gray = 0 residual'}
                </span>
              </div>
            ) : stackResult ? (
              <div className="bg-slate-900/60 border border-cyan-800/40 rounded-xl p-3 flex flex-col items-center shadow-lg shadow-cyan-950/20">
                <div className="w-full flex items-center justify-between text-[11px] font-mono mb-2">
                  <span className="text-cyan-300 font-semibold flex items-center gap-1">
                    <Layers className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Co-Add Stack ({stackResult.method.toUpperCase()})</span>
                  </span>
                  <span className="text-emerald-400 font-bold bg-emerald-950/80 px-1.5 py-0.5 rounded border border-emerald-800/60 text-[10px]">
                    +{((stackResult.snr_improvement_factor - 1) * 100).toFixed(0)}% SNR (~{stackResult.snr_improvement_factor}×)
                  </span>
                </div>
                <div className="w-full aspect-square bg-black rounded-lg border border-slate-700 overflow-hidden flex items-center justify-center relative">
                  <img
                    src={stackResult.image_base64}
                    alt="Stacked Co-Add Frame"
                    className="w-full h-full object-contain [image-rendering:pixelated]"
                  />
                </div>
                <span className="text-[10px] text-cyan-400 font-mono mt-2">
                  N={stackResult.frame_count} Co-added frames • {stackResult.dimensions.join('×')} px
                </span>
              </div>
            ) : null}
          </div>

          {/* Mode 1 Details: Astrometric Motion & Differencing */}
          {opMode === 'diff' && motionResult && (
            <div className="bg-slate-900/60 border border-indigo-900/50 rounded-xl p-5 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-indigo-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Move className="w-4 h-4 text-cyan-400" />
                  Candidate Astrometric Motion & Proper Motion Vector
                </h4>
                <span className={`text-[10px] font-semibold px-2.5 py-0.5 rounded-full border ${
                  motionResult.motion_class.includes('High')
                    ? 'bg-amber-950/80 text-amber-300 border-amber-800'
                    : 'bg-slate-800 text-slate-300 border-slate-700'
                }`}>
                  {motionResult.motion_class}
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 font-mono text-xs">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Annual Proper Motion</span>
                  <span className="text-cyan-300 font-bold text-sm">
                    {motionResult.proper_motion_arcsec_yr}″/yr
                  </span>
                  <span className="text-[9px] text-slate-500 block">({motionResult.proper_motion_mas_yr} mas/yr)</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Net Angular Shift</span>
                  <span className="text-slate-100 font-bold text-sm">{motionResult.displacement_arcsec}″</span>
                  <span className="text-[9px] text-slate-500 block">({motionResult.displacement_pixels} pixels)</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Vector (Δx, Δy)</span>
                  <span className="text-indigo-300 font-bold text-sm">
                    ({motionResult.dx_pixels}, {motionResult.dy_pixels}) px
                  </span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Position Angle (PA)</span>
                  <span className="text-amber-400 font-bold text-sm">{motionResult.position_angle_deg}°</span>
                  <span className="text-[9px] text-slate-500 block">N through E</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Detection Confidence</span>
                  <span className="text-emerald-400 font-bold text-sm">
                    {(motionResult.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>
          )}

          {opMode === 'diff' && diffResult && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Differential Photometric & Astrometric Metrics
                </h4>
                {diffResult.diff_stats.alignment_method && (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold">
                    {diffResult.diff_stats.alignment_method === 'wcs_reproject'
                      ? 'Astropy / Reproject WCS Alignment'
                      : diffResult.diff_stats.alignment_method === 'fft_shift'
                      ? '2D FFT Cross-Correlation Shift'
                      : 'Direct Pixel Alignment'}
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">RMS Difference</span>
                  <span className="text-cyan-400 font-bold text-sm">{diffResult.diff_stats.rms_diff_mjy_sr} MJy/sr</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">Peak Positive Flux</span>
                  <span className="text-emerald-400 font-bold text-sm">+{diffResult.diff_stats.peak_positive_flux} MJy/sr</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">Peak Negative Flux</span>
                  <span className="text-rose-400 font-bold text-sm">{diffResult.diff_stats.peak_negative_flux} MJy/sr</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">Noise Level (σ)</span>
                  <span className="text-slate-200 font-bold text-sm">±{diffResult.diff_stats.sigma_mjy_sr} MJy/sr</span>
                </div>
              </div>

              <div className="p-3 bg-cyan-950/20 border border-cyan-800/40 rounded-lg text-[11px] text-cyan-300 space-y-1">
                <p className="font-semibold">Differencing Interpretation:</p>
                <p className="text-slate-400">
                  Mid-gray (128) denotes zero net brightness change between epochs. Red marker indicates Epoch 1 point source centroid, green indicates Epoch 2 centroid. Bright white spots represent newly brightened or incoming sources, while dark regions indicate dimmed or departed sources.
                </p>
              </div>
            </div>
          )}

          {/* Mode 2 Details: Co-Addition & Stacking Telemetry */}
          {opMode === 'stack' && stackResult && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-cyan-300 uppercase tracking-wider flex items-center gap-1.5">
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                  Noise Suppression & Signal-to-Noise Ratio (SNR) Metrics
                </h4>
                {stackResult.alignment_method && (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold">
                    {stackResult.alignment_method === 'wcs_reproject'
                      ? 'Astropy / Reproject WCS Registration'
                      : stackResult.alignment_method === 'fft_shift'
                      ? 'FFT Sub-Pixel Registration'
                      : 'Direct Coordinate Co-Addition'}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">SNR Improvement</span>
                  <span className="text-emerald-400 font-bold text-base">
                    {stackResult.snr_improvement_factor}×
                  </span>
                  <span className="text-[10px] text-slate-500 block">(Theory: √N = {stackResult.theoretical_snr_gain}×)</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">Stacked Background Noise</span>
                  <span className="text-cyan-300 font-bold text-sm">
                    ±{stackResult.noise_stats.stacked_noise_sigma} MJy/sr
                  </span>
                  <span className="text-[10px] text-slate-500 block">Single-frame: ±{stackResult.noise_stats.reference_noise_sigma}</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">Peak Co-Add Flux</span>
                  <span className="text-amber-400 font-bold text-sm">
                    {stackResult.noise_stats.max_flux_mjy_sr} MJy/sr
                  </span>
                  <span className="text-[10px] text-slate-500 block">Mean: {stackResult.noise_stats.mean_flux_mjy_sr}</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">Co-Added Epochs</span>
                  <span className="text-slate-100 font-bold text-sm">
                    {stackResult.frame_count} Frames
                  </span>
                  <span className="text-[10px] text-indigo-300 block">Method: {stackResult.method.toUpperCase()}</span>
                </div>
              </div>

              <div className="p-3 bg-cyan-950/20 border border-cyan-800/40 rounded-lg text-[11px] text-cyan-300 space-y-1">
                <p className="font-semibold flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-cyan-400" />
                  Astronomical Co-Addition Discovery Benefit:
                </p>
                <p className="text-slate-400">
                  Co-addition of registered observation frames suppresses uncorrelated detector read noise and sky background Poisson noise by a factor of ~√N. While differencing reveals moving objects and dipoles, co-addition deepens the detection limit, bringing faint static infrared sources, cold brown dwarfs (such as WISE 0855), circumstellar dust disks, and high-redshift extragalactic sources above the detection threshold.
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
