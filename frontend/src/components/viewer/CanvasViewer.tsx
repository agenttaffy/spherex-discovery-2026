import React, { useRef, useEffect, useState, useCallback } from 'react';
import { FrameResponse, CatalogSource } from '../../types/astronomy';
import { ZoomIn, ZoomOut, RotateCcw, Crosshair, Palette, Sliders, Star, Globe, Keyboard } from 'lucide-react';
import { AladinViewer } from './AladinViewer';
import { projectCatalog } from '../../services/api';
import { imageProvenanceLabel } from '../../services/imageProvenance';

interface CanvasViewerProps {
  frame: FrameResponse | null;
  loading: boolean;
  stretch: string;
  setStretch: (s: string) => void;
  colormap: string;
  setColormap: (c: string) => void;
  catalogSources?: CatalogSource[];
  loadingCatalog?: boolean;
  catalogQueryError?: boolean;
  showCatalog?: boolean;
  setShowCatalog?: (show: boolean) => void;
  title?: string;
  subtitle?: string;
  targetRa?: number;
  targetDec?: number;
  targetFov?: number;
  targetId?: string;
  emptyFieldPreview?: React.ReactNode;
}

export const CanvasViewer: React.FC<CanvasViewerProps> = ({
  frame,
  loading,
  stretch,
  setStretch,
  colormap,
  setColormap,
  catalogSources = [],
  loadingCatalog = false,
  catalogQueryError = false,
  showCatalog = false,
  setShowCatalog,
  title,
  subtitle,
  targetRa,
  targetDec,
  targetFov,
  targetId,
  emptyFieldPreview,
}) => {
  const prediction = targetId ? frame?.target_predictions?.[targetId] : undefined;
  const photometry = targetId ? frame?.target_photometry?.[targetId] : undefined;
  const [viewerMode, setViewerMode] = useState<'canvas' | 'aladin'>('canvas');
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [zoom, setZoom] = useState(1.0);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [showCrosshair, setShowCrosshair] = useState(true);
  const [showCatalogLabels, setShowCatalogLabels] = useState(false);
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null);
  const [cachedImg, setCachedImg] = useState<HTMLImageElement | null>(null);
  const [announcement, setAnnouncement] = useState<string>('');
  const [catalogPixels, setCatalogPixels] = useState<({x: number; y: number; motion_applied: boolean} | null)[]>([]);
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
    return () => { img.onload = null; };
  }, [frame?.image_base64, frame?.colormapped_base64, colormap]);

  // 2. High-performance canvas redraw (runs smoothly during dragging / zooming)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const draw = () => {
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      canvas.width = canvas.parentElement?.clientWidth || 600;
      canvas.height = canvas.parentElement?.clientHeight || 450;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!cachedImg || !frame) return;
      ctx.imageSmoothingEnabled = false; // Nearest neighbor preserves astronomical pixel blocks!

      ctx.save();
      ctx.translate(canvas.width / 2 + offset.x, canvas.height / 2 + offset.y);
      ctx.scale(zoom, zoom);

      // Fit at whole display pixels per sample when the viewport has room.
      const gutter = Math.min(40, Math.min(canvas.width, canvas.height) * 0.1);
      const fit = Math.min((canvas.width - gutter) / cachedImg.width, (canvas.height - gutter) / cachedImg.height);
      const pixelScale = fit >= 1 ? Math.floor(fit) : fit;
      const drawW = cachedImg.width * pixelScale;
      const drawH = cachedImg.height * pixelScale;
      ctx.drawImage(cachedImg, -drawW / 2, -drawH / 2, drawW, drawH);
      ctx.lineWidth = 1 / zoom;
      ctx.strokeStyle = '#8493b96b';
      ctx.strokeRect(-drawW / 2 - 1, -drawH / 2 - 1, drawW + 2, drawH + 2);

      const predictedPixel = prediction?.pixel;
      if (predictedPixel?.inside) {
        const x = (predictedPixel.x + 0.5) * pixelScale - drawW / 2;
        const y = drawH / 2 - (predictedPixel.y + 0.5) * pixelScale;
        ctx.strokeStyle = '#f2b85b';
        ctx.lineWidth = 2;
        ctx.strokeRect(x - 5, y - 5, 10, 10);
      }

      // Gaia DR3 Celestial Catalog Overlay
      if (showCatalog && catalogSources.length > 0) {
        catalogSources.forEach((src, index) => {
          const pixel = catalogPixels[index];
          if (!pixel) return;
          const markerX = (pixel.x + 0.5) * pixelScale - drawW / 2;
          // FITS arrays are flipped vertically for display by the backend.
          const markerY = drawH / 2 - (pixel.y + 0.5) * pixelScale;

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

          // Long catalog identifiers are optional so they do not obscure the sky.
          if (showCatalogLabels) {
            ctx.font = '10px monospace';
            ctx.fillStyle = '#f8fafc';
            const label = `${src.designation}${src.g_mag != null ? ` (G=${src.g_mag.toFixed(1)})` : ''} ${pixel.motion_applied ? '[PM]' : '[2016]'}`;
            ctx.fillText(label, markerX + 10, markerY + 3);
          }
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
    };
    draw();
    const observer = new ResizeObserver(draw);
    if (canvas.parentElement) observer.observe(canvas.parentElement);
    return () => observer.disconnect();
  }, [cachedImg, zoom, offset, showCrosshair, showCatalog, showCatalogLabels, catalogSources, catalogPixels, frame, viewerMode, prediction]);

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
    <div className="instrument-viewer flex-1 min-h-[340px] sm:min-h-[340px] lg:min-h-0 flex flex-col bg-slate-950 relative overflow-hidden select-none" ref={containerRef}>
      {/* Screen reader live announcements */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {announcement}
      </div>
      <div id="canvas-keyboard-help" className="sr-only">
        Interactive astronomical canvas viewer. Use Arrow keys to pan image, Plus or Equal to zoom in, Minus to zoom out, and 0 to reset view.
      </div>

      {/* Observation identity and display controls */}
      <div className="viewer-tools shrink-0 z-20 flex flex-wrap items-center justify-between gap-2 px-2.5 sm:px-3 py-2 border-b border-slate-800 bg-slate-950">
        <div className="w-full sm:w-auto px-1 py-1 pointer-events-auto flex items-center justify-between sm:justify-start gap-2">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-slate-100 break-words">{title || (frame ? frame.obs_id : 'Astronomical Viewer')}</h3>
            <p className="text-xs text-slate-300 tabular-nums break-words">
              {subtitle || (frame ? `${frame.detector} • ${frame.utc_date?.split('T')[0] || ''}` : 'Select an observation')}
            </p>
            {frame && <p className="text-[10px] sm:text-[11px] text-slate-300 break-words">Image source: {imageProvenanceLabel(frame.image_provenance)}</p>}
            {frame?.is_synthetic && (
              <span className="inline-block mt-0.5 px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-amber-500/20 text-amber-200 border border-amber-500/40">
                Synthetic image · archive cutout unavailable
              </span>
            )}
          </div>
        </div>

        {/* Viewer Mode Switcher: SPHEREx Canvas vs Aladin Lite Sky Context */}
        <div
          role="tablist"
          aria-label="Astronomical viewer display mode"
          className="w-full sm:w-auto grid grid-cols-2 sm:flex bg-slate-900/90 backdrop-blur-md border border-slate-800 p-1 rounded-xl pointer-events-auto items-center gap-1 shadow-lg"
        >
          <button
            role="tab"
            aria-selected={viewerMode === 'canvas'}
            aria-label="Switch to SPHEREx quantitative canvas view"
            onClick={() => {
              setViewerMode('canvas');
              setAnnouncement('Switched to SPHEREx quantitative canvas');
            }}
            className={`px-2.5 sm:px-3 py-1 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1.5 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
              viewerMode === 'canvas'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm font-semibold'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Sliders className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span className="truncate">Canvas</span>
          </button>
          <button
            role="tab"
            aria-selected={viewerMode === 'aladin'}
            aria-label="Switch to Aladin Lite multi-wavelength sky context view"
            onClick={() => {
              setViewerMode('aladin');
              setAnnouncement('Switched to Aladin Lite multi-wavelength sky context');
            }}
            className={`px-2.5 sm:px-3 py-1 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1.5 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
              viewerMode === 'aladin'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm font-semibold'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Globe className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span className="hidden sm:inline">Aladin context</span>
            <span className="sm:hidden truncate">Sky Context</span>
          </button>
        </div>


      </div>

      {targetId && frame && !frame.is_synthetic && frame.image_provenance !== 'local_fixture' && (
        <div className="field-evidence shrink-0 px-4 py-2 text-xs text-slate-300 border-b">
          {prediction ? <>
            {viewerMode === 'canvas' && prediction.pixel?.inside && <span aria-hidden="true" className="text-amber-300">□ </span>}
            Catalog prediction at exposure · {prediction.ra.toFixed(5)}°, {prediction.dec.toFixed(5)}°
            {' · '}{prediction.pixel ? (prediction.pixel.inside ? 'Inside FITS field' : 'Outside FITS field') : 'Footprint unavailable'}
            {' · '}Source identity unconfirmed. <a className="underline text-cyan-300" href={prediction.reference_url}>Catalog reference</a>
          </> : 'Exposure-epoch prediction unavailable. Source identity unconfirmed.'}
          <details className="mt-1">
            <summary className="cursor-pointer text-amber-200">Target photometry unavailable</summary>
            <div className="mt-1 space-y-1">
              {viewerMode === 'canvas' && showCrosshair && <p>The blue crosshair marks the cutout center.</p>}
              <p>{photometry?.reason ?? 'A real exposure and a usable epoch prediction are needed for a field assessment.'}</p>
              {photometry && (
                <p>
                  {photometry.epsf_present ? 'ePSF extension present' : 'No ePSF extension'}
                  {photometry.core_pixels != null && ` · ${photometry.usable_core_pixels}/${photometry.core_pixels} usable core pixels · ${photometry.background_pixels} usable annulus pixels`}.
                </p>
              )}
              {(targetId === 'rw_aurigae' || targetId === 'epsilon_indi_b') &&
                <p>The catalog components require a blend model.</p>}
              <p>A target flux requires a validated source fit, matched calibration, and a check for nearby sources.</p>
            </div>
          </details>
        </div>
      )}
      {viewerMode === 'aladin' && targetRa != null && targetDec != null ? (
        <AladinViewer
          ra={targetRa}
          dec={targetDec}
          fov={targetFov ?? 0.04}
          footprint={frame?.footprint_icrs_deg ?? null}
        />
      ) : viewerMode === 'aladin' ? (
        <div className="flex-1 flex items-center justify-center p-6 text-sm text-slate-300" role="status">Search for coordinates to open sky context.</div>
      ) : !frame && !loading && emptyFieldPreview ? (
        emptyFieldPreview
      ) : (
        <>
          {/* Canvas Area with Keyboard Focus & Navigation */}
          <div
            tabIndex={0}
            role="region"
            aria-label="SPHEREx Astronomical Canvas Viewer. Use arrow keys to pan, plus or minus to zoom, and zero to reset view."
            aria-describedby="canvas-keyboard-help"
            onKeyDown={handleKeyDown}
            className="flex-1 instrument-canvas min-h-[220px] w-full h-full cursor-grab active:cursor-grabbing relative flex items-center justify-center outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-inset"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
          >
            <canvas ref={canvasRef} className="absolute inset-0 w-full h-full block" />

            {loading && (
              <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm flex flex-col items-center justify-center gap-2 z-30">
                <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-xs text-cyan-300 font-mono">Loading observation…</span>
              </div>
            )}

            {!frame && !loading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-4 text-slate-400 gap-2 p-4 text-center pointer-events-none">
                <Crosshair className="w-8 h-8 sm:w-10 sm:h-10 opacity-40 text-cyan-400" />
                <p className="text-xs max-w-[260px] sm:max-w-xs text-center text-slate-300 leading-relaxed">
                  No observation loaded. Select a target preset or enter sky coordinates.
                </p>
              </div>
            )}
          </div>

          {/* Image display toolbar */}
          <div className="image-toolbar shrink-0 z-20 flex flex-wrap items-center justify-between gap-2 px-2.5 sm:px-3 py-2 border-t">
            <div
              role="group"
              aria-label="Image stretch and palette controls"
              className="w-full sm:w-auto bg-slate-900/90 backdrop-blur-md border border-slate-800 p-1 rounded-lg pointer-events-auto flex flex-wrap items-center justify-between sm:justify-start gap-1 sm:gap-1.5 text-xs"
            >
              <div className="flex items-center gap-1 px-1.5 sm:px-2 py-0.5 sm:border-r border-slate-800 text-slate-300 font-medium shrink-0">
                <Sliders className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                <span>Stretch<span className="hidden sm:inline"> (display contrast)</span>:</span>
              </div>
              <div className="flex items-center gap-1">
                {(['asinh', 'zscale', 'linear'] as const).map((s) => (
                  <button
                    key={s}
                    aria-pressed={stretch === s}
                    aria-label={`Apply ${s} display stretch preview`}
                    onClick={() => {
                      setStretch(s);
                      setAnnouncement(`Display stretch set to ${s}`);
                    }}
                    className={`px-2 py-0.5 sm:py-1 rounded text-[11px] font-mono capitalize transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                      stretch === s
                        ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/30'
                        : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>

              <div className="hidden sm:block h-4 w-px bg-slate-800 mx-1" />

              {/* Colormap toggle */}
              <button
                onClick={() => {
                  const nextColormap = colormap === 'inferno' ? 'grayscale' : 'inferno';
                  setColormap(nextColormap);
                  setAnnouncement(`Color palette set to ${nextColormap}`);
                }}
                aria-label={`Toggle colormap. Current: ${colormap}`}
                className={`px-2 py-0.5 sm:py-1 rounded text-[11px] flex items-center gap-1 transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ml-auto sm:ml-0 ${
                  colormap === 'inferno'
                    ? 'bg-amber-500/20 text-amber-200 font-semibold border border-amber-500/40'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <Palette className="w-3 h-3 text-cyan-400 shrink-0" />
                <span>{colormap === 'inferno' ? 'Inferno' : 'Grayscale'}</span>
              </button>
            </div>
            {showCatalog && <div className="w-full text-[11px] text-slate-300 break-words" role="status">
              <p>{targetRa == null || targetDec == null ? 'Search for coordinates to load reference sources.' : loadingCatalog ? 'Loading Gaia DR3…' : catalogQueryError ? 'The Gaia catalog request failed. Turn the overlay off and on to retry.' : catalogSources.length === 0 ? 'No Gaia DR3 sources returned in this search.' : catalogError || (!frame ? 'Select an observation to project reference positions.' : catalogPixels.length === 0 ? 'Projecting reference positions onto the image…' : !catalogPixels.some(Boolean) ? 'No returned reference positions fall within this image.' : 'Gaia markers [PM] use approximate proper-motion shifts to the exposure midpoint; [2016] lacks a usable shift. Parallax and radial motion are not modeled. A marker does not confirm identity.')}</p>
            </div>}
            <div className="w-full sm:w-auto bg-slate-900/90 backdrop-blur-md border border-slate-800 px-2.5 sm:px-3 py-1 rounded-md pointer-events-auto text-[11px] font-mono text-slate-300 flex flex-wrap items-center justify-between sm:justify-start gap-x-2 gap-y-1">
              <span>Zoom: {(zoom * 100).toFixed(0)}% of fit</span>
              {frame && (
                <>
                  <span className="text-slate-600">|</span>
                  <span>Dims: {frame.dimensions.join('×')} px</span>
                  <span className="text-slate-600">|</span>
                  <span>FOV: ~{(frame.dimensions[0] * 6.2 / 60).toFixed(1)}′</span>
                  {mousePos && (
                    <>
                      <span className="hidden sm:inline text-slate-600">|</span>
                      <span className="hidden sm:inline text-cyan-400">Cursor: [{mousePos.x}, {mousePos.y}]</span>
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
              className="w-full sm:w-auto bg-slate-900/90 backdrop-blur-md border border-slate-800 p-1 rounded-lg pointer-events-auto flex items-center justify-between sm:justify-end gap-1"
            >
              {setShowCatalog && (
                <button
                  onClick={() => {
                    setShowCatalog(!showCatalog);
                    setAnnouncement(!showCatalog ? 'Reference stars enabled' : 'Reference stars disabled');
                  }}
                  aria-pressed={showCatalog}
                  aria-label={`Toggle Reference Stars: ${catalogSources[0]?.provenance || 'Gaia DR3'}`}
                  title={`Toggle Reference Stars: ${catalogSources[0]?.provenance || 'Gaia DR3'}`}
                  className={`px-2 py-1 rounded text-[11px] font-mono flex items-center gap-1 transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none shrink-0 ${
                    showCatalog
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                  }`}
                >
                  <Star className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                  <span>
                    <span className="hidden sm:inline">
                      Gaia DR3
                    </span>
                    <span className="sm:hidden">
                      Gaia
                    </span>
                    {catalogSources.length > 0 ? ` (${catalogSources.length})` : ''}
                  </span>
                </button>
              )}
              {showCatalog && (
                <button type="button" aria-pressed={showCatalogLabels}
                  aria-label="Show Gaia source labels on image"
                  title="Show Gaia source labels on image"
                  onClick={() => setShowCatalogLabels(value => !value)}
                  className={`px-2 py-1 rounded text-[11px] font-mono focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${showCatalogLabels ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-300 hover:text-white hover:bg-slate-800/60'}`}>
                  Labels
                </button>
              )}

              <div className="h-4 w-px bg-slate-800 mx-0.5" />

              <div className="flex items-center gap-0.5 sm:gap-1">
                <button
                  onClick={() => {
                    setShowCrosshair(!showCrosshair);
                    setAnnouncement(!showCrosshair ? 'Celestial crosshair enabled' : 'Celestial crosshair disabled');
                  }}
                  aria-pressed={showCrosshair}
                  aria-label="Toggle image-center crosshair"
                  title="Toggle image-center crosshair"
                  className={`p-1 sm:p-1.5 rounded transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                    showCrosshair ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                  }`}
                >
                  <Crosshair className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
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
                  className="p-1 sm:p-1.5 text-slate-300 hover:text-white hover:bg-slate-800 rounded transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
                >
                  <ZoomIn className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
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
                  className="p-1 sm:p-1.5 text-slate-300 hover:text-white hover:bg-slate-800 rounded transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
                >
                  <ZoomOut className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                </button>
                <button
                  onClick={() => {
                    resetView();
                    setAnnouncement('View reset to default 100% zoom and center position');
                  }}
                  aria-label="Reset View"
                  title="Reset View (0)"
                  className="p-1 sm:p-1.5 text-slate-300 hover:text-white hover:bg-slate-800 rounded transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
                >
                  <RotateCcw className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
