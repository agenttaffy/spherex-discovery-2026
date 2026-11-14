import React, { useState } from 'react';
import { X, ChevronRight, ChevronLeft, Telescope, Activity, Orbit, Award, CheckCircle } from 'lucide-react';

interface GuidedTourModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectPreset?: (presetId: string) => void;
}

export const GuidedTourModal: React.FC<GuidedTourModalProps> = ({
  isOpen,
  onClose,
  onSelectPreset,
}) => {
  const [currentStep, setCurrentStep] = useState(0);

  if (!isOpen) return null;

  const steps = [
    {
      title: 'SPHEREx Mission & Linear Variable Filters (LVF)',
      icon: <Telescope className="w-5 h-5 text-cyan-400" />,
      content: (
        <div className="space-y-3 text-xs leading-relaxed text-slate-300">
          <p>
            NASA's <strong className="text-white">SPHEREx</strong> (Spectro-Photometer for the History of the Universe, Epoch of Reionization and Ices) is an all-sky near-infrared observatory mapping the entire cosmos every 6 months across 102 spectral bands from <strong className="text-cyan-300">0.75 μm to 5.0 μm</strong>.
          </p>
          <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
            <span className="font-semibold text-cyan-300 block text-[11px] uppercase tracking-wider">
              Critical Scientific Principle: Linear Variable Filters
            </span>
            <p>
              Unlike traditional telescopes with discrete broadband glass filters, SPHEREx detectors (D1 to D6) use <strong className="text-slate-100">Linear Variable Filters</strong> glued directly atop the detector arrays. The observed wavelength shifts continuously across each pixel column.
            </p>
            <p className="text-amber-300/90 font-mono text-[11px]">
              ⚠️ Scientific Rule: Pixel-by-pixel temporal subtraction (I₂ − I₁) is ONLY valid between identical detector bands and aligned celestial pointings. Subtraction across differing detectors creates spurious chromatic artifacts.
            </p>
          </div>
        </div>
      ),
    },
    {
      title: 'Distinguishing Moving Objects vs. Variable Stars',
      icon: <Activity className="w-5 h-5 text-amber-400" />,
      content: (
        <div className="space-y-3 text-xs leading-relaxed text-slate-300">
          <p>
            Astronomers hunting for new solar system bodies, rogue asteroids, and nearby brown dwarfs rely on time-domain differencing. Our platform computes calibrated mathematical subtractions ($I_2 - I_1$):
          </p>
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="font-bold text-amber-400 block text-xs mb-1">
                Moving Objects (Dipole)
              </span>
              <p className="text-[11px] text-slate-400">
                A moving body leaves a characteristic <strong className="text-slate-200">dipole signature</strong>: a dark negative hole at Epoch 1 coordinates and a bright positive peak at Epoch 2 coordinates. The astrometric vector engine measures the proper motion in arcsec/year.
              </p>
            </div>
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="font-bold text-cyan-400 block text-xs mb-1">
                Variable Stars (Monopole)
              </span>
              <p className="text-[11px] text-slate-400">
                Pulsating red giants and young stars remain stationary in pixel space ($\Delta x = 0$). Their difference image is a centered positive or negative monopole, and their fluctuations are tracked in the multi-epoch Light Curve dock.
              </p>
            </div>
          </div>
        </div>
      ),
    },
    {
      title: 'Official Challenge Test Targets',
      icon: <Orbit className="w-5 h-5 text-indigo-400" />,
      content: (
        <div className="space-y-2 text-xs leading-relaxed text-slate-300">
          <p className="mb-2">
            The challenge provides 5 official target fields. Click any target to immediately explore its verified real SPHEREx observations:
          </p>
          <div className="space-y-1.5 font-mono text-[11px]">
            <div
              onClick={() => { onSelectPreset?.('barnards_star'); onClose(); }}
              className="p-2.5 rounded-lg bg-slate-950 hover:bg-cyan-950/40 border border-slate-800 hover:border-cyan-800/80 cursor-pointer flex justify-between items-center transition"
            >
              <div>
                <span className="font-bold text-cyan-300 block">1. Barnard's Star (Gl 699)</span>
                <span className="text-[10px] text-slate-400 font-sans">Fastest proper motion star known (10.3″/yr) • Visible 1.6-pixel displacement</span>
              </div>
              <ChevronRight className="w-4 h-4 text-cyan-400 shrink-0" />
            </div>

            <div
              onClick={() => { onSelectPreset?.('wise_0855'); onClose(); }}
              className="p-2.5 rounded-lg bg-slate-950 hover:bg-cyan-950/40 border border-slate-800 hover:border-cyan-800/80 cursor-pointer flex justify-between items-center transition"
            >
              <div>
                <span className="font-bold text-amber-300 block">2. WISE 0855-0714</span>
                <span className="text-[10px] text-slate-400 font-sans">Coldest sub-stellar brown dwarf (~250 K) • Strong D4/D5 infrared detection</span>
              </div>
              <ChevronRight className="w-4 h-4 text-cyan-400 shrink-0" />
            </div>

            <div
              onClick={() => { onSelectPreset?.('rw_aurigae'); onClose(); }}
              className="p-2.5 rounded-lg bg-slate-950 hover:bg-cyan-950/40 border border-slate-800 hover:border-cyan-800/80 cursor-pointer flex justify-between items-center transition"
            >
              <div>
                <span className="font-bold text-rose-300 block">3. RW Aurigae</span>
                <span className="text-[10px] text-slate-400 font-sans">Violent T Tauri disk disruption • Dramatic multi-magnitude photometric variability</span>
              </div>
              <ChevronRight className="w-4 h-4 text-cyan-400 shrink-0" />
            </div>

            <div
              onClick={() => { onSelectPreset?.('r_draconis'); onClose(); }}
              className="p-2.5 rounded-lg bg-slate-950 hover:bg-cyan-950/40 border border-slate-800 hover:border-cyan-800/80 cursor-pointer flex justify-between items-center transition"
            >
              <div>
                <span className="font-bold text-purple-300 block">4. R Draconis</span>
                <span className="text-[10px] text-slate-400 font-sans">Mira-type pulsating red giant (245-day period) • Large flux amplitude</span>
              </div>
              <ChevronRight className="w-4 h-4 text-cyan-400 shrink-0" />
            </div>

            <div
              onClick={() => { onSelectPreset?.('epsilon_indi_b'); onClose(); }}
              className="p-2.5 rounded-lg bg-slate-950 hover:bg-cyan-950/40 border border-slate-800 hover:border-cyan-800/80 cursor-pointer flex justify-between items-center transition"
            >
              <div>
                <span className="font-bold text-teal-300 block">5. Epsilon Indi B</span>
                <span className="text-[10px] text-slate-400 font-sans">Binary brown dwarf system • Significant proper motion (4.7″/yr) & brown dwarf spectra</span>
              </div>
              <ChevronRight className="w-4 h-4 text-cyan-400 shrink-0" />
            </div>
          </div>
        </div>
      ),
    },
    {
      title: 'NASA Space Apps Challenge 2026 Judging Alignment',
      icon: <Award className="w-5 h-5 text-emerald-400" />,
      content: (
        <div className="space-y-3 text-xs leading-relaxed text-slate-300">
          <p>
            SPHEREx Discovery is built strictly to the criteria defined in Challenge Prompt 1:
          </p>
          <div className="space-y-2 font-sans">
            <div className="flex items-start gap-2 bg-slate-950 p-2.5 rounded border border-slate-800">
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-slate-100">Live NASA IRSA SIA2 Integration & 100% Offline Fallback:</span>
                <p className="text-[11px] text-slate-400">Queries the live IPAC SIA2 service with 22 cached real DR1/QR3 Level 2 FITS cutouts for guaranteed presentation reliability.</p>
              </div>
            </div>
            <div className="flex items-start gap-2 bg-slate-950 p-2.5 rounded border border-slate-800">
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-slate-100">Astropy Celestial WCS & Calibrated Differencing:</span>
                <p className="text-[11px] text-slate-400">Accurate coordinate mapping, sub-pixel FFT image registration, and real physical surface brightness in MJy/sr.</p>
              </div>
            </div>
            <div className="flex items-start gap-2 bg-slate-950 p-2.5 rounded border border-slate-800">
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-slate-100">Comprehensive Traceability & Documentation:</span>
                <p className="text-[11px] text-slate-400">Full technical documentation suite in docs/ covering architecture, data provenance, API references, and 3-minute demo script.</p>
              </div>
            </div>
          </div>
        </div>
      ),
    },
  ];

  const step = steps[currentStep];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 bg-slate-950/80 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center">
              {step.icon}
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">{step.title}</h3>
              <span className="text-[10px] text-cyan-400 font-mono">
                Step {currentStep + 1} of {steps.length}
              </span>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 bg-slate-900/90 min-h-[220px]">
          {step.content}
        </div>

        {/* Footer Navigation */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between">
          <button
            onClick={() => setCurrentStep((s) => Math.max(0, s - 1))}
            disabled={currentStep === 0}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg flex items-center gap-1 transition ${
              currentStep === 0
                ? 'opacity-40 cursor-not-allowed text-slate-500'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-200'
            }`}
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            Previous
          </button>

          {/* Step dots */}
          <div className="flex items-center space-x-1.5">
            {steps.map((_, i) => (
              <div
                key={i}
                onClick={() => setCurrentStep(i)}
                className={`w-2 h-2 rounded-full cursor-pointer transition ${
                  i === currentStep ? 'bg-cyan-400 w-4' : 'bg-slate-700 hover:bg-slate-500'
                }`}
              />
            ))}
          </div>

          {currentStep < steps.length - 1 ? (
            <button
              onClick={() => setCurrentStep((s) => Math.min(steps.length - 1, s + 1))}
              className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white flex items-center gap-1 transition"
            >
              Next
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={onClose}
              className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1 transition shadow-lg shadow-emerald-900/30"
            >
              Start Exploring
              <CheckCircle className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
