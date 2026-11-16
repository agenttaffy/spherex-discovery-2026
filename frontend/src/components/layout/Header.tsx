import React from 'react';
import { Telescope, Radio, Sparkles, Orbit, BookOpen, Share2, Check, Download, Layers, Box } from 'lucide-react';

const workspaceViews = [
  { id: 'explorer', label: 'Explorer', icon: Telescope },
  { id: 'blink', label: 'Blink', icon: Sparkles },
  { id: 'cube', label: '102 Bands', icon: Box },
  { id: 'diff', label: 'Difference & Stack', icon: Layers },
  { id: 'about', label: 'About' },
] as const;

export type MainView = typeof workspaceViews[number]['id'];

interface HeaderProps {
  irsaConnected: boolean | null | 'backend-error';
  demoCacheOnly: boolean;
  activeTab: MainView;
  setActiveTab: (tab: MainView) => void;
  onOpenGuidedTour?: () => void;
  onCopyShareLink?: () => void;
  onExportReport?: () => void;
  copiedLink?: boolean;
  onRefreshConnection?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  irsaConnected, demoCacheOnly, activeTab, setActiveTab,
  onOpenGuidedTour, onCopyShareLink, onExportReport, copiedLink = false, onRefreshConnection,
}) => (
  <header className="observatory-header instrument-header">
    <a className="observatory-brand" href="#observatory" aria-label="SPHEREx Discovery observatory">
      <span className="observatory-mark"><Orbit aria-hidden="true" /></span>
      <span>SPHEREx <strong>Discovery</strong></span>
    </a>
    <nav role="tablist" aria-label="Main application view navigation" className="observatory-nav flex-wrap">
      {workspaceViews.map((view) => {
        const Icon = 'icon' in view ? view.icon : null;
        return <button key={view.id} type="button" role="tab" aria-selected={activeTab === view.id}
          aria-controls="main-workspace" onClick={() => setActiveTab(view.id)}>
          {Icon && <Icon aria-hidden="true" />} {view.label}
        </button>;
      })}
    </nav>
    <div className="observatory-header-actions">
      {onOpenGuidedTour && <button type="button" onClick={onOpenGuidedTour} aria-label="Open Guided Tour and Science Guide" title="Open guided tour" className="observatory-action"><BookOpen aria-hidden="true" /><span>Guide</span></button>}
      {onCopyShareLink && <button type="button" onClick={onCopyShareLink} aria-label="Copy shareable deep-link URL to clipboard" title="Copy share link" className="observatory-action">{copiedLink ? <Check aria-hidden="true" /> : <Share2 aria-hidden="true" />}<span>{copiedLink ? 'Copied' : 'Share'}</span></button>}
      {onExportReport && <button type="button" onClick={onExportReport} aria-label="Export Scientific Discovery Report" title="Export discovery report" className="observatory-action"><Download aria-hidden="true" /><span>Report</span></button>}
      <span role="status" className="observatory-connection" data-reachable={demoCacheOnly || irsaConnected === true}
        aria-label={demoCacheOnly ? 'Cached demo observations' : irsaConnected === 'backend-error' ? 'App server unavailable' : `IRSA image search check: ${irsaConnected === null ? 'checking' : irsaConnected ? 'responding' : 'unavailable'}`}
        title={demoCacheOnly ? 'Observation search uses the selected local manifest.' : irsaConnected === 'backend-error' ? 'The app server could not be reached; start or check the backend.' : 'Latest image-search check only. Individual images and other IRSA services may behave differently.'}>
        <Radio aria-hidden="true" />{demoCacheOnly ? 'Cached demo' : irsaConnected === 'backend-error' ? 'App server unavailable' : irsaConnected === null ? 'Checking search' : irsaConnected ? 'Search responding' : 'Search check failed'}
      </span>
      {onRefreshConnection && !demoCacheOnly && <button type="button" onClick={onRefreshConnection}
        disabled={irsaConnected === null} aria-label="Retry archive search status check"
        title="Check archive search status again" className="observatory-action disabled:opacity-50">
        Retry status
      </button>}
    </div>
  </header>
);
