import React from 'react';
import { Telescope, Radio, Sparkles, Orbit } from 'lucide-react';

interface HeaderProps {
  irsaConnected: boolean;
  activeTab: 'explorer' | 'blink' | 'diff' | 'about';
  setActiveTab: (tab: 'explorer' | 'blink' | 'diff' | 'about') => void;
}

export const Header: React.FC<HeaderProps> = ({ irsaConnected, activeTab, setActiveTab }) => {
  return (
    <header className="h-16 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-indigo-500/30 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
          <Telescope className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="font-bold text-lg text-slate-100 tracking-tight flex items-center gap-1.5">
              SPHEREx <span className="text-cyan-400">Discovery</span>
            </h1>
            <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800/60">
              NASA Space Apps 2026
            </span>
          </div>
          <p className="text-xs text-slate-400">Time-domain infrared observatory (0.75 – 5.0 µm)</p>
        </div>
      </div>

      {/* Navigation tabs */}
      <nav className="flex items-center space-x-1 bg-slate-900/90 border border-slate-800 p-1 rounded-lg">
        <button
          onClick={() => setActiveTab('explorer')}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition flex items-center gap-1.5 ${
            activeTab === 'explorer'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          <Orbit className="w-3.5 h-3.5" />
          Explorer & Timeline
        </button>
        <button
          onClick={() => setActiveTab('blink')}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition flex items-center gap-1.5 ${
            activeTab === 'blink'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          Blink Comparator
        </button>
        <button
          onClick={() => setActiveTab('diff')}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition flex items-center gap-1.5 ${
            activeTab === 'diff'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          Difference Engine
        </button>
        <button
          onClick={() => setActiveTab('about')}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${
            activeTab === 'about'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          About & Science
        </button>
      </nav>

      {/* NASA Connection Status Indicator */}
      <div className="flex items-center space-x-2 text-xs">
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border ${
          irsaConnected
            ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
            : 'bg-amber-950/40 border-amber-800/60 text-amber-300'
        }`}>
          <Radio className={`w-3.5 h-3.5 ${irsaConnected ? 'animate-pulse text-emerald-400' : 'text-amber-400'}`} />
          <span>{irsaConnected ? 'NASA/IPAC IRSA Live' : 'Demo Cache Active'}</span>
        </div>
      </div>
    </header>
  );
};
