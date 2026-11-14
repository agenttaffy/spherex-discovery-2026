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
    <div className="h-20 bg-slate-950/90 border-t border-slate-800 px-6 flex items-center justify-between gap-6 z-20">
      {/* Playback Controls */}
      <div className="flex items-center space-x-2">
        <button
          onClick={() => onSelectIndex(Math.max(0, currentIndex - 1))}
          disabled={currentIndex <= 0}
          title="Previous Epoch"
          className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg disabled:opacity-40 transition"
        >
          <SkipBack className="w-4 h-4" />
        </button>

        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className={`p-2.5 rounded-lg font-semibold transition flex items-center justify-center ${
            isPlaying
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'bg-cyan-600 text-white hover:bg-cyan-500 shadow-md shadow-cyan-950'
          }`}
          title={isPlaying ? 'Pause Time-Lapse' : 'Play Time-Lapse'}
        >
          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-white" />}
        </button>

        <button
          onClick={() => onSelectIndex(Math.min(observations.length - 1, currentIndex + 1))}
          disabled={currentIndex >= observations.length - 1}
          title="Next Epoch"
          className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg disabled:opacity-40 transition"
        >
          <SkipForward className="w-4 h-4" />
        </button>

        <button
          onClick={() => setIsLoop(!isLoop)}
          title="Loop Animation"
          className={`p-2 rounded-lg transition ${
            isLoop ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-500 hover:text-slate-300'
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
          className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 border transition ${
            isBlinkActive
              ? 'bg-fuchsia-950/60 border-fuchsia-500 text-fuchsia-300'
              : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
          }`}
        >
          <Zap className="w-3.5 h-3.5" />
          <span>Blink Mode</span>
        </button>
      </div>

      {/* Scrubber Timeline */}
      <div className="flex-1 flex flex-col justify-center">
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1.5">
          <span className="flex items-center gap-2">
            <span className="text-cyan-400 font-semibold">Epoch {currentIndex + 1} of {observations.length}</span>
            {currentObs?.utc_date && (
              <span className="text-slate-300 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                {currentObs.utc_date} UTC
              </span>
            )}
          </span>
          <span className="text-slate-500">{currentObs?.detector}</span>
        </div>

        {/* Frame markers / Scrubber bar */}
        <div className="relative w-full h-2 bg-slate-900 rounded-full cursor-pointer flex items-center">
          <div
            className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 rounded-full transition-all duration-150"
            style={{ width: `${((currentIndex + 1) / observations.length) * 100}%` }}
          />
          {observations.map((obs, idx) => (
            <button
              key={obs.id || idx}
              onClick={() => onSelectIndex(idx)}
              title={`${obs.utc_date || ''} (${obs.detector})`}
              className={`absolute w-3 h-3 -ml-1.5 rounded-full border transition-all ${
                idx === currentIndex
                  ? 'bg-cyan-400 border-white scale-125 z-10 shadow-sm shadow-cyan-400'
                  : 'bg-slate-800 border-slate-600 hover:bg-slate-600'
              }`}
              style={{ left: `${(idx / (observations.length - 1 || 1)) * 100}%` }}
            />
          ))}
        </div>
      </div>

      {/* FPS selector */}
      <div className="flex items-center space-x-1 text-xs">
        <span className="text-[11px] text-slate-500 font-mono mr-1">Speed:</span>
        {[1, 2, 4].map((speed) => (
          <button
            key={speed}
            onClick={() => setFps(speed)}
            className={`px-2 py-1 rounded text-[11px] font-mono transition ${
              fps === speed
                ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {speed}x
          </button>
        ))}
      </div>
    </div>
  );
};
