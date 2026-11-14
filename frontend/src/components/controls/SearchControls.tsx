import React from 'react';
import { Search, Compass, Layers, Filter, Sparkles, Loader2 } from 'lucide-react';
import { DemoPreset } from '../../types/astronomy';

interface SearchControlsProps {
  ra: string;
  setRa: (ra: string) => void;
  dec: string;
  setDec: (dec: string) => void;
  fov: number;
  setFov: (fov: number) => void;
  collection: string;
  setCollection: (col: string) => void;
  detector: string;
  setDetector: (det: string) => void;
  loading: boolean;
  onSearch: () => void;
  presets: DemoPreset[];
  onSelectPreset: (preset: DemoPreset) => void;
  selectedPresetId?: string;
}

export const SearchControls: React.FC<SearchControlsProps> = ({
  ra,
  setRa,
  dec,
  setDec,
  fov,
  setFov,
  collection,
  setCollection,
  detector,
  setDetector,
  loading,
  onSearch,
  presets,
  onSelectPreset,
  selectedPresetId,
}) => {
  return (
    <div className="w-80 bg-slate-900/60 border-r border-slate-800 p-4 flex flex-col gap-4 overflow-y-auto">
      {/* Official Challenge Presets */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            Official Targets
          </label>
        </div>
        <div className="grid grid-cols-1 gap-1.5">
          {presets.map((p) => (
            <button
              key={p.id}
              onClick={() => onSelectPreset(p)}
              className={`w-full text-left p-2 rounded-lg text-xs transition border ${
                selectedPresetId === p.id
                  ? 'bg-cyan-950/60 border-cyan-500/50 text-cyan-200'
                  : 'bg-slate-900 border-slate-800/80 hover:border-slate-700 text-slate-300'
              }`}
            >
              <div className="font-semibold text-slate-200 flex items-center justify-between">
                <span>{p.name}</span>
                <span className="text-[10px] text-cyan-400/80 font-mono">
                  {p.ra.toFixed(2)}°, {p.dec.toFixed(2)}°
                </span>
              </div>
              <p className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">{p.notable_feature}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="border-t border-slate-800/80 pt-3">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-2.5">
          <Compass className="w-3.5 h-3.5 text-cyan-400" />
          Coordinates (J2000)
        </label>

        <div className="space-y-2">
          <div>
            <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
              <span>Right Ascension (RA)</span>
              <span className="text-[10px] text-slate-500">deg or HMS</span>
            </div>
            <input
              type="text"
              value={ra}
              onChange={(e) => setRa(e.target.value)}
              placeholder="e.g. 269.45208 or 17h57m48s"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div>
            <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
              <span>Declination (Dec)</span>
              <span className="text-[10px] text-slate-500">deg or DMS</span>
            </div>
            <input
              type="text"
              value={dec}
              onChange={(e) => setDec(e.target.value)}
              placeholder="e.g. 4.69339 or +04d41m36s"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>
        </div>
      </div>

      {/* Query Parameters */}
      <div className="border-t border-slate-800/80 pt-3 space-y-3">
        <div>
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-1.5">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            Field of View (Cutout Size)
          </label>
          <div className="grid grid-cols-3 gap-1.5">
            {[0.02, 0.04, 0.08].map((size) => (
              <button
                key={size}
                type="button"
                onClick={() => setFov(size)}
                className={`py-1 text-xs rounded-md border font-mono transition ${
                  fov === size
                    ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {(size * 60).toFixed(1)}′
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5 block">
            Survey Release
          </label>
          <div className="grid grid-cols-2 gap-1.5">
            <button
              type="button"
              onClick={() => setCollection('spherex_dr1')}
              className={`py-1.5 px-2 text-xs rounded-md border transition text-center ${
                collection === 'spherex_dr1'
                  ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300 font-semibold'
                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              DR1 (Surveys 1 & 2)
            </button>
            <button
              type="button"
              onClick={() => setCollection('spherex_qr3')}
              className={`py-1.5 px-2 text-xs rounded-md border transition text-center ${
                collection === 'spherex_qr3'
                  ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300 font-semibold'
                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              QR3 (Surveys 3 & 4)
            </button>
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-1.5">
            <Filter className="w-3.5 h-3.5 text-cyan-400" />
            Detector Band Filter
          </label>
          <select
            value={detector}
            onChange={(e) => setDetector(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Detectors (D1 – D6)</option>
            <option value="SPHEREx-D1">D1 (0.75 – 1.12 µm)</option>
            <option value="SPHEREx-D2">D2 (1.10 – 1.65 µm)</option>
            <option value="SPHEREx-D3">D3 (1.63 – 2.43 µm)</option>
            <option value="SPHEREx-D4">D4 (2.40 – 3.85 µm)</option>
            <option value="SPHEREx-D5">D5 (3.81 – 4.43 µm)</option>
            <option value="SPHEREx-D6">D6 (4.41 – 5.01 µm)</option>
          </select>
        </div>
      </div>

      <div className="mt-auto pt-2">
        <button
          onClick={onSearch}
          disabled={loading}
          className="w-full py-2.5 px-4 bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white rounded-lg font-semibold text-xs transition flex items-center justify-center gap-2 shadow-lg shadow-cyan-950/50 disabled:opacity-50"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Querying NASA IRSA...</span>
            </>
          ) : (
            <>
              <Search className="w-4 h-4" />
              <span>Discover Observations</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
