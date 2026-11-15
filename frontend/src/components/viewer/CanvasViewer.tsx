import React, { useRef, useEffect, useState, useCallback } from 'react';
import { FrameResponse, CatalogSource } from '../../types/astronomy';
import { ZoomIn, ZoomOut, RotateCcw, Crosshair, Palette, Sliders, Star, Globe, Keyboard } from 'lucide-react';
import { AladinViewer } from './AladinViewer';
import { projectCatalog } from '../../services/api';

const IMAGE_PROVENANCE: Record<string, string> = {
  live_archive_cutout: 'live IRSA cutout', cached_archive_cutout: 'cached IRSA cutout',
  cached_demo_cutout: 'cached demonstration cutout', simulated: 'simulated fixture', local_fixture: 'local fixture',
};

interface CanvasViewerProps {
  frame: FrameResponse | null;
  loading: boolean;
  stretch: string;
  setStretch: (s: string) => void;
  colormap: string;
  setColormap: (c: string) => void;
  catalogSources?: CatalogSource[];
  showCatalog?: boolean;
  setShowCatalog?: (show: boolean) => void;
  title?: string;
  subtitle?: string;
  targetRa?: number;
  targetDec?: number;
  targetFov?: number;
}

export const CanvasViewer: React.FC<CanvasViewerProps> = ({
  frame,
  loading,
  stretch,
  setStretch,
  colormap,
  setColormap,
  catalogSources = [],
  showCatalog = false,
  setShowCatalog,
  title,
  subtitle,
  targetRa,
  targetDec,
  targetFov,
}) => {
  const [viewerMode, setViewerMode] = useState<'canvas' | 'aladin'>('canvas');
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [zoom, setZoom] = useState(1.0);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [showCrosshair, setShowCrosshair] = useState(true);
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null);
  const [cachedImg, setCachedImg] = useState<HTMLImageElement | null>(null);
  const [announcement, setAnnouncement] = useState<string>('');
  const [catalogPixels, setCatalogPixels] = useState<({x: number; y: number} | null)[]>([]);
  const [catalogError, setCatalogError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setCatalogPixels([]);
    setCatalogError(null);
    if (showCatalog && frame && !frame.is_synthetic && catalogSources.length > 0) {
      projectCatalog(frame.frame_id, targetFov ?? 0.04, catalogSources)
        .then(points => { if (active) setCatalogPixels(points); })
        .catch(() => { if (active) setCatalogError('Catalog positions are unavailable for this image.'); });
    } else if (showCatalog && frame?.is_synthetic) {
      setCatalogError('Catalog positions cannot be overlaid on a simulated image.');
    }
    return () => { active = false; };
  }, [frame, showCatalog, catalogSources, targetFov]);

  const resetView = useCallback(() => {
    setZoom(1.0);
    setOffset({ x: 0, y: 0 });
  }, []);

  // Keyboard controls for canvas accessibility
  const handleKeyDown = (e: React.KeyboardEvent) => {
    const panStep = 40;
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setOffset((prev) => {
        const nextY = prev.y + panStep;
        setAnnouncement(`Panned up [Offset: X=${prev.x}, Y=${nextY}]`);
        return { ...prev, y: nextY };
      });
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setOffset((prev) => {
        const nextY = prev.y - panStep;
        setAnnouncement(`Panned down [Offset: X=${prev.x}, Y=${nextY}]`);
        return { ...prev, y: nextY };
      });
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      setOffset((prev) => {
        const nextX = prev.x + panStep;
        setAnnouncement(`Panned left [Offset: X=${nextX}, Y=${prev.y}]`);
        return { ...prev, x: nextX };
      });
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      setOffset((prev) => {
        const nextX = prev.x - panStep;
        setAnnouncement(`Panned right [Offset: X=${nextX}, Y=${prev.y}]`);
        return { ...prev, x: nextX };
      });
    } else if (e.key === '+' || e.key === '=') {
      e.preventDefault();
      setZoom((prev) => {
        if (prev >= 7.9) {
          setAnnouncement('Maximum zoom limit reached (800%)');
          return 8.0;
        }
        const next = Math.min(prev * 1.25, 8.0);
        setAnnouncement(`Zoomed in to ${Math.round(next * 100)}%`);
        return next;
      });
    } else if (e.key === '-' || e.key === '_') {
      e.preventDefault();
      setZoom((prev) => {
        if (prev <= 0.41) {
          setAnnouncement('Minimum zoom limit reached (40%)');
          return 0.4;
        }
        const next = Math.max(prev * 0.8, 0.4);
        setAnnouncement(`Zoomed out to ${Math.round(next * 100)}%`);
        return next;
      });
    } else if (e.key === '0' || e.key === 'Home') {
      e.preventDefault();
      resetView();
      setAnnouncement('View reset to default 100% zoom and center position (0, 0)');
    }
  };

  // 1. Decode image once when frame or colormap changes
  useEffect(() => {
    if (!frame) {
      setCachedImg(null);
      return;
    }

    const img = new Image();
    img.src = colormap === 'inferno' && frame.colormapped_base64
      ? frame.colormapped_base64
      : frame.image_base64;

    img.onload = () => {
      setCachedImg(img);
    };
  }, [frame?.image_base64, frame?.colormapped_base64, colormap]);

  // 2. High-performance canvas redraw (runs smoothly during dragging / zooming)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !cachedImg) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = canvas.parentElement?.clientWidth || 600;
    canvas.height = canvas.parentElement?.clientHeight || 450;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.imageSmoothingEnabled = false; // Nearest neighbor preserves astronomical pixel blocks!

    ctx.save();
    ctx.translate(canvas.width / 2 + offset.x, canvas.height / 2 + offset.y);
    ctx.scale(zoom, zoom);

    // Draw image centered
    const drawW = cachedImg.width * 14;
    const drawH = cachedImg.height * 14;
    ctx.drawImage(cachedImg, -drawW / 2, -drawH / 2, drawW, drawH);

    // Gaia DR3 Celestial Catalog Overlay
    if (showCatalog && catalogSources.length > 0) {
      catalogSources.forEach((src, index) => {
        const pixel = catalogPixels[index];
        if (!pixel) return;
        const markerX = (pixel.x + 0.5) * 14 - drawW / 2;
        // FITS arrays are flipped vertically for display by the backend.
        const markerY = drawH / 2 - (pixel.y + 0.5) * 14;

        ctx.strokeStyle = '#38bdf8'; // Cyan-400
        ctx.fillStyle = '#38bdf8';
        ctx.lineWidth = 1.5;

        // Diamond marker
        ctx.beginPath();
        ctx.moveTo(markerX, markerY - 7);
        ctx.lineTo(markerX + 7, markerY);
        ctx.lineTo(markerX, markerY + 7);
        ctx.lineTo(markerX - 7, markerY);
        ctx.closePath();
        ctx.stroke();

        // Designation label & provenance badge
        ctx.font = '10px monospace';
        ctx.fillStyle = '#f8fafc';
        const provBadge = src.provenance?.includes('Demo') ? ' [Demo]' : (src.provenance?.includes('Live') ? ' [Live TAP]' : '');
        const label = `${src.designation}${src.g_mag ? ` (G=${src.g_mag.toFixed(1)})` : ''}${provBadge}`;
        ctx.fillText(label, markerX + 10, markerY + 3);
      });
    }

    // Crosshair
    if (showCrosshair) {
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.5)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);

      ctx.beginPath();
      ctx.moveTo(-drawW / 2 - 20, 0);
      ctx.lineTo(drawW / 2 + 20, 0);
      ctx.moveTo(0, -drawH / 2 - 20);
      ctx.lineTo(0, drawH / 2 + 20);
      ctx.stroke();

      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.arc(0, 0, 16, 0, Math.PI * 2);
      ctx.stroke();
    }

    ctx.restore();
  }, [cachedImg, zoom, offset, showCrosshair, showCatalog, catalogSources, catalogPixels, frame, viewerMode]);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }

    const rect = canvasRef.current?.getBoundingClientRect();
    if (rect) {
      setMousePos({
        x: Math.round(e.clientX - rect.left),
        y: Math.round(e.clientY - rect.top),
      });
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.15 : 0.85;
    setZoom((prev) => Math.min(Math.max(prev * factor, 0.4), 8.0));
  };

  return (
    <div className="flex-1 min-h-[440px] lg:min-h-0 flex flex-col bg-slate-950 relative overflow-hidden select-none" ref={containerRef}>
      {/* Screen reader live announcements */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {announcement}
      </div>
      <div id="canvas-keyboard-help" className="sr-only">
        Interactive astronomical canvas viewer. Use Arrow keys to pan image, Plus or Equal to zoom in, Minus to zoom out, and 0 to reset view.
      </div>

      {/* Top Overlay Controls */}
      <div className="shrink-0 z-20 flex flex-wrap items-center justify-between gap-2 px-3 py-2 border-b border-slate-800 bg-slate-950">
        <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 px-3 py-1.5 rounded-lg pointer-events-auto flex items-center gap-3">
          <div>
            <h3 className="text-xs font-semibold text-slate-100">{title || (frame ? frame.obs_id : 'Astronomical Viewer')}</h3>
            <p className="text-[10px] text-slate-300 font-mono">
              {subtitle || (frame ? `${frame.detector} • ${frame.utc_date?.split('T')[0] || ''}` : 'Select an observation')}
            </p>
            {frame && <p className="text-[11px] text-slate-300">Image source: {IMAGE_PROVENANCE[frame.image_provenance || ''] || 'unknown'}</p>}
            {frame?.is_synthetic && (
              <span className="inline-block mt-0.5 px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-amber-500/20 text-amber-200 border border-amber-500/40">
                SIMULATED FIXTURE (CUTOUT UNAVAILABLE)
              </span>
            )}
          </div>
        </div>

        {/* Viewer Mode Switcher: SPHEREx Canvas vs Aladin Lite Sky Context */}
        <div
          role="tablist"
          aria-label="Astronomical viewer display mode"
          className="bg-slate-900/90 backdrop-blur-md border border-slate-800 p-1 rounded-xl pointer-events-auto flex items-center gap-1 shadow-lg"
        >
          <button
            role="tab"
            aria-selected={viewerMode === 'canvas'}
            aria-label="Switch to SPHEREx quantitative canvas view"
            onClick={() => {
              setViewerMode('canvas');
              setAnnouncement('Switched to SPHEREx quantitative canvas');
            }}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
              viewerMode === 'canvas'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm font-semibold'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Sliders className="w-3.5 h-3.5 text-cyan-400" />
            <span>SPHEREx Canvas</span>
          </button>
          <button
            role="tab"
            aria-selected={viewerMode === 'aladin'}
            aria-label="Switch to Aladin Lite multi-wavelength sky context view"
            onClick={() => {
              setViewerMode('aladin');
              setAnnouncement('Switched to Aladin Lite multi-wavelength sky context');
            }}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
              viewerMode === 'aladin'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm font-semibold'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Globe className="w-3.5 h-3.5 text-cyan-400" />
            <span>Aladin Lite Sky Context</span>
          </button>
        </div>

        {/* Stretch & Visual Filters (shown in Canvas mode) */}
        {viewerMode === 'canvas' ? (
          <div
            role="group"
            aria-label="Image stretch and palette controls"
            className="bg-slate-900/90 backdrop-blur-md border border-slate-800 p-1 rounded-lg pointer-events-auto flex flex-wrap items-center gap-1.5 text-xs"
          >
            <div className="flex items-center gap-1 px-2 py-0.5 border-r border-slate-800 text-slate-300 font-medium">
              <Sliders className="w-3.5 h-3.5 text-cyan-400" />
              <span>Stretch (display contrast):</span>
            </div>
            {(['asinh', 'zscale', 'linear'] as const).map((s) => (
              <button
                key={s}
                aria-pressed={stretch === s}
                aria-label={`Apply ${s} display stretch preview`}
                onClick={() => {
                  setStretch(s);
                  setAnnouncement(`Display stretch set to ${s}`);
                }}
                className={`px-2 py-1 rounded text-[11px] font-mono capitalize transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                  stretch === s
                    ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/30'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                {s}
              </button>
            ))}

            <div className="h-4 w-px bg-slate-800 mx-1" />

            {/* Colormap toggle */}
            <button
              onClick={() => {
                const nextColormap = colormap === 'inferno' ? 'grayscale' : 'inferno';
                setColormap(nextColormap);
                setAnnouncement(`Color palette set to ${nextColormap}`);
              }}
              aria-label={`Toggle colormap. Current: ${colormap}`}
              className={`px-2 py-1 rounded text-[11px] flex items-center gap-1 transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                colormap === 'inferno'
                  ? 'bg-amber-500/20 text-amber-200 font-semibold border border-amber-500/40'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Palette className="w-3 h-3 text-cyan-400" />
              <span>{colormap === 'inferno' ? 'Inferno' : 'Grayscale'}</span>
            </button>
          </div>
        ) : (
          <div className="hidden sm:block pointer-events-auto">
            <span className="text-[11px] text-slate-300">Context survey</span>
          </div>
        )}
      </div>

      {viewerMode === 'aladin' && targetRa != null && targetDec != null ? (
        <AladinViewer
          ra={targetRa}
          dec={targetDec}
          fov={targetFov ?? 0.04}
          footprint={frame?.footprint_icrs_deg ?? null}
        />
      ) : viewerMode === 'aladin' ? (
        <div className="flex-1 flex items-center justify-center p-6 text-sm text-slate-300" role="status">Search for coordinates to open sky context.</div>
      ) : (
        <>
          {/* Canvas Area with Keyboard Focus & Navigation */}
          <div
            tabIndex={0}
            role="region"
            aria-label="SPHEREx Astronomical Canvas Viewer. Use arrow keys to pan, plus or minus to zoom, and zero to reset view."
            aria-describedby="canvas-keyboard-help"
            onKeyDown={handleKeyDown}
            className="flex-1 w-full h-full cursor-grab active:cursor-grabbing relative flex items-center justify-center outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-inset"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
          >
            <canvas ref={canvasRef} className="w-full h-full block" />

            {loading && (
              <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm flex flex-col items-center justify-center gap-2 z-30">
                <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-xs text-cyan-300 font-mono">Calibrating FITS Cutout...</span>
              </div>
            )}

            {!frame && !loading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-400 gap-2">
                <Crosshair className="w-10 h-10 opacity-40 text-cyan-400" />
                <p className="text-xs">No observation loaded. Select a target preset or enter sky coordinates.</p>
              </div>
            )}
          </div>

          {/* Bottom Floating Telemetry & Zoom Dock */}
          <div className="shrink-0 z-20 flex flex-wrap items-center justify-between gap-2 px-3 py-2 border-t border-slate-800 bg-slate-950">
            {showCatalog && <p className="w-full text-[11px] text-slate-300" role="status">{catalogError || 'Catalog positions are projected at their catalog epoch; proper motion is not applied and a marker does not confirm identity.'}</p>}
            <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 px-3 py-1 rounded-md pointer-events-auto text-[11px] font-mono text-slate-300 flex items-center gap-3">
              <span>Scale: {(zoom * 100).toFixed(0)}%</span>
              {frame && (
                <>
                  <span className="text-slate-600">|</span>
                  <span>Dims: {frame.dimensions.join('×')} px</span>
                  <span className="text-slate-600">|</span>
                  <span>FOV: ~{(frame.dimensions[0] * 6.2 / 60).toFixed(1)}′</span>
                  {mousePos && (
                    <>
                      <span className="text-slate-600">|</span>
                      <span className="text-cyan-400">Cursor: [{mousePos.x}, {mousePos.y}]</span>
                    </>
                  )}
                </>
              )}
              {/* Keyboard shortcuts helper badge */}
              <span className="hidden xl:inline-flex items-center gap-1.5 text-slate-400 border-l border-slate-700/80 pl-3">
                <Keyboard className="w-3 h-3 text-cyan-400" />
                <span>Pan: <kbd className="px-1 py-0.5 bg-slate-800 rounded border border-slate-700 text-slate-200">Arrows</kbd></span>
                <span>Zoom: <kbd className="px-1 py-0.5 bg-slate-800 rounded border border-slate-700 text-slate-200">+/-</kbd></span>
                <span>Reset: <kbd className="px-1 py-0.5 bg-slate-800 rounded border border-slate-700 text-slate-200">0</kbd></span>
              </span>
            </div>

            {/* Zoom controls */}
            <div
              role="toolbar"
              aria-label="Canvas zoom and view controls"
              className="bg-slate-900/90 backdrop-blur-md border border-slate-800 p-1 rounded-lg pointer-events-auto flex items-center gap-1"
            >
              {setShowCatalog && (
                <button
                  onClick={() => {
                    setShowCatalog(!showCatalog);
                    setAnnouncement(!showCatalog ? 'Reference stars enabled' : 'Reference stars disabled');
                  }}
                  aria-pressed={showCatalog}
                  aria-label={`Toggle Reference Stars: ${catalogSources[0]?.provenance || 'Gaia DR3 / Curated Demo'}`}
                  title={`Toggle Reference Stars: ${catalogSources[0]?.provenance || 'Gaia DR3 / Curated Demo'}`}
                  className={`px-2 py-1 rounded text-[11px] font-mono flex items-center gap-1 transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                    showCatalog
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                  }`}
                >
                  <Star className="w-3.5 h-3.5 text-cyan-400" />
                  <span>
                    {catalogSources[0]?.provenance?.includes('Demo') ? 'Curated Demo Gaia' : (catalogSources[0]?.provenance?.includes('Live') ? 'Live Gaia TAP' : 'Gaia DR3')}{' '}
                    {catalogSources.length > 0 ? `(${catalogSources.length})` : ''}
                  </span>
                </button>
              )}

              <div className="h-4 w-px bg-slate-800 mx-0.5" />

              <button
                onClick={() => {
                  setShowCrosshair(!showCrosshair);
                  setAnnouncement(!showCrosshair ? 'Celestial crosshair enabled' : 'Celestial crosshair disabled');
                }}
                aria-pressed={showCrosshair}
                  aria-label="Toggle image-center crosshair"
                  title="Toggle image-center crosshair"
                className={`p-1.5 rounded transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                  showCrosshair ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <Crosshair className="w-4 h-4" />
              </button>
              <button
                onClick={() => {
                  setZoom((prev) => {
                    const next = Math.min(prev * 1.25, 8.0);
                    setAnnouncement(`Zoomed in to ${Math.round(next * 100)}%`);
                    return next;
                  });
                }}
                aria-label="Zoom In"
                title="Zoom In (+)"
                className="p-1.5 text-slate-300 hover:text-white hover:bg-slate-800 rounded transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                onClick={() => {
                  setZoom((prev) => {
                    const next = Math.max(prev * 0.8, 0.4);
                    setAnnouncement(`Zoomed out to ${Math.round(next * 100)}%`);
                    return next;
                  });
                }}
                aria-label="Zoom Out"
                title="Zoom Out (-)"
                className="p-1.5 text-slate-300 hover:text-white hover:bg-slate-800 rounded transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button
                onClick={() => {
                  resetView();
                  setAnnouncement('View reset to default 100% zoom and center position');
                }}
                aria-label="Reset View"
                title="Reset View (0)"
                className="p-1.5 text-slate-300 hover:text-white hover:bg-slate-800 rounded transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
