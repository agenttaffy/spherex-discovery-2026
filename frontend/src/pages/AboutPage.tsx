import React from 'react';
import { Telescope, BookOpen, Award, ExternalLink } from 'lucide-react';

export const AboutPage: React.FC = () => {
  return (
    <div className="flex-1 bg-slate-950 p-8 overflow-y-auto text-slate-300">
      <div className="max-w-4xl mx-auto space-y-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950 border border-cyan-800 text-cyan-300 text-xs font-semibold mb-3">
            <Award className="w-3.5 h-3.5" />
            NASA Space Apps Challenge 2026 Entry
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            SPHEREx Discovery: Time-Domain Astronomical Observatory
          </h1>
          <p className="text-sm text-slate-400 mt-2 leading-relaxed">
            NASA's Spectro-Photometer for the History of the Universe, Epoch of Reionization and Ices Explorer (SPHEREx)
            is conducting an unprecedented all-sky infrared spectroscopic survey. By revisiting every point on the sky every six months across four distinct survey sweeps, SPHEREx enables time-domain infrared astronomy on a cosmic scale.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Telescope className="w-4 h-4 text-cyan-400" />
              Instrument &amp; Linear Variable Filters
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              SPHEREx incorporates six 2048×2048 focal plane arrays with Linear Variable Filters (LVF). Unlike conventional broad-band filter wheels, LVFs continuously vary the transmitted wavelength across the physical surface of the detector, providing 102 distinct spectral channels from 0.75 µm to 5.0 µm.
            </p>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-cyan-400" />
              Scientific Calibration &amp; Integrity
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              All pixel intensities are calibrated in MegaJanskys per steradian (MJy/sr). Display stretch functions (asinh and ZScale) operate exclusively on browser-rendered previews without modifying scientific floating-point data arrays.
            </p>
          </div>
        </div>

        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-white">Official Competition Target Analysis</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="font-semibold text-cyan-300 block">Barnard's Star</span>
              <span className="text-slate-400 text-[11px]">10.3″/yr proper motion. 1-year baseline between DR1 and QR3 yields ~1.66 px visible displacement.</span>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="font-semibold text-cyan-300 block">RW Aurigae</span>
              <span className="text-slate-400 text-[11px]">Classical T Tauri variable with circumstellar dust obscuration causing multi-magnitude IR dimming.</span>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="font-semibold text-cyan-300 block">WISE 0855</span>
              <span className="text-slate-400 text-[11px]">Coldest known brown dwarf (~250 K), prominent in mid-IR D4/D6 channels.</span>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="font-semibold text-cyan-300 block">Epsilon Indi B</span>
              <span className="text-slate-400 text-[11px]">Binary brown dwarf system with 4.7″/yr proper motion and mutual orbital velocity.</span>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="font-semibold text-cyan-300 block">R Draconis</span>
              <span className="text-slate-400 text-[11px]">Mira-type long-period pulsating red giant with large infrared amplitude swings.</span>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-800 pt-6 space-y-3 text-xs text-slate-400">
          <h4 className="font-semibold text-slate-300">Data Citations &amp; Provenance</h4>
          <p>
            SPHEREx data products accessed via the NASA/IPAC Infrared Science Archive (IRSA), California Institute of Technology / Jet Propulsion Laboratory under NASA contract.
          </p>
          <div className="flex flex-wrap gap-4 text-cyan-400 font-mono text-[11px]">
            <a href="https://doi.org/10.26131/IRSA678" target="_blank" rel="noreferrer" className="hover:underline flex items-center gap-1">
              DOI: 10.26131/IRSA678 (DR1 Spectral Images) <ExternalLink className="w-3 h-3" />
            </a>
            <a href="https://doi.org/10.26131/IRSA679" target="_blank" rel="noreferrer" className="hover:underline flex items-center gap-1">
              DOI: 10.26131/IRSA679 (DR1 All-Sky Cube) <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
