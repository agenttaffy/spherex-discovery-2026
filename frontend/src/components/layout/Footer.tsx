import React from 'react';
import { ExternalLink, Database, ShieldAlert } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-slate-800 bg-slate-950 px-3 sm:px-6 py-3 text-xs text-slate-300 flex flex-col md:flex-row items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-3 sm:gap-4">
        <span className="flex items-center gap-1.5 text-slate-200">
          <Database className="w-3.5 h-3.5 text-cyan-400" />
          Data: NASA / IPAC IRSA SPHEREx DR1 (DOI: 10.26131/IRSA678) &amp; QR3
        </span>
        <a
          href="https://irsa.ipac.caltech.edu/Missions/spherex.html"
          target="_blank"
          rel="noreferrer"
          aria-label="Visit NASA/IPAC IRSA SPHEREx Mission Archive Portal in new window"
          className="hover:text-cyan-300 text-slate-300 flex items-center gap-1 transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none rounded px-1"
        >
          Archive Portal <ExternalLink className="w-3 h-3 text-cyan-400" />
        </a>
      </div>

      <div className="flex items-center space-x-2 text-[11px] text-slate-400">
        <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
        <span>Display stretch changes appearance only. Check each frame for source and quality details.</span>
      </div>
    </footer>
  );
};
