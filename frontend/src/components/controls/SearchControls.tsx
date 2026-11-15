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
    <aside
      aria-label="Target search and coordinate parameters"
      className="w-full lg:w-80 lg:shrink-0 bg-slate-950 border-b lg:border-b-0 lg:border-r border-slate-800 p-4 flex flex-col gap-4 overflow-y-auto"
    >
      {/* Official Challenge Presets */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            Explore a target
          </label>
        </div>
        <p className="text-xs text-slate-400 mb-2">Starting coordinates for the challenge; a position alone does not identify a source.</p>
        <div className="grid grid-cols-1 gap-0.5" role="group" aria-label="Official Challenge Presets">
          {presets.map((p) => (
            <button
              key={p.id}
              onClick={() => onSelectPreset(p)}
              aria-pressed={selectedPresetId === p.id}
              className={`w-full text-left px-2 py-2 rounded text-xs transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                selectedPresetId === p.id
                  ? 'bg-cyan-950/70 text-cyan-100 ring-1 ring-inset ring-cyan-500/60'
                  : 'text-slate-200 hover:bg-slate-900'
              }`}
            >
              <div className="font-semibold text-slate-100 flex items-center justify-between">
                <span>{p.name}</span>
                <span className="text-[10px] text-cyan-300 font-mono">
                  {p.ra.toFixed(2)}°, {p.dec.toFixed(2)}°
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="border-t border-slate-800/80 pt-3">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 mb-2.5">
          <Compass className="w-3.5 h-3.5 text-cyan-400" />
          Coordinates (J2000)
        </label>
        <p className="text-xs text-slate-400 mb-2">Enter sky coordinates in degrees or sexagesimal format.</p>

        <div className="space-y-2">
          <div>
            <div className="flex items-center justify-between text-[11px] text-slate-300 mb-1">
              <label htmlFor="ra-input">Right Ascension (RA)</label>
              <span className="text-[10px] text-slate-400">deg or HMS</span>
            </div>
            <input
              id="ra-input"
              type="text"
              value={ra}
              onChange={(e) => setRa(e.target.value)}
              placeholder="e.g. 269.45208 or 17h57m48s"
              aria-label="Right Ascension (RA) in decimal degrees or sexagesimal HMS"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-cyan-500 focus-visible:ring-2 focus-visible:ring-cyan-400 font-mono"
            />
          </div>

          <div>
            <div className="flex items-center justify-between text-[11px] text-slate-300 mb-1">
              <label htmlFor="dec-input">Declination (Dec)</label>
              <span className="text-[10px] text-slate-400">deg or DMS</span>
            </div>
            <input
              id="dec-input"
              type="text"
              value={dec}
              onChange={(e) => setDec(e.target.value)}
              placeholder="e.g. 4.69339 or +04d41m36s"
              aria-label="Declination (Dec) in decimal degrees or sexagesimal DMS"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-cyan-500 focus-visible:ring-2 focus-visible:ring-cyan-400 font-mono"
            />
          </div>
        </div>
      </div>

      {/* Query Parameters */}
      <div className="border-t border-slate-800/80 pt-3 space-y-3">
        <div>
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 mb-1.5">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            Field of View (Cutout Size)
          </label>
          <p className="text-[11px] text-slate-300 mb-2">The width of sky requested around the coordinates. One arcminute is 1/60 of a degree.</p>
          <div className="grid grid-cols-3 gap-1.5" role="group" aria-label="Field of view options">
            {[0.02, 0.04, 0.08].map((size) => (
              <button
                key={size}
                type="button"
                onClick={() => setFov(size)}
                aria-pressed={fov === size}
                aria-label={`Field of view ${(size * 60).toFixed(1)} arcminutes`}
                className={`py-1 text-xs rounded-md border font-mono transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                  fov === size
                    ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300 font-semibold'
                    : 'bg-slate-950 border-slate-800 text-slate-300 hover:text-white'
                }`}
              >
                {(size * 60).toFixed(1)}′
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5 block">
            Survey Release
          </label>
          <div className="grid grid-cols-3 gap-1" role="group" aria-label="Survey release data version">
            <button
              type="button"
              onClick={() => setCollection('spherex_dr1')}
              aria-pressed={collection === 'spherex_dr1'}
              aria-label="Data Release 1 (Surveys 1 and 2)"
              className={`py-1.5 px-1.5 text-[11px] rounded-md border transition text-center focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                collection === 'spherex_dr1'
                  ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300 font-semibold'
                  : 'bg-slate-950 border-slate-800 text-slate-300 hover:text-white'
              }`}
            >
              DR1
            </button>
            <button
              type="button"
              onClick={() => setCollection('spherex_qr3')}
              aria-pressed={collection === 'spherex_qr3'}
              aria-label="Quick Release 3 (Surveys 3 and 4)"
              className={`py-1.5 px-1.5 text-[11px] rounded-md border transition text-center focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                collection === 'spherex_qr3'
                  ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300 font-semibold'
                  : 'bg-slate-950 border-slate-800 text-slate-300 hover:text-white'
              }`}
            >
              QR3
            </button>
            <button
              type="button"
              onClick={() => setCollection('ALL')}
              aria-pressed={collection === 'ALL'}
              aria-label="Search configured releases for multiple epochs"
              className={`py-1.5 px-1.5 text-[11px] rounded-md border transition text-center focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                collection === 'ALL'
                  ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300 font-semibold'
                  : 'bg-slate-950 border-slate-800 text-slate-300 hover:text-white'
              }`}
            >
              Configured releases
            </button>
          </div>
        </div>

        <div>
          <label htmlFor="detector-select" className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 mb-1.5">
            <Filter className="w-3.5 h-3.5 text-cyan-400" />
            Detector Band Filter
          </label>
          <p className="text-[11px] text-slate-300 mb-2">Each detector covers a range of infrared wavelengths; choose All to include every detector.</p>
          <select
            id="detector-select"
            value={detector}
            onChange={(e) => setDetector(e.target.value)}
            aria-label="Filter observations by detector band"
            className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 focus-visible:ring-2 focus-visible:ring-cyan-400"
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
          aria-label="Discover Observations from NASA IRSA"
          className="w-full py-2.5 px-4 bg-gradient-to-r from-cyan-700 to-indigo-700 hover:from-cyan-800 hover:to-indigo-800 text-white rounded-lg font-semibold text-xs transition flex items-center justify-center gap-2 shadow-lg shadow-cyan-950/50 disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-white" />
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
    </aside>
  );
};
