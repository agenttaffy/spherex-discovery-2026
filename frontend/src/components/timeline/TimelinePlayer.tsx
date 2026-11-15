import React, { useEffect, useState } from 'react';
import { Play, Pause, SkipBack, SkipForward, Repeat, Zap } from 'lucide-react';
import { ObservationRecord } from '../../types/astronomy';

interface TimelinePlayerProps {
  observations: ObservationRecord[];
  currentIndex: number;
  onSelectIndex: (index: number) => void;
  isBlinkActive: boolean;
  setIsBlinkActive: (active: boolean) => void;
}

export const TimelinePlayer: React.FC<TimelinePlayerProps> = ({
  observations,
  currentIndex,
  onSelectIndex,
  isBlinkActive,
  setIsBlinkActive,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [fps, setFps] = useState(2);
  const [isLoop, setIsLoop] = useState(true);

  // Animation interval
  useEffect(() => {
    if (!isPlaying || observations.length === 0) return;

    const interval = setInterval(() => {
      let next: number;
      if (isBlinkActive && observations.length >= 2) {
        next = currentIndex === 0 ? 1 : 0;
      } else {
        next = currentIndex + 1;
        if (next >= observations.length) {
          if (isLoop) {
            next = 0;
          } else {
            setIsPlaying(false);
            return;
          }
        }
      }
      onSelectIndex(next);
    }, 1000 / fps);

    return () => clearInterval(interval);
  }, [isPlaying, fps, isLoop, observations.length, isBlinkActive, currentIndex, onSelectIndex]);

  if (observations.length === 0) return null;

  const currentObs = observations[currentIndex];

  return (
    <div
      role="region"
      aria-label="Observation timeline player"
      className="bg-slate-950/90 border-t border-slate-800 px-3 sm:px-6 py-2.5 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 z-20"
    >
      {/* Playback Controls & Blink */}
      <div className="flex items-center justify-between sm:justify-start gap-1.5 shrink-0" role="toolbar" aria-label="Timeline playback controls">
        <button
          onClick={() => onSelectIndex(Math.max(0, currentIndex - 1))}
          disabled={currentIndex <= 0}
          aria-label="Previous observation epoch"
          title="Previous Epoch"
          className="p-1.5 sm:p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg disabled:opacity-40 transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
        >
          <SkipBack className="w-4 h-4" />
        </button>

        <button
          onClick={() => setIsPlaying(!isPlaying)}
          aria-label={isPlaying ? 'Pause time-lapse' : 'Play time-lapse'}
          title={isPlaying ? 'Pause Time-Lapse' : 'Play Time-Lapse'}
          className={`p-2 sm:p-2.5 rounded-lg font-semibold transition flex items-center justify-center focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
            isPlaying
              ? 'bg-amber-500/20 text-amber-200 border border-amber-500/40'
              : 'bg-cyan-700 text-white hover:bg-cyan-800 shadow-md shadow-cyan-950'
          }`}
        >
          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-white" />}
        </button>

        <button
          onClick={() => onSelectIndex(Math.min(observations.length - 1, currentIndex + 1))}
          disabled={currentIndex >= observations.length - 1}
          aria-label="Next observation epoch"
          title="Next Epoch"
          className="p-1.5 sm:p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg disabled:opacity-40 transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
        >
          <SkipForward className="w-4 h-4" />
        </button>

        <button
          onClick={() => setIsLoop(!isLoop)}
          aria-pressed={isLoop}
          aria-label="Loop playback animation"
          title="Loop Animation"
          className={`p-1.5 sm:p-2 rounded-lg transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
            isLoop ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Repeat className="w-4 h-4" />
        </button>

        {/* Rapid Blink Mode */}
        <button
          onClick={() => {
            const nextBlink = !isBlinkActive;
            setIsBlinkActive(nextBlink);
            if (nextBlink) setIsPlaying(true);
          }}
          aria-pressed={isBlinkActive}
          aria-label="Toggle rapid 2-epoch blink comparator"
          title="Toggle rapid blink comparison between first two epochs"
          className={`px-2 sm:px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 border transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
            isBlinkActive
              ? 'bg-fuchsia-950/60 border-fuchsia-500 text-fuchsia-200'
              : 'bg-slate-900 border-slate-800 text-slate-300 hover:text-white'
          }`}
        >
          <Zap className="w-3.5 h-3.5 text-fuchsia-400" />
          <span className="hidden xs:inline">Blink Mode</span>
        </button>
      </div>

      {/* Scrubber Timeline */}
      <div className="flex-1 flex flex-col justify-center min-w-0">
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-300 mb-1.5">
          <span className="flex items-center gap-2 truncate">
            <span className="text-cyan-300 font-semibold">Epoch {currentIndex + 1}/{observations.length}</span>
            {currentObs?.utc_date && (
              <span className="text-slate-200 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800 truncate">
                {currentObs.utc_date.split('T')[0]}
              </span>
            )}
          </span>
          <span className="text-indigo-300 font-semibold shrink-0 ml-2">{currentObs?.detector}</span>
        </div>

        {/* Native range provides a single keyboard stop for any number of epochs. */}
        <input
          type="range"
          aria-label="Observation timeline epoch slider"
          min={1}
          max={observations.length}
          step={1}
          value={currentIndex + 1}
          aria-valuetext={`Epoch ${currentIndex + 1} of ${observations.length}, ${currentObs?.detector}, ${currentObs?.utc_date || ''}`}
          onChange={(event) => onSelectIndex(Number(event.target.value) - 1)}
          className="w-full h-5 cursor-pointer accent-cyan-400 focus-visible:ring-2 focus-visible:ring-cyan-400 rounded"
        />
      </div>

      {/* FPS speed selector */}
      <div className="flex items-center justify-end space-x-1 text-xs shrink-0" role="group" aria-label="Playback frame rate">
        <span className="text-[11px] text-slate-400 font-mono mr-1">Speed:</span>
        {[1, 2, 4].map((speed) => (
          <button
            key={speed}
            onClick={() => setFps(speed)}
            aria-pressed={fps === speed}
            aria-label={`Set playback speed to ${speed} frames per second`}
            className={`px-2 py-0.5 rounded text-[11px] font-mono transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
              fps === speed
                ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            {speed}x
          </button>
        ))}
      </div>
    </div>
  );
};
