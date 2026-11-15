import React, { useState } from 'react';
import { DiscoveryReport } from '../../types/astronomy';
import { FileDown, Copy, Check, X, FileText, ExternalLink, ShieldCheck } from 'lucide-react';

interface DiscoveryReportModalProps {
  report: DiscoveryReport | null;
  isOpen: boolean;
  onClose: () => void;
}

export const DiscoveryReportModal: React.FC<DiscoveryReportModalProps> = ({
  report,
  isOpen,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen || !report) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(report.markdown_report);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadMd = () => {
    const blob = new Blob([report.markdown_report], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${report.report_id}_${report.target.name.replace(/[^a-zA-Z0-9]/g, '_')}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadJson = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${report.report_id}_${report.target.name.replace(/[^a-zA-Z0-9]/g, '_')}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4" role="dialog" aria-modal="true" aria-label="Scientific Discovery Report">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <span>Scientific Discovery Report</span>
                <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-800">
                  {report.report_id}
                </span>
              </h3>
              <p className="text-[11px] text-slate-300">
                {report.target.name} • {report.target.sexagesimal}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close discovery report modal"
            className="p-1 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body / Report Preview */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-950 font-mono text-xs text-slate-300 leading-relaxed space-y-4">
          <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-4 font-mono text-[11px] whitespace-pre-wrap select-all">
            {report.markdown_report}
          </div>

          {/* DOI & Citation Callout */}
          <div className="bg-cyan-950/30 border border-cyan-800/60 rounded-lg p-3 text-[11px] flex items-start gap-2.5 text-cyan-200 font-sans">
            <ShieldCheck className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold block text-slate-100">NASA Provenance & Citation</span>
              SPHEREx data are available through NASA/IPAC IRSA. Results may include cached demonstration observations; check the observation list and source before interpreting them. DR1 citation: <a href="https://doi.org/10.26131/IRSA678" target="_blank" rel="noreferrer" className="underline font-mono text-cyan-300 hover:text-cyan-100 inline-flex items-center gap-0.5">10.26131/IRSA678 <ExternalLink className="w-3 h-3" /></a>.
            </div>
          </div>
        </div>

        {/* Modal Footer / Actions */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between">
          <span className="text-[11px] text-slate-400">
            Export formatted for submission to NASA Space Apps Challenge 2026.
          </span>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleCopy}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? 'Copied!' : 'Copy Markdown'}
            </button>
            <button
              onClick={handleDownloadJson}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition"
            >
              <FileDown className="w-3.5 h-3.5" />
              Download JSON
            </button>
            <button
              onClick={handleDownloadMd}
              className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-cyan-700 hover:bg-cyan-800 text-white flex items-center gap-1.5 transition shadow-lg shadow-cyan-900/30"
            >
              <FileDown className="w-3.5 h-3.5" />
              Download Markdown
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
