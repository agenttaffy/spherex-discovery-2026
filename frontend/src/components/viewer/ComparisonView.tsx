import React, { useState, useEffect } from 'react';
import { ObservationRecord, DiffResult } from '../../types/astronomy';
import { computeDiff } from '../../services/api';
import { ArrowRight, Sparkles, Loader2, AlertCircle } from 'lucide-react';

interface ComparisonViewProps {
  observations: ObservationRecord[];
}

export const ComparisonView: React.FC<ComparisonViewProps> = ({ observations }) => {
  const [index1, setIndex1] = useState(0);
  const [index2, setIndex2] = useState(Math.min(1, observations.length - 1));
  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const obs1 = observations[index1];
  const obs2 = observations[index2];

  useEffect(() => {
    if (observations.length < 2 || !obs1 || !obs2) return;
    if (obs1.id === obs2.id) {
      setDiffResult(null);
      setError('Please select two different observations for temporal differencing.');
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    computeDiff(obs1.id, obs2.id)
      .then((res) => {
        if (active) setDiffResult(res);
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
  }, [obs1, obs2, observations.length]);

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

  return (
    <div className="flex-1 flex flex-col p-6 bg-slate-950 overflow-y-auto">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-base font-bold text-slate-100">Differential Image Analysis (I₂ − I₁)</h2>
          <p className="text-xs text-slate-400">Sub-pixel scientific differencing to isolate astrometric and photometric transients.</p>
        </div>

        {/* Epoch Selectors */}
        <div className="flex items-center space-x-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-500">Epoch 1:</span>
            <select
              value={index1}
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
            <span className="text-slate-500">Epoch 2:</span>
            <select
              value={index2}
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
          <span className="text-xs font-mono">Computing calibrated differential frame...</span>
        </div>
      )}

      {!loading && diffResult && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-6 flex-1 items-start">
          <div className="md:col-span-2 flex flex-col items-center justify-center bg-slate-900/40 border border-slate-800 rounded-xl p-4">
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">
              Calibrated Difference Frame (I₂ − I₁)
            </h4>
            <div className="relative border border-slate-700 rounded-lg overflow-hidden bg-black max-w-md w-full aspect-square flex items-center justify-center">
              <img
                src={diffResult.image_base64}
                alt="Difference Frame"
                className="w-full h-full object-contain [image-rendering:pixelated]"
              />
            </div>
            <p className="text-[11px] text-slate-500 mt-3 text-center max-w-sm">
              Mid-gray represents zero residual flux. Bright white spots indicate positive flux emergence (brightening/arrival); dark regions indicate flux reduction (dimming/departure).
            </p>
          </div>

          {/* Differential Metrics */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Differencing Metrics
            </h4>
            <div className="space-y-3 font-mono text-xs">
              <div className="flex justify-between items-center p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-slate-400">RMS Difference:</span>
                <span className="text-cyan-400 font-bold">{diffResult.diff_stats.rms_diff_mjy_sr} MJy/sr</span>
              </div>
              <div className="flex justify-between items-center p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-slate-400">Peak Positive Residual:</span>
                <span className="text-emerald-400 font-bold">+{diffResult.diff_stats.peak_positive_flux} MJy/sr</span>
              </div>
              <div className="flex justify-between items-center p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-slate-400">Peak Negative Residual:</span>
                <span className="text-rose-400 font-bold">{diffResult.diff_stats.peak_negative_flux} MJy/sr</span>
              </div>
              <div className="flex justify-between items-center p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-slate-400">Noise Sigma (σ):</span>
                <span className="text-slate-300">±{diffResult.diff_stats.sigma_mjy_sr} MJy/sr</span>
              </div>
            </div>

            <div className="mt-2 p-3 bg-cyan-950/20 border border-cyan-800/40 rounded-lg text-[11px] text-cyan-300 space-y-1">
              <p className="font-semibold">Transient Detection Threshold:</p>
              <p className="text-slate-400">
                Signal-to-noise ratio ($S/N$) for candidate transients is evaluated against local variance per pixel.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
