import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Globe, Layers, ZoomIn, ZoomOut, RotateCcw, Crosshair } from 'lucide-react';

export interface AladinViewerProps {
  ra: number;
  dec: number;
  fov?: number;
  obsId?: string;
  detector?: string;
  dimensions?: number[];
  collection?: string;
}

interface SurveyOption {
  id: string;
  name: string;
  band: string;
  description: string;
}

const SURVEY_OPTIONS: SurveyOption[] = [
  {
    id: 'P/2MASS/color',
    name: '2MASS Color',
    band: 'Near-Infrared (JHK: 1.25–2.17 µm)',
    description: 'Direct celestial baseline for SPHEREx Band 1-2 infrared sources',
  },
  {
    id: 'P/allWISE/color',
    name: 'AllWISE Color',
    band: 'Mid-Infrared (W1-W4: 3.4–22 µm)',
    description: 'Longer wavelength infrared archive for SPHEREx dust & variability',
  },
  {
    id: 'P/DSS2/color',
    name: 'DSS2 Color',
    band: 'Optical (Blue/Red/IR)',
    description: 'Digitized Sky Survey optical baseline for stellar identification',
  },
  {
    id: 'P/PanSTARRS/DR1/color-z-zg-g',
    name: 'Pan-STARRS DR1',
    band: 'Deep Optical (g/r/i/z/y)',
    description: 'High-resolution optical sky survey for host galaxy and stellar counterparts',
  },
];

