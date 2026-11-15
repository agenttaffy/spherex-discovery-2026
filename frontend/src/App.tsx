import React, { useState, useEffect, useCallback, useRef } from 'react';
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
  clearFrameCache,
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
  const [searchOpen, setSearchOpen] = useState(true);
  const [analysisOpen, setAnalysisOpen] = useState(false);
  const [irsaConnected, setIrsaConnected] = useState<boolean | null>(null);

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
  const [searchedTarget, setSearchedTarget] = useState<{ra: number; dec: number} | null>(null);
  const [searchedQuery, setSearchedQuery] = useState<{ra: number; dec: number; fov: number; collection: string; detector: string} | null>(null);

  // UI & Stretch state
  const [stretch, setStretch] = useState('asinh');
  const [colormap, setColormap] = useState('grayscale');
  const [isBlinkActive, setIsBlinkActive] = useState(false);

  // Gaia DR3 & Photometry Science state
  const [catalogSources, setCatalogSources] = useState<CatalogSource[]>([]);
  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [catalogQueryError, setCatalogQueryError] = useState(false);
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
  const searchRequest = useRef(0);
  const frameRequest = useRef(0);

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
          const urlTab = params.get('tab');
          const urlRa = params.get('ra');
          const urlDec = params.get('dec');
          const urlFov = params.get('fov');
          const urlStretch = params.get('stretch');
          const urlColormap = params.get('colormap');
          const urlTarget = params.get('target');
          const urlObs = params.get('obs');

          if (urlTab && ['explorer', 'blink', 'diff', 'about'].includes(urlTab)) {
            setActiveTab(urlTab as any);
          }
          if (urlStretch) setStretch(urlStretch);
          if (urlColormap) setColormap(urlColormap);

          const targetPreset = urlTarget ? p.find((x) => x.id === urlTarget) : null;
          if (urlRa && urlDec) {
            setSelectedPresetId(targetPreset && Number(urlRa) === targetPreset.ra && Number(urlDec) === targetPreset.dec ? targetPreset.id : '');
            setRa(urlRa);
            setDec(urlDec);
            const searchColl = params.get('collection') || 'spherex_dr1';
            setCollection(searchColl);
            if (urlFov) setFov(Number(urlFov));
            searchWithCoords(urlRa, urlDec, urlFov ? Number(urlFov) : 0.04, searchColl, urlObs);
          } else if (targetPreset) {
            setSelectedPresetId(targetPreset.id);
            setRa(String(targetPreset.ra));
            setDec(String(targetPreset.dec));
            setCollection(targetPreset.default_collection);
            searchWithCoords(targetPreset.ra, targetPreset.dec, 0.04, targetPreset.default_collection, urlObs);
          } else {
            // Load default preset (Barnard's Star)
            const def = p[0];
            setSelectedPresetId(def.id);
            setRa(String(def.ra));
            setDec(String(def.dec));
            setCollection(def.default_collection);
            searchWithCoords(def.ra, def.dec, 0.04, def.default_collection, urlObs);
          }
        }
      })
      .catch((err) => console.error('Failed to load presets:', err));
  }, []);

  const searchWithCoords = useCallback(
    async (
      searchRa: number | string,
      searchDec: number | string,
      searchFov: number,
      searchColl: string,
      targetObsId?: string | null
    ) => {
      const requestId = ++searchRequest.current;
      ++frameRequest.current;
      clearFrameCache();
      setCurrentFrame(null);
      setSearchedTarget(null);
      setSearchedQuery(null);
      setObservations([]);
      setLightCurve(null);
      setSpectrum(null);
      setCatalogSources([]);
      setLoadingPhotometry(false);
      setLoadingSpectrum(false);
      setLoadingObs(true);
      setErrorMessage(null);
      try {
        const res = await fetchObservations(searchRa, searchDec, searchFov, searchColl, detector);
        if (requestId !== searchRequest.current) return;
        setSearchedTarget({ra: res.target.ra, dec: res.target.dec});
        setSearchedQuery({ra: res.target.ra, dec: res.target.dec, fov: searchFov, collection: searchColl, detector});
        setObservations(res.observations);
        let startIdx = 0;
        if (targetObsId && res.observations.length > 0) {
          const matchIdx = res.observations.findIndex((o) => o.id === targetObsId || o.obs_id === targetObsId);
          if (matchIdx >= 0) startIdx = matchIdx;
        }
        setCurrentIndex(startIdx);
        if (res.observations.length > 0) {
          loadFrame(res.observations[startIdx].id, stretch, searchFov);
        } else {
          setCurrentFrame(null);
        }

      } catch (err: any) {
        if (requestId === searchRequest.current) setErrorMessage(err.message || 'Observation discovery failed');
      } finally {
        if (requestId === searchRequest.current) setLoadingObs(false);
      }
    },
    [detector, stretch]
  );

  useEffect(() => {
    if (!searchedQuery || (!analysisOpen && mobilePanel !== 'telemetry')) return;
    let active = true;
    const q = searchedQuery;
    setLoadingPhotometry(true);
    setLoadingSpectrum(true);
    fetchPhotometry(q.ra, q.dec, q.collection, q.detector, q.fov)
      .then(value => { if (active) setLightCurve(value); })
      .catch(() => { if (active) setLightCurve(null); })
      .finally(() => { if (active) setLoadingPhotometry(false); });
    fetchSpectrum(q.ra, q.dec, q.collection, q.fov)
      .then(value => { if (active) setSpectrum(value); })
      .catch(() => { if (active) setSpectrum(null); })
      .finally(() => { if (active) setLoadingSpectrum(false); });
    return () => { active = false; };
  }, [searchedQuery, analysisOpen, mobilePanel]);

  useEffect(() => {
    if (!showCatalog || !searchedQuery) {
      setLoadingCatalog(false);
      return;
    }
    let active = true;
    setLoadingCatalog(true);
    setCatalogQueryError(false);
    setCatalogSources([]);
    fetchCatalogs(searchedQuery.ra, searchedQuery.dec, 0.08)
      .then(result => { if (active) setCatalogSources(result.sources); })
      .catch(() => { if (active) { setCatalogSources([]); setCatalogQueryError(true); } })
      .finally(() => { if (active) setLoadingCatalog(false); });
    return () => { active = false; };
  }, [showCatalog, searchedQuery]);

  const loadFrame = useCallback(
    async (frameId: string, currentStretch: string, currentFov: number) => {
      const requestId = ++frameRequest.current;
      setLoadingFrame(true);
      setCurrentFrame(null);
      try {
        const frame = await fetchFrame(frameId, currentStretch, currentFov);
        if (requestId === frameRequest.current) setCurrentFrame(frame);
      } catch (err: any) {
        if (requestId === frameRequest.current) setErrorMessage(err.message || 'Frame could not be loaded');
      } finally {
        if (requestId === frameRequest.current) setLoadingFrame(false);
      }
    },
    []
  );

  // Handle timeline index selection
  const handleSelectIndex = (idx: number) => {
    setCurrentIndex(idx);
    const obs = observations[idx];
    if (obs) {
      loadFrame(obs.id, stretch, searchedQuery?.fov ?? fov);
      // Synchronize active observation with URL search params
      const url = new URL(window.location.href);
      url.searchParams.set('obs', obs.id);
      window.history.replaceState({}, '', url.toString());

      // Prefetch adjacent frames for smooth playback and blink comparison
      if (idx + 1 < observations.length) {
        prefetchFrame(observations[idx + 1].id, stretch, searchedQuery?.fov ?? fov);
      }
      if (idx - 1 >= 0) {
        prefetchFrame(observations[idx - 1].id, stretch, searchedQuery?.fov ?? fov);
      }
    }
  };

  // Handle stretch changes
  const handleSetStretch = (newStretch: string) => {
    setStretch(newStretch);
    const obs = observations[currentIndex];
    if (obs) {
      loadFrame(obs.id, newStretch, searchedQuery?.fov ?? fov);
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
    setSelectedPresetId('');
    searchWithCoords(ra, dec, fov, collection);
    setMobilePanel('canvas');
    const url = new URL(window.location.href);
    url.searchParams.set('ra', ra);
    url.searchParams.set('dec', dec);
    url.searchParams.set('fov', String(fov));
    url.searchParams.set('collection', collection);
    url.searchParams.delete('target');
    url.searchParams.delete('obs');
    window.history.replaceState({}, '', url.toString());
  };

  // Share URL Deep Link
  const handleCopyShareLink = () => {
    const url = new URL(window.location.href);
    if (activeTab !== 'explorer') {
      url.searchParams.set('tab', activeTab);
    } else {
      url.searchParams.delete('tab');
    }
    url.searchParams.set('ra', ra);
    url.searchParams.set('dec', dec);
    url.searchParams.set('fov', String(fov));
    url.searchParams.set('collection', collection);
    url.searchParams.set('stretch', stretch);
    url.searchParams.set('colormap', colormap);
    if (observations[currentIndex]) {
      url.searchParams.set('obs', observations[currentIndex].id);
    }
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
        spectrum_data: spectrum,
      });
      setReportData(rep);
      setIsReportOpen(true);
    } catch (err) {
      console.error('Failed to generate report:', err);
    }
  };

  return (
    <div className="flex flex-col min-h-screen lg:h-screen w-full bg-slate-950 text-slate-100 overflow-x-hidden lg:overflow-hidden">
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
      <main id="main-workspace" className="flex flex-col flex-1 min-h-[760px] lg:min-h-0 lg:overflow-hidden relative">
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
              <div className={`${mobilePanel === 'search' ? 'flex' : 'hidden'} ${searchOpen ? 'lg:flex' : 'lg:hidden'} w-full lg:w-80 lg:shrink-0 h-full overflow-hidden`}>
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
              <div className={`${mobilePanel === 'canvas' ? 'flex' : 'hidden'} lg:flex flex-1 min-w-0 flex-col overflow-hidden relative h-full`}>
                <div className="hidden lg:flex items-center gap-2 px-3 py-2 border-b border-slate-800 bg-slate-950 text-xs">
                  <button type="button" aria-expanded={searchOpen} onClick={() => setSearchOpen(!searchOpen)} className="rounded px-3 py-1.5 hover:bg-slate-800 text-slate-200">{searchOpen ? 'Hide target search' : 'Search targets'}</button>
                  <span className="text-slate-400">{searchedTarget ? `RA ${searchedTarget.ra.toFixed(5)}° · Dec ${searchedTarget.dec.toFixed(5)}°` : 'Choose a target or search coordinates'}</span>
                  <button type="button" aria-expanded={analysisOpen} onClick={() => setAnalysisOpen(!analysisOpen)} className="ml-auto rounded px-3 py-1.5 hover:bg-slate-800 text-slate-200">{analysisOpen ? 'Hide analysis' : 'Open analysis'}</button>
                </div>
                {errorMessage && (
                  <div className="bg-rose-950/70 border-b border-rose-800 text-rose-300 text-xs px-4 py-2 flex items-center justify-between">
                    <span>{errorMessage}</span>
                    <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-white">
                      ✕
                    </button>
                  </div>
                )}

                {observations[currentIndex] && (
                  <p className="px-3 py-2 text-xs text-slate-200 bg-slate-900" role="status">
                    {observations[currentIndex].search_provenance === 'cached_demo'
                      ? 'Cached demonstration observation · fixed cutout coverage, not a live search result'
                      : observations[currentIndex].search_provenance === 'irsa_query'
                        ? 'IRSA archive search result · image may be served from cache'
                        : <>Observation search provenance unavailable. <button className="underline text-cyan-300" onClick={handleManualSearch}>Search again</button> to request current source details.</>}
                  </p>
                )}
                <CanvasViewer
                  frame={currentFrame}
                  loading={loadingFrame}
                  stretch={stretch}
                  setStretch={handleSetStretch}
                  colormap={colormap}
                  setColormap={setColormap}
                  catalogSources={catalogSources}
                  loadingCatalog={loadingCatalog}
                  catalogQueryError={catalogQueryError}
                  showCatalog={showCatalog}
                  setShowCatalog={setShowCatalog}
                  title={observations[currentIndex]?.obs_id}
                  subtitle={
                    observations[currentIndex]
                      ? `${observations[currentIndex].collection.toUpperCase()} • ${observations[currentIndex].detector} • ${observations[currentIndex].utc_date || ''}`
                      : undefined
                  }
                  targetRa={searchedTarget?.ra}
                  targetDec={searchedTarget?.dec}
                  targetFov={searchedQuery?.fov ?? fov}
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
              <div className={`${mobilePanel === 'telemetry' ? 'flex' : 'hidden'} ${analysisOpen ? 'lg:flex' : 'lg:hidden'} w-full lg:w-80 lg:shrink-0 h-full overflow-hidden`}>
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
