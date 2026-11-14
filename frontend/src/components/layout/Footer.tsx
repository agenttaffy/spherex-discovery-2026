import React from 'react';
import { ExternalLink, Database, ShieldAlert } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-slate-800 bg-slate-950 px-6 py-4 text-xs text-slate-400 flex flex-col md:flex-row items-center justify-between gap-4">
      <div className="flex items-center space-x-4">
        <span className="flex items-center gap-1.5 text-slate-300">
          <Database className="w-3.5 h-3.5 text-cyan-400" />
          Data: NASA / IPAC IRSA SPHEREx DR1 (DOI: 10.26131/IRSA678) &amp; QR3
        </span>
        <a
          href="https://irsa.ipac.caltech.edu/Missions/spherex.html"
          target="_blank"
          rel="noreferrer"
          className="hover:text-cyan-400 flex items-center gap-1 transition"
        >
          Archive Portal <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      <div className="flex items-center space-x-2 text-[11px] text-slate-500">
        <ShieldAlert className="w-3.5 h-3.5 text-amber-500/80" />
        <span>Calibrated surface brightness in MJy/sr. Display stretches are non-destructive browser previews.</span>
      </div>
    </footer>
  );
};
