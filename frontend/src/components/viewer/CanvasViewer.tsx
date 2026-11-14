import React, { useRef, useEffect, useState, useCallback } from 'react';
import { FrameResponse } from '../../types/astronomy';
import { ZoomIn, ZoomOut, RotateCcw, Crosshair, Palette, Sliders } from 'lucide-react';

interface CanvasViewerProps {
  frame: FrameResponse | null;
  loading: boolean;
  stretch: string;
  setStretch: (s: string) => void;
  colormap: string;
  setColormap: (c: string) => void;
  title?: string;
  subtitle?: string;
}

export const CanvasViewer: React.FC<CanvasViewerProps> = ({
  frame,
  loading,
  stretch,
  setStretch,
  colormap,
  setColormap,
  title,
  subtitle,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [zoom, setZoom] = useState(1.0);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [showCrosshair, setShowCrosshair] = useState(true);
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null);

  const resetView = useCallback(() => {
    setZoom(1.0);
    setOffset({ x: 0, y: 0 });
  }, []);

  // Redraw image onto canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !frame) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.src = colormap === 'inferno' && frame.colormapped_base64
      ? frame.colormapped_base64
      : frame.image_base64;

    img.onload = () => {
      canvas.width = canvas.parentElement?.clientWidth || 600;
      canvas.height = canvas.parentElement?.clientHeight || 450;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.imageSmoothingEnabled = false; // Nearest neighbor preserves astronomical pixel blocks!

      ctx.save();
      ctx.translate(canvas.width / 2 + offset.x, canvas.height / 2 + offset.y);
      ctx.scale(zoom, zoom);

      // Draw image centered
      const drawW = img.width * 14;
      const drawH = img.height * 14;
      ctx.drawImage(img, -drawW / 2, -drawH / 2, drawW, drawH);

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
  }, [frame, zoom, offset, colormap, showCrosshair]);

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
    <div className="flex-1 flex flex-col bg-slate-950 relative overflow-hidden select-none" ref={containerRef}>
      {/* Top Overlay Controls */}
      <div className="absolute top-3 left-4 right-4 z-20 flex items-center justify-between pointer-events-none">
        <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 px-3 py-1.5 rounded-lg pointer-events-auto flex items-center gap-3">
          <div>
            <h3 className="text-xs font-semibold text-slate-200">{title || (frame ? frame.obs_id : 'Astronomical Viewer')}</h3>
            <p className="text-[10px] text-slate-400 font-mono">
              {subtitle || (frame ? `${frame.detector} • ${frame.utc_date?.split('T')[0] || ''}` : 'Select an observation')}
            </p>
          </div>
        </div>

        {/* Stretch & Visual Filters */}
        <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 p-1 rounded-lg pointer-events-auto flex items-center gap-1.5 text-xs">
          <div className="flex items-center gap-1 px-2 py-0.5 border-r border-slate-800 text-slate-400">
            <Sliders className="w-3.5 h-3.5 text-cyan-400" />
            <span>Stretch:</span>
          </div>
          {(['asinh', 'zscale', 'linear'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStretch(s)}
              className={`px-2 py-1 rounded text-[11px] font-mono capitalize transition ${
                stretch === s
                  ? 'bg-cyan-500/20 text-cyan-300 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {s}
            </button>
          ))}

          <div className="h-4 w-px bg-slate-800 mx-1" />

          {/* Colormap toggle */}
          <button
            onClick={() => setColormap(colormap === 'inferno' ? 'grayscale' : 'inferno')}
            className={`px-2 py-1 rounded text-[11px] flex items-center gap-1 transition ${
              colormap === 'inferno'
                ? 'bg-amber-500/20 text-amber-300 font-semibold border border-amber-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Palette className="w-3 h-3" />
            <span>{colormap === 'inferno' ? 'Inferno' : 'Grayscale'}</span>
          </button>
        </div>
      </div>

      {/* Canvas Area */}
      <div
        className="flex-1 w-full h-full cursor-grab active:cursor-grabbing relative flex items-center justify-center"
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
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 gap-2">
            <Crosshair className="w-10 h-10 opacity-30 text-cyan-400" />
            <p className="text-xs">No observation loaded. Select a target preset or enter sky coordinates.</p>
          </div>
        )}
      </div>

      {/* Bottom Floating Telemetry & Zoom Dock */}
      <div className="absolute bottom-3 left-4 right-4 z-20 flex items-center justify-between pointer-events-none">
        <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 px-3 py-1 rounded-md pointer-events-auto text-[11px] font-mono text-slate-400 flex items-center gap-3">
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
        </div>

        {/* Zoom controls */}
        <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 p-1 rounded-lg pointer-events-auto flex items-center gap-1">
          <button
            onClick={() => setShowCrosshair(!showCrosshair)}
            title="Toggle Celestial Crosshair"
            className={`p-1.5 rounded transition ${
              showCrosshair ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Crosshair className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom((prev) => Math.min(prev * 1.25, 8.0))}
            title="Zoom In"
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom((prev) => Math.max(prev * 0.8, 0.4))}
            title="Zoom Out"
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={resetView}
            title="Reset View"
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