export const AladinViewer: React.FC<AladinViewerProps> = ({
  ra,
  dec,
  fov = 0.04,
  obsId,
  detector,
  dimensions = [128, 128],
  collection = 'SPHEREx DR1',
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const aladinInstanceRef = useRef<any>(null);
  const [activeSurvey, setActiveSurvey] = useState<string>('P/2MASS/color');
  const [scriptLoaded, setScriptLoaded] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [currentZoomFov, setCurrentZoomFov] = useState<number>(fov * 2.5);

  // Compute bounding box footprint coordinates
  const halfFovDeg = fov / 2;
  const cosDec = Math.max(Math.cos((dec * Math.PI) / 180), 0.01);
  const halfRaDeg = halfFovDeg / cosDec;

  const footprintCorners = [
    { ra: ra - halfRaDeg, dec: dec - halfFovDeg },
    { ra: ra + halfRaDeg, dec: dec - halfFovDeg },
    { ra: ra + halfRaDeg, dec: dec + halfFovDeg },
    { ra: ra - halfRaDeg, dec: dec + halfFovDeg },
  ];

  // Helper to load Aladin Lite script dynamically
  useEffect(() => {
    if ((window as any).A) {
      setScriptLoaded(true);
      return;
    }

    const scriptSrc = 'https://cdn.jsdelivr.net/npm/aladin-lite@3.3.0/dist/aladin.umd.cjs';
    const existing = document.querySelector(`script[src="${scriptSrc}"]`);
    if (existing) {
      existing.addEventListener('load', () => setScriptLoaded(true));
      return;
    }

    const script = document.createElement('script');
    script.src = scriptSrc;
    script.async = true;
    script.onload = () => {
      setScriptLoaded(true);
    };
    script.onerror = () => {
      // Secondary fallback to CDS official URL
      const fallbackScript = document.createElement('script');
      fallbackScript.src = 'https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.js';
      fallbackScript.async = true;
      fallbackScript.onload = () => setScriptLoaded(true);
      fallbackScript.onerror = () => {
        setLoadError('Aladin Lite library could not be loaded from external CDN.');
      };
      document.head.appendChild(fallbackScript);
    };
    document.head.appendChild(script);
  }, []);

  // Update SPHEREx coverage footprint overlay
  const updateFootprintOverlay = useCallback((aladin: any) => {
    try {
      const A = (window as any).A;
      if (!A || !aladin) return;

      // Clean existing overlays
      if (aladin.view && aladin.view.overlays) {
        aladin.view.overlays.forEach((o: any) => {
          if (o.name === 'SPHEREx Footprint') {
            o.removeAll && o.removeAll();
          }
        });
      }

      const overlay = A.graphicOverlay({
        name: 'SPHEREx Footprint',
        color: '#06b6d4', // Cyan-500
        lineWidth: 2,
      });
      aladin.addOverlay(overlay);

      const polygonCoords = [
        [footprintCorners[0].ra, footprintCorners[0].dec],
        [footprintCorners[1].ra, footprintCorners[1].dec],
        [footprintCorners[2].ra, footprintCorners[2].dec],
        [footprintCorners[3].ra, footprintCorners[3].dec],
      ];

      const polygon = A.polygon(polygonCoords);
      overlay.add(polygon);
    } catch (err) {
      console.warn('[AladinViewer] Could not draw footprint overlay:', err);
    }
  }, [footprintCorners]);

  // Initialize or re-target Aladin Lite instance
  useEffect(() => {
    if (!scriptLoaded || !containerRef.current) return;
    const A = (window as any).A;
    if (!A) return;

    try {
      if (!aladinInstanceRef.current) {
        // Clear previous content
        containerRef.current.innerHTML = '';
        const aladinDiv = document.createElement('div');
        aladinDiv.id = 'aladin-lite-mount-point';
        aladinDiv.style.width = '100%';
        aladinDiv.style.height = '100%';
        containerRef.current.appendChild(aladinDiv);

        const initPromise = A.init ? A.init : Promise.resolve();
        initPromise.then(() => {
          const inst = A.aladin('#aladin-lite-mount-point', {
            survey: activeSurvey,
            fov: currentZoomFov,
            target: `${ra} ${dec}`,
            showReticle: true,
            showZoomControl: false,
            showFullscreenControl: false,
            showLayersControl: false,
            showGotoControl: false,
          });
          aladinInstanceRef.current = inst;
          updateFootprintOverlay(inst);
        }).catch((e: any) => {
          console.warn('[AladinViewer] WebGL initialization fallback:', e);
          setLoadError(String(e));
        });
      } else {
        const inst = aladinInstanceRef.current;
        if (inst.gotoRaDec) {
          inst.gotoRaDec(ra, dec);
        }
        if (inst.setFov) {
          inst.setFov(currentZoomFov);
        }
        updateFootprintOverlay(inst);
      }
    } catch (err: any) {
      console.warn('[AladinViewer] Aladin initialization error:', err);
      setLoadError(err.message || 'Aladin initialization error');
    }
  }, [scriptLoaded, ra, dec, currentZoomFov, updateFootprintOverlay]);

  // Survey switch handler
  const handleSelectSurvey = (surveyId: string) => {
    setActiveSurvey(surveyId);
    if (aladinInstanceRef.current && aladinInstanceRef.current.setImageSurvey) {
      aladinInstanceRef.current.setImageSurvey(surveyId);
    }
  };

  const handleZoom = (factor: number) => {
    const newFov = Math.max(Math.min(currentZoomFov * factor, 15.0), 0.005);
    setCurrentZoomFov(newFov);
    if (aladinInstanceRef.current && aladinInstanceRef.current.setFov) {
      aladinInstanceRef.current.setFov(newFov);
    }
  };

  const handleReset = () => {
    const resetFov = fov * 2.5;
    setCurrentZoomFov(resetFov);
    if (aladinInstanceRef.current) {
      if (aladinInstanceRef.current.gotoRaDec) {
        aladinInstanceRef.current.gotoRaDec(ra, dec);
      }
      if (aladinInstanceRef.current.setFov) {
        aladinInstanceRef.current.setFov(resetFov);
      }
      updateFootprintOverlay(aladinInstanceRef.current);
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-slate-950 relative overflow-hidden select-none">
      {/* Top Header & Survey Switcher Bar */}
      <div className="absolute top-3 left-4 right-4 z-20 flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        {/* Sky Context Target Badge */}
        <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 px-3.5 py-1.5 rounded-xl pointer-events-auto flex items-center gap-3 shadow-lg">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Globe className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-semibold text-slate-100">Aladin Lite Sky Context</h3>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                CDS v3 HiPS
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono">
              RA {ra.toFixed(5)}° Dec {dec >= 0 ? `+${dec.toFixed(5)}` : dec.toFixed(5)}° • {obsId || 'Active Target'}
            </p>
          </div>
        </div>

        {/* Survey Selection Bar */}
        <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 p-1 rounded-xl pointer-events-auto flex items-center gap-1 shadow-lg">
          <div className="flex items-center gap-1 px-2 py-0.5 text-xs text-slate-400 border-r border-slate-800">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Survey:</span>
          </div>
          {SURVEY_OPTIONS.map((srv) => (
            <button
              key={srv.id}
              onClick={() => handleSelectSurvey(srv.id)}
              title={`${srv.band} — ${srv.description}`}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                activeSurvey === srv.id
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              {srv.name}
            </button>
          ))}
        </div>
      </div>

      {/* Main Aladin Lite Mount Area */}
      <div className="flex-1 w-full h-full relative" ref={containerRef}>
        {/* Offline / WebGL Fallback Card when CDN or WebGL is not available */}
        {loadError && (
          <div className="absolute inset-0 bg-slate-950 flex flex-col items-center justify-center p-6 text-center z-10">
            <div className="max-w-lg bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl backdrop-blur-md">
              <div className="w-12 h-12 rounded-full bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mx-auto mb-3 text-cyan-400">
                <Globe className="w-6 h-6" />
              </div>
              <h4 className="text-sm font-semibold text-slate-100 mb-1">
                Aladin Lite Sky Context Overlay
              </h4>
              <p className="text-xs text-slate-400 mb-4 font-mono">
                Synchronized Target Footprint: RA {ra.toFixed(5)}°, Dec {dec.toFixed(5)}°
              </p>

              {/* High-fidelity SVG Sky Footprint Simulation */}
              <div className="w-full h-48 bg-slate-950/80 rounded-xl border border-slate-800 relative overflow-hidden flex items-center justify-center mb-4">
                <svg className="w-full h-full" viewBox="0 0 400 200">
                  {/* Sky grid lines */}
                  <line x1="50" y1="100" x2="350" y2="100" stroke="#334155" strokeDasharray="4 4" strokeWidth="1" />
                  <line x1="200" y1="20" x2="200" y2="180" stroke="#334155" strokeDasharray="4 4" strokeWidth="1" />
                  <circle cx="200" cy="100" r="70" fill="none" stroke="#1e293b" strokeWidth="1" />
                  <circle cx="200" cy="100" r="40" fill="none" stroke="#1e293b" strokeWidth="1" />

                  {/* SPHEREx Observation Footprint Box */}
                  <rect
                    x="165"
                    y="75"
                    width="70"
                    height="50"
                    fill="rgba(6, 182, 212, 0.15)"
                    stroke="#06b6d4"
                    strokeWidth="2"
                    strokeDasharray="6 3"
                    rx="4"
                  />
                  {/* Center Crosshair */}
                  <line x1="190" y1="100" x2="210" y2="100" stroke="#38bdf8" strokeWidth="1.5" />
                  <line x1="200" y1="90" x2="200" y2="110" stroke="#38bdf8" strokeWidth="1.5" />
                  <circle cx="200" cy="100" r="3" fill="#38bdf8" />

                  <text x="200" y="65" textAnchor="middle" fill="#38bdf8" fontSize="10" fontFamily="monospace">
                    SPHEREx Cutout ({dimensions[0]}×{dimensions[1]} px)
                  </text>
                  <text x="200" y="145" textAnchor="middle" fill="#94a3b8" fontSize="9" fontFamily="monospace">
                    FOV: ~{(fov * 60).toFixed(1)} arcmin • {detector || 'All Detectors'}
                  </text>
                </svg>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                <span>Active Baseline: <strong className="text-cyan-400">{SURVEY_OPTIONS.find(s => s.id === activeSurvey)?.name}</strong></span>
                <span>Coverage: <strong className="text-slate-200">{collection}</strong></span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Floating Telemetry & Controls */}
      <div className="absolute bottom-3 left-4 right-4 z-20 flex items-center justify-between pointer-events-none">
        <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 px-3.5 py-1.5 rounded-xl pointer-events-auto text-[11px] font-mono text-slate-300 flex items-center gap-3 shadow-lg">
          <div className="flex items-center gap-1.5 text-cyan-400">
            <Crosshair className="w-3.5 h-3.5" />
            <span>Target:</span>
          </div>
          <span>RA {ra.toFixed(5)}°</span>
          <span className="text-slate-600">|</span>
          <span>Dec {dec >= 0 ? `+${dec.toFixed(5)}` : dec.toFixed(5)}°</span>
          <span className="text-slate-600">|</span>
          <span className="text-cyan-300">FOV: {(currentZoomFov * 60).toFixed(1)}′</span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400 hidden sm:inline">
            Footprint: {((fov * 3600) / 60).toFixed(1)}′ × {((fov * 3600) / 60).toFixed(1)}′
          </span>
        </div>

        {/* Zoom & View Controls */}
        <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 p-1 rounded-xl pointer-events-auto flex items-center gap-1 shadow-lg">
          <button
            onClick={() => handleZoom(0.7)}
            title="Zoom In Sky Context"
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => handleZoom(1.4)}
            title="Zoom Out Sky Context"
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={handleReset}
            title="Reset to SPHEREx Coverage Center"
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
