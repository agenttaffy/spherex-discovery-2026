import React, { useState, useEffect } from 'react';
import { ObservationRecord, DiffResult, FrameResponse, AstrometricMotion } from '../../types/astronomy';
import { computeDiff, fetchFrame, computeMotion } from '../../services/api';
import { ArrowRight, Sparkles, Loader2, AlertCircle, Move } from 'lucide-react';

interface ComparisonViewProps {
  observations: ObservationRecord[];
}

export const ComparisonView: React.FC<ComparisonViewProps> = ({ observations }) => {
  const [index1, setIndex1] = useState(0);
  const [index2, setIndex2] = useState(1);
  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);
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

  // Compute differential image and astrometric motion
  useEffect(() => {
    if (observations.length < 2 || !obs1 || !obs2) return;
    if (obs1.id === obs2.id) {
      setDiffResult(null);
      setMotionResult(null);
      setError('Please select two different epochs for temporal differencing.');
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

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

    return () => {
      active = false;
    };
  }, [obs1?.id, obs2?.id, observations.length]);

  if (observations.length < 2) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
        <Sparkles className="w-12 h-12 text-cyan-500/40 mb-3" />
        <h3 className="text-base font-semibold text-slate-200">Insufficient Epochs</h3>
        <p className="text-xs text-slate-400 max-w-md mt-1">
          Astronomical differencing requires at least two epochs from the same or compatible detector band.
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
    <div className="flex-1 flex flex-col p-6 bg-slate-950 overflow-y-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <span>Differential Image Analysis (I₂ − I₁)</span>
            {deltaDays !== null && (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/60">
                Δt = {deltaDays.toFixed(1)} days ({(deltaDays / 365.25).toFixed(2)} yrs)
              </span>
            )}
          </h2>
          <p className="text-xs text-slate-400">
            Sub-pixel scientific differencing to isolate astrometric movement and photometric transients.
          </p>
        </div>

        {/* Epoch Selectors */}
        <div className="flex items-center space-x-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-500">Epoch 1 (I₁):</span>
            <select
              value={safeIndex1}
              onChange={(e) => setIndex1(Number(e.target.value))}
              className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-slate-200 font-mono text-xs focus:outline-none focus:border-cyan-500"
            >
              {observations.map((o, idx) => (
                <option key={o.id} value={idx}>
                  {idx + 1}. {o.utc_date?.split('T')[0]} ({o.detector})
                </option>
              ))}
            </select>
          </div>

          <ArrowRight className="w-4 h-4 text-slate-600" />

          <div className="flex items-center gap-2">
            <span className="text-slate-500">Epoch 2 (I₂):</span>
            <select
              value={safeIndex2}
              onChange={(e) => setIndex2(Number(e.target.value))}
              className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-slate-200 font-mono text-xs focus:outline-none focus:border-cyan-500"
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
          <span className="text-xs font-mono">Computing calibrated differential frame & astrometric vectors...</span>
        </div>
      )}

      {!loading && diffResult && (
        <div className="mt-6 flex flex-col gap-6 flex-1">
          {/* Side-by-Side Comparison: Epoch 1, Epoch 2, Difference */}
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

            {/* Calibrated Difference Frame */}
            <div className="bg-slate-900/60 border border-cyan-800/40 rounded-xl p-3 flex flex-col items-center shadow-lg shadow-cyan-950/20">
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
                {motionResult && motionResult.displacement_pixels > 0.4 && (
                  <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                    <svg className="w-full h-full" viewBox="-20 -20 40 40">
                      <line
                        x1={-motionResult.dx_pixels * 5}
                        y1={-motionResult.dy_pixels * 5}
                        x2={motionResult.dx_pixels * 5}
                        y2={motionResult.dy_pixels * 5}
                        stroke="#38bdf8"
                        strokeWidth="1.5"
                        strokeDasharray="2,2"
                      />
                      <circle cx={-motionResult.dx_pixels * 5} cy={-motionResult.dy_pixels * 5} r="2" fill="#f43f5e" />
                      <circle cx={motionResult.dx_pixels * 5} cy={motionResult.dy_pixels * 5} r="2" fill="#10b981" />
                    </svg>
                  </div>
                )}
              </div>
              <span className="text-[10px] text-slate-400 font-mono mt-2">
                {motionResult?.displacement_pixels ? `Displacement: ${motionResult.displacement_pixels} px` : 'Mid-gray = 0 residual'}
              </span>
            </div>
          </div>

          {/* Astrometric Motion Detection Card */}
          {motionResult && (
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

          {/* Differential Metrics Dock */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Differential Photometric & Astrometric Metrics
            </h4>
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
              <p className="font-semibold">Interpretation:</p>
              <p className="text-slate-400">
                Mid-gray (128) denotes zero net brightness change between epochs. Red marker indicates Epoch 1 point source centroid, green indicates Epoch 2 centroid. Bright white spots represent newly brightened or incoming sources, while dark regions indicate dimmed or departed sources.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
