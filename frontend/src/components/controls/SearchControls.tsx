import React, { useEffect, useState } from 'react';
import { Search, Compass, Layers, Filter, Sparkles, Loader2 } from 'lucide-react';
import { DemoPreset, ObservationRecord } from '../../types/astronomy';

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
  observations: ObservationRecord[];
  currentIndex: number;
  onSelectObservation: (index: number) => void;
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
  observations,
  currentIndex,
  onSelectObservation,
}) => {
  const [filter, setFilter] = useState('');
  const [customFov, setCustomFov] = useState(() => String(Number((fov * 60).toFixed(3))));
  useEffect(() => setCustomFov(String(Number((fov * 60).toFixed(3)))), [fov]);
  const matchingPresets = presets.filter(preset => preset.name.toLowerCase().includes(filter.trim().toLowerCase()));

  return (
    <aside
      aria-label="Target search and coordinate parameters"
      className="target-panel w-full lg:w-80 lg:shrink-0 bg-slate-950 border-b lg:border-b-0 lg:border-r border-slate-800 p-4 flex flex-col gap-4 overflow-y-auto"
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
        <input type="search" value={filter} onChange={event => setFilter(event.target.value)}
          aria-label="Filter targets" placeholder="Filter targets" className="instrument-input mb-3 w-full" />
        {presets.length > 0 && matchingPresets.length === 0 && <p className="text-sm text-slate-400">No matching targets.</p>}
        <div className="grid grid-cols-1 gap-0.5" role="group" aria-label="Official Challenge Presets">
          {matchingPresets.map((p) => (
            <button
              key={p.id}
              onClick={() => onSelectPreset(p)}
              aria-pressed={selectedPresetId === p.id}
              className={`target-row w-full text-left px-3 py-2 rounded text-xs transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
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
          Coordinates (ICRS)
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

      {observations.length > 0 && (
        <div className="border-t border-slate-800 pt-3">
          <label htmlFor="target-observation" className="block mb-2 text-sm font-medium">Observation</label>
          <select id="target-observation" className="instrument-input w-full"
            value={currentIndex} onChange={event => onSelectObservation(Number(event.target.value))}>
            {observations.map((observation, index) => (
              <option key={observation.id} value={index}>
                {index + 1}. {observation.utc_date?.split('T')[0] || 'Date unavailable'} · {observation.detector} · {observation.obs_id}
              </option>
            ))}
          </select>
        </div>
      )}

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
          <label htmlFor="custom-fov" className="block mt-2 text-xs text-slate-300">Custom width (arcminutes, 0.06–18)</label>
          <input id="custom-fov" className="instrument-input mt-1 w-full" type="number" min="0.06" max="18" step="0.06"
            value={customFov} onChange={event => setCustomFov(event.target.value)} onBlur={() => {
              const value = Number(customFov);
              if (value >= 0.06 && value <= 18) setFov(value / 60);
              else setCustomFov(String(Number((fov * 60).toFixed(3))));
            }} />
        </div>

        <div>
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5 block">
            Survey Release
          </label>
          <p className="text-[11px] text-slate-300 mb-2">Configured releases searches this app’s release list (normally DR1 and QR3). More observations depend on archive access.</p>
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
          className="search-submit w-full py-2.5 px-4 rounded-lg font-semibold text-xs transition flex items-center justify-center gap-2 disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
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
