import React, { useState, useEffect, useCallback } from 'react';
import { Telescope, Search, Activity } from 'lucide-react';
import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';
import { SearchControls } from './components/controls/SearchControls';
import { CanvasViewer } from './components/viewer/CanvasViewer';
import { TimelinePlayer } from './components/timeline/TimelinePlayer';
import { MetadataPanel } from './components/metadata/MetadataPanel';
import { ComparisonView } from './components/viewer/ComparisonView';
import { AboutPage } from './pages/AboutPage';
import { GuidedTourModal } from './components/layout/GuidedTourModal';
import { DiscoveryReportModal } from './components/science/DiscoveryReportModal';
import {
  ObservationRecord,
  FrameResponse,
  DemoPreset,
  CatalogSource,
  LightCurveSeries,
  SpectrumResponse,
  DiscoveryReport,
} from './types/astronomy';
import {
  checkHealth,
  fetchObservations,
  fetchFrame,
  prefetchFrame,
  fetchDemoPresets,
  fetchCatalogs,
  fetchPhotometry,
  fetchSpectrum,
  computeMotion,
  generateDiscoveryReport,
} from './services/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'explorer' | 'blink' | 'diff' | 'about'>('explorer');
  const [mobilePanel, setMobilePanel] = useState<'canvas' | 'search' | 'telemetry'>('canvas');
  const [irsaConnected, setIrsaConnected] = useState(false);

  // Search parameters
  const [ra, setRa] = useState('269.45208'); // Barnard's Star default
  const [dec, setDec] = useState('4.69339');
  const [fov, setFov] = useState(0.04);
  const [collection, setCollection] = useState('spherex_dr1');
  const [detector, setDetector] = useState('ALL');

  // Observation & Frame state
  const [observations, setObservations] = useState<ObservationRecord[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [currentFrame, setCurrentFrame] = useState<FrameResponse | null>(null);

  // UI & Stretch state
  const [stretch, setStretch] = useState('asinh');
  const [colormap, setColormap] = useState('grayscale');
  const [isBlinkActive, setIsBlinkActive] = useState(false);

  // Gaia DR3 & Photometry Science state
  const [catalogSources, setCatalogSources] = useState<CatalogSource[]>([]);
  const [showCatalog, setShowCatalog] = useState(false);
  const [lightCurve, setLightCurve] = useState<LightCurveSeries | null>(null);
  const [loadingPhotometry, setLoadingPhotometry] = useState(false);
  const [spectrum, setSpectrum] = useState<SpectrumResponse | null>(null);
  const [loadingSpectrum, setLoadingSpectrum] = useState(false);

  // Modals & Share State
  const [isTourOpen, setIsTourOpen] = useState(false);
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [reportData, setReportData] = useState<DiscoveryReport | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  // Loading states
  const [loadingObs, setLoadingObs] = useState(false);
  const [loadingFrame, setLoadingFrame] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Presets
  const [presets, setPresets] = useState<DemoPreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>('barnards_star');

  // 1. Initial health and presets load
  useEffect(() => {
    checkHealth()
      .then((h) => setIrsaConnected(h.irsa_connected))
      .catch(() => setIrsaConnected(false));

    fetchDemoPresets()
      .then((p) => {
        setPresets(p);
        if (p.length > 0) {
          // Check URL query parameters
          const params = new URLSearchParams(window.location.search);
          const urlRa = params.get('ra');
          const urlDec = params.get('dec');
          const urlFov = params.get('fov');
          const urlStretch = params.get('stretch');
          const urlColormap = params.get('colormap');
          const urlTarget = params.get('target');

          if (urlStretch) setStretch(urlStretch);
          if (urlColormap) setColormap(urlColormap);

          const targetPreset = urlTarget ? p.find((x) => x.id === urlTarget) : null;
          if (targetPreset) {
            setSelectedPresetId(targetPreset.id);
            setRa(String(targetPreset.ra));
            setDec(String(targetPreset.dec));
            setCollection(targetPreset.default_collection);
            searchWithCoords(targetPreset.ra, targetPreset.dec, 0.04, targetPreset.default_collection);
          } else if (urlRa && urlDec) {
            setRa(urlRa);
            setDec(urlDec);
            const searchColl = params.get('collection') || 'spherex_dr1';
            setCollection(searchColl);
            if (urlFov) setFov(Number(urlFov));
            searchWithCoords(urlRa, urlDec, urlFov ? Number(urlFov) : 0.04, searchColl);
          } else {
            // Load default preset (Barnard's Star)
            const def = p[0];
            setSelectedPresetId(def.id);
            setRa(String(def.ra));
            setDec(String(def.dec));
            setCollection(def.default_collection);
            searchWithCoords(def.ra, def.dec, 0.04, def.default_collection);
          }
        }
      })
      .catch((err) => console.error('Failed to load presets:', err));
  }, []);

  const searchWithCoords = useCallback(
    async (searchRa: number | string, searchDec: number | string, searchFov: number, searchColl: string) => {
      setLoadingObs(true);
      setErrorMessage(null);
      try {
        const res = await fetchObservations(searchRa, searchDec, searchFov, searchColl, detector);
        setObservations(res.observations);
        setCurrentIndex(0);
        if (res.observations.length > 0) {
          loadFrame(res.observations[0].id, stretch, searchFov);
        } else {
          setCurrentFrame(null);
        }

        // Fetch Catalogs in background
        fetchCatalogs(searchRa, searchDec, 0.08)
          .then((cat) => setCatalogSources(cat.sources))
          .catch(() => setCatalogSources([]));

        // Fetch Photometric light curve in background
        setLoadingPhotometry(true);
        fetchPhotometry(searchRa, searchDec, searchColl, detector, searchFov)
          .then(setLightCurve)
          .catch(() => setLightCurve(null))
          .finally(() => setLoadingPhotometry(false));

        // Fetch Infrared Spectrum SED in background
        setLoadingSpectrum(true);
        fetchSpectrum(searchRa, searchDec, searchColl, searchFov)
          .then(setSpectrum)
          .catch(() => setSpectrum(null))
          .finally(() => setLoadingSpectrum(false));

      } catch (err: any) {
        setErrorMessage(err.message || 'Observation discovery failed');
      } finally {
        setLoadingObs(false);
      }
    },
    [detector, stretch]
  );

  const loadFrame = useCallback(
    async (frameId: string, currentStretch: string, currentFov: number) => {
      setLoadingFrame(true);
      try {
        const frame = await fetchFrame(frameId, currentStretch, currentFov);
        setCurrentFrame(frame);
      } catch (err: any) {
        console.error('Frame fetch error:', err);
      } finally {
        setLoadingFrame(false);
      }
    },
    []
  );

  // Handle timeline index selection
  const handleSelectIndex = (idx: number) => {
    setCurrentIndex(idx);
    const obs = observations[idx];
    if (obs) {
      loadFrame(obs.id, stretch, fov);
      // Prefetch adjacent frames for smooth playback and blink comparison
      if (idx + 1 < observations.length) {
        prefetchFrame(observations[idx + 1].id, stretch, fov);
      }
      if (idx - 1 >= 0) {
        prefetchFrame(observations[idx - 1].id, stretch, fov);
      }
    }
  };

  // Handle stretch changes
  const handleSetStretch = (newStretch: string) => {
    setStretch(newStretch);
    const obs = observations[currentIndex];
    if (obs) {
      loadFrame(obs.id, newStretch, fov);
    }
  };

  // Handle preset selection
  const handleSelectPreset = (preset: DemoPreset) => {
    setSelectedPresetId(preset.id);
    setRa(String(preset.ra));
    setDec(String(preset.dec));
    setCollection(preset.default_collection);
    searchWithCoords(preset.ra, preset.dec, fov, preset.default_collection);
    setMobilePanel('canvas');

    // Update URL without reload
    const url = new URL(window.location.href);
    url.searchParams.set('ra', String(preset.ra));
    url.searchParams.set('dec', String(preset.dec));
    url.searchParams.set('target', preset.id);
    window.history.replaceState({}, '', url.toString());
  };

  const handleManualSearch = () => {
    searchWithCoords(ra, dec, fov, collection);
    setMobilePanel('canvas');
    const url = new URL(window.location.href);
    url.searchParams.set('ra', ra);
    url.searchParams.set('dec', dec);
    url.searchParams.set('fov', String(fov));
    url.searchParams.set('collection', collection);
    window.history.replaceState({}, '', url.toString());
  };

  // Share URL Deep Link
  const handleCopyShareLink = () => {
    const url = new URL(window.location.href);
    url.searchParams.set('ra', ra);
    url.searchParams.set('dec', dec);
    url.searchParams.set('fov', String(fov));
    url.searchParams.set('collection', collection);
    url.searchParams.set('stretch', stretch);
    url.searchParams.set('colormap', colormap);
    window.history.replaceState({}, '', url.toString());

    navigator.clipboard.writeText(url.toString());
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  // Generate & Export Scientific Discovery Report
  const handleExportDiscoveryReport = async () => {
    const currentPreset = presets.find((p) => p.id === selectedPresetId);
    const targetName = currentPreset ? currentPreset.name : `SPHEREx Target (RA ${ra}, Dec ${dec})`;
    const targetType = currentPreset ? currentPreset.target_type : 'Astronomical Source';

    // Calculate motion data across compatible epochs if available
    let motionData = null;
    if (observations.length >= 2) {
      for (let i = 0; i < observations.length; i++) {
        for (let j = i + 1; j < observations.length; j++) {
          if (observations[i].detector === observations[j].detector) {
            try {
              const mRes = await computeMotion(observations[i].id, observations[j].id);
              if (mRes?.motion) {
                motionData = mRes.motion;
                break;
              }
            } catch {
              // ignore
            }
          }
        }
        if (motionData) break;
      }
    }

    try {
      const rep = await generateDiscoveryReport({
        target_name: targetName,
        ra: Number(ra),
        dec: Number(dec),
        target_type: targetType,
        motion_data: motionData,
        photometry_data: lightCurve,
        observations: observations,
        notes: currentPreset?.description,
      });
      setReportData(rep);
      setIsReportOpen(true);
    } catch (err) {
      console.error('Failed to generate report:', err);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden">
      <Header
        irsaConnected={irsaConnected}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenGuidedTour={() => setIsTourOpen(true)}
        onCopyShareLink={handleCopyShareLink}
        onExportReport={handleExportDiscoveryReport}
        copiedLink={copiedLink}
      />

      {/* Main Workspace Layout */}
      <main id="main-workspace" className="flex flex-col flex-1 overflow-hidden relative">
        {activeTab === 'about' ? (
          <AboutPage />
        ) : activeTab === 'diff' ? (
          <ComparisonView observations={observations} />
        ) : (
          <>
            {/* Mobile Panel Switcher & Observation Identity Strip (< lg) */}
            <div className="lg:hidden bg-slate-900 border-b border-slate-800 px-3 py-1.5 flex flex-wrap items-center justify-between gap-2 shrink-0">
              <div role="tablist" aria-label="Mobile workspace view tabs" className="flex items-center gap-1">
                <button
                  role="tab"
                  aria-selected={mobilePanel === 'canvas'}
                  aria-label="View astronomical canvas and timeline"
                  onClick={() => setMobilePanel('canvas')}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                    mobilePanel === 'canvas'
                      ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40'
                      : 'text-slate-300 hover:text-white'
                  }`}
                >
                  <Telescope className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Canvas</span>
                </button>
                <button
                  role="tab"
                  aria-selected={mobilePanel === 'search'}
                  aria-label="Target search and coordinate parameters"
                  onClick={() => setMobilePanel('search')}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                    mobilePanel === 'search'
                      ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40'
                      : 'text-slate-300 hover:text-white'
                  }`}
                >
                  <Search className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Target</span>
                </button>
                <button
                  role="tab"
                  aria-selected={mobilePanel === 'telemetry'}
                  aria-label="Scientific telemetry and SED spectra"
                  onClick={() => setMobilePanel('telemetry')}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                    mobilePanel === 'telemetry'
                      ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40'
                      : 'text-slate-300 hover:text-white'
                  }`}
                >
                  <Activity className="w-3.5 h-3.5 text-cyan-400" />
                  <span>SED &amp; Data</span>
                </button>
              </div>

              {/* Current target identity indicator */}
              <div className="text-[11px] font-mono text-slate-300 truncate max-w-[200px]">
                <span className="text-cyan-300 font-semibold">
                  {presets.find((p) => p.id === selectedPresetId)?.name || 'Target'}
                </span>{' '}
                • {observations[currentIndex]?.detector || 'D1'}
              </div>
            </div>

            <div className="flex flex-1 overflow-hidden relative">
              {/* Left Controls Dock */}
              <div className={`${mobilePanel === 'search' ? 'flex' : 'hidden'} lg:flex w-full lg:w-80 lg:shrink-0 h-full overflow-hidden`}>
                <SearchControls
                  ra={ra}
                  setRa={setRa}
                  dec={dec}
                  setDec={setDec}
                  fov={fov}
                  setFov={setFov}
                  collection={collection}
                  setCollection={setCollection}
                  detector={detector}
                  setDetector={setDetector}
                  loading={loadingObs}
                  onSearch={handleManualSearch}
                  presets={presets}
                  onSelectPreset={handleSelectPreset}
                  selectedPresetId={selectedPresetId}
                />
              </div>

              {/* Central Astronomical Viewing Canvas */}
              <div className={`${mobilePanel === 'canvas' ? 'flex' : 'hidden'} lg:flex flex-1 flex-col overflow-hidden relative h-full`}>
                {errorMessage && (
                  <div className="bg-rose-950/70 border-b border-rose-800 text-rose-300 text-xs px-4 py-2 flex items-center justify-between">
                    <span>{errorMessage}</span>
                    <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-white">
                      ✕
                    </button>
                  </div>
                )}

                <CanvasViewer
                  frame={currentFrame}
                  loading={loadingFrame}
                  stretch={stretch}
                  setStretch={handleSetStretch}
                  colormap={colormap}
                  setColormap={setColormap}
                  catalogSources={catalogSources}
                  showCatalog={showCatalog}
                  setShowCatalog={setShowCatalog}
                  title={observations[currentIndex]?.obs_id}
                  subtitle={
                    observations[currentIndex]
                      ? `${observations[currentIndex].collection.toUpperCase()} • ${observations[currentIndex].detector} • ${observations[currentIndex].utc_date || ''}`
                      : undefined
                  }
                  targetRa={Number(ra)}
                  targetDec={Number(dec)}
                  targetFov={fov}
                />

                {/* Bottom Multi-Epoch Timeline & Blink Player */}
                <TimelinePlayer
                  observations={observations}
                  currentIndex={currentIndex}
                  onSelectIndex={handleSelectIndex}
                  isBlinkActive={isBlinkActive || activeTab === 'blink'}
                  setIsBlinkActive={setIsBlinkActive}
                />
              </div>

              {/* Right Telemetry & Provenance Dock */}
              <div className={`${mobilePanel === 'telemetry' ? 'flex' : 'hidden'} lg:flex w-full lg:w-80 lg:shrink-0 h-full overflow-hidden`}>
                <MetadataPanel
                  frame={currentFrame}
                  lightCurve={lightCurve}
                  loadingPhotometry={loadingPhotometry}
                  spectrum={spectrum}
                  loadingSpectrum={loadingSpectrum}
                  onSelectObsId={(obsId) => {
                    const idx = observations.findIndex((o) => o.obs_id === obsId);
                    if (idx >= 0) handleSelectIndex(idx);
                  }}
                  onOpenDiscoveryReport={handleExportDiscoveryReport}
                />
              </div>
            </div>
          </>
        )}
      </main>

      <Footer />

      {/* Guided Tour Modal */}
      <GuidedTourModal
        isOpen={isTourOpen}
        onClose={() => setIsTourOpen(false)}
        onSelectPreset={(presetId) => {
          const p = presets.find((x) => x.id === presetId);
          if (p) handleSelectPreset(p);
        }}
      />

      {/* Scientific Discovery Report Modal */}
      <DiscoveryReportModal
        report={reportData}
        isOpen={isReportOpen}
        onClose={() => setIsReportOpen(false)}
      />
    </div>
  );
};

export default App;
