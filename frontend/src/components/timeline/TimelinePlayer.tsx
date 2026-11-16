import React, { useEffect, useState } from 'react';
import { Play, Pause, SkipBack, SkipForward, Repeat, Zap } from 'lucide-react';
import { ObservationRecord } from '../../types/astronomy';
import { initialBlinkPair, nextBlinkIndex } from './blinkSelection';

interface TimelinePlayerProps {
  observations: ObservationRecord[];
  currentIndex: number;
  onSelectIndex: (index: number) => void;
  isBlinkActive: boolean;
  setIsBlinkActive: (active: boolean) => void;
  loadingFrame?: boolean;
  frameError?: boolean;
}

export const TimelinePlayer: React.FC<TimelinePlayerProps> = ({
  observations,
  currentIndex,
  onSelectIndex,
  isBlinkActive,
  setIsBlinkActive,
  loadingFrame = false,
  frameError = false,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [fps, setFps] = useState(2);
  const [isLoop, setIsLoop] = useState(true);
  const [blinkFirst, setBlinkFirst] = useState(0);
  const [blinkSecond, setBlinkSecond] = useState(1);

  useEffect(() => {
    if (frameError) setIsPlaying(false);
  }, [frameError]);

  // A new search is a new sequence; do not silently start downloading it.
  useEffect(() => {
    setIsPlaying(false);
    setBlinkFirst(0);
    setBlinkSecond(Math.min(1, Math.max(0, observations.length - 1)));
  }, [observations]);

  // Animation interval
  useEffect(() => {
    if (!isPlaying || loadingFrame || frameError || observations.length < 2) return;

    const interval = setInterval(() => {
      let next: number;
      if (isBlinkActive && observations.length >= 2) {
        next = nextBlinkIndex(currentIndex, blinkFirst, blinkSecond);
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
  }, [isPlaying, loadingFrame, frameError, fps, isLoop, observations.length, isBlinkActive, blinkFirst, blinkSecond, currentIndex, onSelectIndex]);

  if (observations.length === 0) return null;

  const currentObs = observations[currentIndex];
  const blinkSelectors = [
    { value: blinkFirst, other: blinkSecond, setValue: setBlinkFirst, label: 'A' },
    { value: blinkSecond, other: blinkFirst, setValue: setBlinkSecond, label: 'B' },
  ];

  return (
    <div
      role="region"
      aria-label="Observation timeline player"
      className="observation-timeline bg-slate-950/90 border-t border-slate-800 px-3 sm:px-6 py-2.5 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 z-20"
    >
      {/* Playback Controls & Blink */}
      <div className="flex items-center justify-between sm:justify-start gap-1.5 shrink-0" role="toolbar" aria-label="Timeline playback controls">
        <button
          onClick={() => onSelectIndex(Math.max(0, currentIndex - 1))}
          disabled={currentIndex <= 0}
          aria-label="Previous observation"
          title="Previous observation"
          className="p-1.5 sm:p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg disabled:opacity-40 transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
        >
          <SkipBack className="w-4 h-4" />
        </button>

        <button
          onClick={() => setIsPlaying(!isPlaying)}
          disabled={observations.length < 2 || frameError}
          aria-label={isPlaying ? 'Pause time-lapse' : 'Play time-lapse'}
          title={isPlaying ? 'Pause Time-Lapse' : 'Play Time-Lapse'}
          className={`playback-primary p-2 sm:p-2.5 rounded-lg font-semibold transition flex items-center justify-center disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
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
          aria-label="Next observation"
          title="Next observation"
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
            if (nextBlink) {
              const [first, second] = initialBlinkPair(currentIndex, observations.length);
              setBlinkFirst(first);
              setBlinkSecond(second);
              setIsPlaying(true);
            }
          }}
          aria-pressed={isBlinkActive}
          disabled={observations.length < 2 || frameError}
          aria-label="Toggle rapid two-frame blink comparator"
          title="Toggle rapid blink comparison between two selected observations"
          className={`px-2 sm:px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 border transition disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
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
        {isPlaying && loadingFrame && <span className="text-xs text-slate-300" role="status">Loading observation… playback will resume when it finishes.</span>}
        <div className="flex items-center justify-between flex-wrap gap-2 text-xs tabular-nums text-slate-300 mb-1.5">
          <span className="flex items-center gap-2 truncate">
            <span className="text-cyan-300 font-semibold">Observation {currentIndex + 1}/{observations.length}</span>
            {currentObs?.utc_date && (
              <span className="text-slate-200 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800 truncate">
                {currentObs.utc_date.split('T')[0]}
              </span>
            )}
          </span>
          <select aria-label="Jump to observation by date and detector" className="instrument-input min-w-0 max-w-full"
            value={currentIndex} onChange={event => { setIsPlaying(false); onSelectIndex(Number(event.target.value)); }}>
            {observations.map((observation, index) => (
              <option key={observation.id} value={index}>
                {index + 1}. {observation.utc_date?.split('T')[0] || 'Date unavailable'} · {observation.detector} · {observation.obs_id}
              </option>
            ))}
          </select>
        </div>

        {/* Native range provides a single keyboard stop for any number of epochs. */}
        <input
          type="range"
          aria-label="Observation timeline slider"
          min={1}
          max={observations.length}
          step={1}
          value={currentIndex + 1}
          aria-valuetext={`Observation ${currentIndex + 1} of ${observations.length}, ${currentObs?.detector}, ${currentObs?.utc_date || ''}`}
          onChange={(event) => onSelectIndex(Number(event.target.value) - 1)}
          className="w-full h-5 cursor-pointer accent-cyan-400 focus-visible:ring-2 focus-visible:ring-cyan-400 rounded"
        />
        {isBlinkActive && observations.length >= 2 && (
          <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
            {blinkSelectors.map(({ value, other, setValue, label }) => (
              <label key={label} className="min-w-0 text-slate-300">Blink {label}
                <select className="instrument-input block w-full mt-1" aria-label={`Blink observation ${label}`}
                  value={value} onChange={event => { setIsPlaying(false); setValue(Number(event.target.value)); }}>
                  {observations.map((observation, index) => <option key={observation.id} value={index} disabled={index === other}>
                    {index + 1}. {observation.utc_date?.split('T')[0] || 'Date unavailable'} · {observation.detector} · {observation.obs_id}
                  </option>)}
                </select>
              </label>
            ))}
          </div>
        )}
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
