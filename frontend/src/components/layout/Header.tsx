import React from 'react';
import { Telescope, Radio, Sparkles, Orbit, BookOpen, Share2, Check, Download, Layers } from 'lucide-react';

interface HeaderProps {
  irsaConnected: boolean | null;
  activeTab: 'explorer' | 'blink' | 'diff' | 'about';
  setActiveTab: (tab: 'explorer' | 'blink' | 'diff' | 'about') => void;
  onOpenGuidedTour?: () => void;
  onCopyShareLink?: () => void;
  onExportReport?: () => void;
  copiedLink?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  irsaConnected,
  activeTab,
  setActiveTab,
  onOpenGuidedTour,
  onCopyShareLink,
  onExportReport,
  copiedLink = false,
}) => {
  return (
    <header className="border-b border-slate-800 bg-slate-950/90 backdrop-blur-md px-3 sm:px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 sticky top-0 z-50">
      {/* Brand Identity */}
      <div className="flex items-center space-x-2.5">
        <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-indigo-500/30 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
          <Telescope className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="font-bold text-base sm:text-lg text-slate-100 tracking-tight flex items-center gap-1.5">
              SPHEREx <span className="text-cyan-400">Discovery</span>
            </h1>
            <span className="hidden xs:inline-block text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800/60">
              Space Apps 2026
            </span>
          </div>
          <p className="text-[11px] text-slate-400 hidden sm:block">Time-domain infrared observatory (0.75 – 5.0 µm)</p>
        </div>
      </div>

      {/* Primary Navigation Tabs */}
      <nav
        role="tablist"
        aria-label="Main application view navigation"
        className="flex items-center space-x-1 bg-slate-900/90 border border-slate-800 p-1 rounded-lg overflow-x-auto max-w-full"
      >
        <button
          role="tab"
          aria-selected={activeTab === 'explorer'}
          aria-controls="main-workspace"
          onClick={() => setActiveTab('explorer')}
          className={`px-2.5 sm:px-3 py-1.5 text-xs font-medium rounded-md transition flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none whitespace-nowrap ${
            activeTab === 'explorer'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-semibold'
              : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <Orbit className="w-3.5 h-3.5 text-cyan-400" />
          <span>Explorer</span>
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'blink'}
          aria-controls="main-workspace"
          onClick={() => setActiveTab('blink')}
          className={`px-2.5 sm:px-3 py-1.5 text-xs font-medium rounded-md transition flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none whitespace-nowrap ${
            activeTab === 'blink'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-semibold'
              : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          <span>Blink</span>
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'diff'}
          aria-controls="main-workspace"
          onClick={() => setActiveTab('diff')}
          className={`px-2.5 sm:px-3 py-1.5 text-xs font-medium rounded-md transition flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none whitespace-nowrap ${
            activeTab === 'diff'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-semibold'
              : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          <span>Difference & Stack</span>
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'about'}
          aria-controls="main-workspace"
          onClick={() => setActiveTab('about')}
          className={`px-2.5 sm:px-3 py-1.5 text-xs font-medium rounded-md transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none whitespace-nowrap ${
            activeTab === 'about'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-semibold'
              : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <span>About</span>
        </button>
      </nav>

      {/* Action Buttons & Archive Status */}
      <div className="flex items-center flex-wrap gap-2 text-xs">
        {onOpenGuidedTour && (
          <button
            onClick={onOpenGuidedTour}
            aria-label="Open Guided Tour and Science Guide"
            className="px-2 sm:px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-cyan-500/50 text-slate-200 hover:text-cyan-300 flex items-center gap-1.5 transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
            title="Interactive Walkthrough & Science Guide"
          >
            <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline font-medium">Guide</span>
          </button>
        )}

        {onCopyShareLink && (
          <button
            onClick={onCopyShareLink}
            aria-label="Copy shareable deep-link URL to clipboard"
            className="px-2 sm:px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-cyan-500/50 text-slate-200 hover:text-cyan-300 flex items-center gap-1.5 transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
            title="Copy Shareable Deep-Link URL"
          >
            {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Share2 className="w-3.5 h-3.5" />}
            <span className="hidden sm:inline font-medium">{copiedLink ? 'Copied!' : 'Share'}</span>
          </button>
        )}

        {onExportReport && (
          <button
            onClick={onExportReport}
            aria-label="Export Scientific Discovery Report"
            className="px-2.5 py-1.5 rounded-lg bg-cyan-950/80 border border-cyan-800/80 hover:bg-cyan-900/60 text-cyan-200 flex items-center gap-1.5 transition font-semibold focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
            title="Export Scientific Discovery Report"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden md:inline">Report</span>
          </button>
        )}

        {/* NASA Connection Status Indicator */}
        <div
          role="status"
          aria-label={`Initial archive connection check: ${irsaConnected === null ? 'checking' : irsaConnected ? 'reachable' : 'unavailable'}`}
          title="Initial connection check; individual observations show their own source."
          className={`flex items-center gap-1.5 px-2 sm:px-2.5 py-1 rounded-md border text-[11px] font-mono ${
            irsaConnected
              ? 'bg-emerald-950/50 border-emerald-800/70 text-emerald-300'
              : 'bg-amber-950/50 border-amber-800/70 text-amber-300'
          }`}
        >
          <Radio className={`w-3 h-3 ${irsaConnected ? 'animate-pulse text-emerald-400' : 'text-amber-400'}`} />
          <span className="truncate max-w-[120px] sm:max-w-none">{irsaConnected === null ? 'Checking IRSA' : irsaConnected ? 'IRSA reachable' : 'IRSA check failed'}</span>
        </div>
      </div>
    </header>
  );
};
