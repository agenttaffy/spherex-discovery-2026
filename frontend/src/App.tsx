import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Telescope, Search, Activity, Loader2, PanelLeft, PanelRight } from 'lucide-react';
import { Header, type MainView } from './components/layout/Header';
import { Footer } from './components/layout/Footer';
import { SearchControls } from './components/controls/SearchControls';
import { CanvasViewer } from './components/viewer/CanvasViewer';
import { TimelinePlayer } from './components/timeline/TimelinePlayer';
import { MetadataPanel } from './components/metadata/MetadataPanel';
import { ComparisonView } from './components/viewer/ComparisonView';
import { AboutPage } from './pages/AboutPage';
import { GuidedTourModal } from './components/layout/GuidedTourModal';
import { DiscoveryReportModal } from './components/science/DiscoveryReportModal';
import { CubeView } from './components/science/CubeView';
import { applyCubeSharePosition, parseCubeDeepLink, type SkyPosition } from './components/science/cubeShare';
import { findRequestedObservation, unavailableObservationMessage } from './services/observationSelection';
import { OrbitalIntro } from './components/layout/OrbitalIntro';
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
  generateDiscoveryReport,
} from './services/api';

export const App: React.FC = () => {
  const [initialCubeLink] = useState(() => parseCubeDeepLink(new URLSearchParams(window.location.search)));
  const [autoLoadCube, setAutoLoadCube] = useState<SkyPosition | null>(initialCubeLink);
  const consumeAutoLoadCube = useCallback(() => setAutoLoadCube(null), []);
  const [showIntro] = useState(() => {
    const { search, hash } = window.location;
    const params = new URLSearchParams(search);
    return params.get('embed') !== '1' && !['#observatory', '#main-workspace'].includes(hash)
      && !['ra', 'dec', 'target', 'obs', 'tab'].some((key) => params.has(key));
  });
  const [activeTab, setActiveTab] = useState<MainView>(initialCubeLink ? 'cube' : 'explorer');
  const [mobilePanel, setMobilePanel] = useState<'canvas' | 'search' | 'telemetry'>('canvas');
  const [searchOpen, setSearchOpen] = useState(() => new URLSearchParams(window.location.search).get('embed') !== '1');
  const [analysisOpen, setAnalysisOpen] = useState(() => new URLSearchParams(window.location.search).get('embed') !== '1');
  const [irsaConnected, setIrsaConnected] = useState<boolean | null | 'backend-error'>(null);
  const [demoCacheOnly, setDemoCacheOnly] = useState(false);

  // Search parameters
  const [ra, setRa] = useState(() => String(initialCubeLink?.ra ?? 269.45208)); // Barnard's Star default
  const [dec, setDec] = useState(() => String(initialCubeLink?.dec ?? 4.69339));
  const [fov, setFov] = useState(0.04);
  const [collection, setCollection] = useState('ALL');
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
  const [displayedCube, setDisplayedCube] = useState<SkyPosition | null>(null);
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
  const [analysisRefresh, setAnalysisRefresh] = useState(0);

  // Modals & Share State
  const [isTourOpen, setIsTourOpen] = useState(false);
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [reportData, setReportData] = useState<DiscoveryReport | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);
  const [shareError, setShareError] = useState<string | null>(null);

  // Loading states
  const [loadingObs, setLoadingObs] = useState(false);
  const [loadingFrame, setLoadingFrame] = useState(false);
  const [frameError, setFrameError] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [observationWarning, setObservationWarning] = useState<string | null>(null);

  // Presets
  const [presets, setPresets] = useState<DemoPreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>('barnards_star');
  const searchRequest = useRef(0);
  const frameRequest = useRef(0);

  const targetName = presets.find((preset) => preset.id === selectedPresetId)?.name
    ?? (searchedTarget ? 'Custom coordinates' : 'Sky explorer');
  const cubeDraftRa = Number(ra), cubeDraftDec = Number(dec);
  // A cube deep link can still be loaded when the separate image search fails.
  const cubeDraftPosition = ra.trim() && dec.trim() && Number.isFinite(cubeDraftRa) && Number.isFinite(cubeDraftDec)
    && cubeDraftRa >= 0 && cubeDraftRa < 360 && cubeDraftDec >= -90 && cubeDraftDec <= 90
    ? { ra: cubeDraftRa, dec: cubeDraftDec } : null;
  const workspaceStatus = loadingObs ? 'Searching the archive'
    : loadingFrame ? 'Loading cutout'
      : observations.length > 0 ? `${observations.length} observation${observations.length === 1 ? '' : 's'}${observations.length >= 60 ? ' shown (limit)' : ''}`
        : searchedTarget ? 'No observations returned; archive may be unavailable' : '';

  const refreshConnectionStatus = useCallback(() => {
    setIrsaConnected(null);
    checkHealth()
      .then((health) => {
        setIrsaConnected(health.irsa_connected);
        setDemoCacheOnly(health.demo_cache_only === true);
      })
      .catch(() => {
        setDemoCacheOnly(false);
        setIrsaConnected('backend-error');
      });
  }, []);

  // 1. Initial health and presets load
  useEffect(() => {
    refreshConnectionStatus();
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
          const urlObsDetector = params.get('obs_detector');
          const requestedDetector = params.get('detector');
          // Search configured releases by default for the widest temporal view.
          // Explicit shared-link collection choices remain authoritative.
          const searchColl = params.get('collection') || 'ALL';
          const searchDetector = requestedDetector && /^SPHEREx-D[1-6]$/i.test(requestedDetector) ? requestedDetector : 'ALL';
          const initialStretch = urlStretch && ['asinh', 'zscale', 'linear'].includes(urlStretch) ? urlStretch : 'asinh';
          setDetector(searchDetector);
          const parsedFov = urlFov ? Number(urlFov) : 0.04;
          const initialFov = Number.isFinite(parsedFov) && parsedFov > 0 && parsedFov <= 0.3 ? parsedFov : 0.04;
          setFov(initialFov);

          if (urlTab && ['explorer', 'blink', 'cube', 'diff', 'about'].includes(urlTab)) {
            setActiveTab(urlTab as MainView);
          }
          setStretch(initialStretch);
          if (urlColormap && ['grayscale', 'inferno'].includes(urlColormap)) setColormap(urlColormap);

          const targetPreset = urlTarget ? p.find((x) => x.id === urlTarget) : null;
          if (urlRa && urlDec) {
            setSelectedPresetId(targetPreset && Number(urlRa) === targetPreset.ra && Number(urlDec) === targetPreset.dec ? targetPreset.id : '');
            setRa(urlRa);
            setDec(urlDec);
            setCollection(searchColl);
            searchWithCoords(urlRa, urlDec, initialFov, searchColl, urlObs, searchDetector, initialStretch, urlObsDetector);
          } else if (targetPreset) {
            setSelectedPresetId(targetPreset.id);
            setRa(String(targetPreset.ra));
            setDec(String(targetPreset.dec));
            setCollection(searchColl);
            searchWithCoords(targetPreset.ra, targetPreset.dec, initialFov, searchColl, urlObs, searchDetector, initialStretch, urlObsDetector);
          } else {
            // Load default preset (Barnard's Star)
            const def = p[0];
            setSelectedPresetId(def.id);
            setRa(String(def.ra));
            setDec(String(def.dec));
            setCollection(searchColl);
            searchWithCoords(def.ra, def.dec, initialFov, searchColl, urlObs, searchDetector, initialStretch, urlObsDetector);
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
      targetObsId?: string | null,
      searchDetector: string = detector,
      searchStretch: string = stretch,
      targetObsDetector?: string | null
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
      setObservationWarning(null);
      setFrameError(null);
      try {
        const res = await fetchObservations(searchRa, searchDec, searchFov, searchColl, searchDetector);
        if (requestId !== searchRequest.current) return;
        setSearchedTarget({ra: res.target.ra, dec: res.target.dec});
        setSearchedQuery({ra: res.target.ra, dec: res.target.dec, fov: searchFov, collection: searchColl, detector: searchDetector});
        setObservations(res.observations);
        let startIdx = 0;
        if (targetObsId) {
          const matchIdx = findRequestedObservation(res.observations, targetObsId, targetObsDetector);
          if (matchIdx >= 0) startIdx = matchIdx;
          else setObservationWarning(unavailableObservationMessage(targetObsId, res.observations.length > 0));
        }
        setCurrentIndex(startIdx);
        if (res.observations.length > 0) {
          loadFrame(res.observations[startIdx].id, searchStretch, searchFov);
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
  }, [searchedQuery, analysisOpen, mobilePanel, analysisRefresh]);

  useEffect(() => {
    if (!showCatalog || !searchedQuery) {
      setLoadingCatalog(false);
      return;
    }
    let active = true;
    setLoadingCatalog(true);
    setCatalogQueryError(false);
    setCatalogSources([]);
    // Include a 3-arcminute margin for catalog-to-exposure proper motion.
    // The bright-source limit and margin do not guarantee completeness.
    fetchCatalogs(searchedQuery.ra, searchedQuery.dec, Math.min(1, Math.max(0.01, searchedQuery.fov * Math.SQRT2 / 2 + 0.05)))
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
      setFrameError(null);
      try {
        const frame = await fetchFrame(frameId, currentStretch, currentFov);
        if (requestId === frameRequest.current) setCurrentFrame(frame);
      } catch (err: any) {
        if (requestId === frameRequest.current) setFrameError(err.message || 'Frame could not be loaded');
      } finally {
        if (requestId === frameRequest.current) setLoadingFrame(false);
      }
    },
    []
  );

  // Handle timeline index selection
  const handleSelectIndex = (idx: number) => {
    setObservationWarning(null);
    setCurrentIndex(idx);
    const obs = observations[idx];
    if (obs) {
      loadFrame(obs.id, stretch, searchedQuery?.fov ?? fov);
      // Synchronize active observation with URL search params
      const url = new URL(window.location.href);
      // Archive and cached-search records can use different local IDs for the
      // same exposure; the observation ID plus detector is portable.
      url.searchParams.set('obs', obs.obs_id);
      url.searchParams.set('obs_detector', obs.detector);
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
    searchWithCoords(preset.ra, preset.dec, fov, collection);
    setMobilePanel('canvas');

    // Update URL without reload
    const url = new URL(window.location.href);
    url.searchParams.set('ra', String(preset.ra));
    url.searchParams.set('dec', String(preset.dec));
    url.searchParams.set('target', preset.id);
    url.searchParams.set('fov', String(fov));
    url.searchParams.set('collection', collection);
    url.searchParams.set('detector', detector);
    url.searchParams.delete('obs');
    url.searchParams.delete('obs_detector');
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
    url.searchParams.set('detector', detector);
    url.searchParams.delete('target');
    url.searchParams.delete('obs');
    url.searchParams.delete('obs_detector');
    window.history.replaceState({}, '', url.toString());
  };

  // Retry the applied search, not unsubmitted values in the edit form.
  const retryAppliedSearch = () => {
    if (!searchedQuery) return;
    const obs = observations[currentIndex];
    searchWithCoords(searchedQuery.ra, searchedQuery.dec, searchedQuery.fov, searchedQuery.collection,
      obs?.obs_id, searchedQuery.detector, stretch, obs?.detector);
  };

  // Share URL Deep Link
  const handleCopyShareLink = async () => {
    if (activeTab === 'cube' && !displayedCube) {
      setShareError('Load a spectrum successfully before sharing this 102 Bands view.');
      return;
    }
    setShareError(null);
    const url = new URL(window.location.href);
    if (activeTab !== 'explorer') {
      url.searchParams.set('tab', activeTab);
    } else {
      url.searchParams.delete('tab');
    }
    url.searchParams.set('ra', String(searchedQuery?.ra ?? ra));
    url.searchParams.set('dec', String(searchedQuery?.dec ?? dec));
    url.searchParams.set('fov', String(searchedQuery?.fov ?? fov));
    url.searchParams.set('collection', searchedQuery?.collection ?? collection);
    url.searchParams.set('detector', searchedQuery?.detector ?? detector);
    url.searchParams.set('stretch', stretch);
    url.searchParams.set('colormap', colormap);
    if (observations[currentIndex]) {
      url.searchParams.set('obs', observations[currentIndex].obs_id);
      url.searchParams.set('obs_detector', observations[currentIndex].detector);
    } else {
      url.searchParams.delete('obs');
      url.searchParams.delete('obs_detector');
    }
    if (activeTab === 'cube') applyCubeSharePosition(url, displayedCube);
    window.history.replaceState({}, '', url.toString());

    try {
      await navigator.clipboard.writeText(url.toString());
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    } catch {
      setShareError('The share link is in the address bar; copy it from there.');
    }
  };

  // Generate & Export Scientific Discovery Report
  const handleExportDiscoveryReport = async () => {
    if (!searchedTarget) {
      setErrorMessage('Search for a field before generating a report.');
      return;
    }
    const currentPreset = presets.find((p) => p.id === selectedPresetId);
    const targetName = currentPreset ? currentPreset.name : `SPHEREx field (RA ${searchedTarget.ra}, Dec ${searchedTarget.dec})`;
    const targetType = currentPreset ? currentPreset.target_type : 'Astronomical Source';
    const hasOutsideCoverage = observations.some(observation => observation.catalog_coverage === 'outside');

    // No automatic proper-motion claim until source association is validated.
    const motionData = null;

    try {
      const rep = await generateDiscoveryReport({
        target_name: targetName,
        ra: searchedTarget.ra,
        dec: searchedTarget.dec,
        target_type: targetType,
        motion_data: motionData,
        photometry_data: currentPreset || hasOutsideCoverage ? null : lightCurve,
        observations: observations,
        notes: hasOutsideCoverage
          ? 'The epoch-corrected catalog position is outside at least one cached cutout. Target photometry and spectrum are unavailable for this set.'
          : currentPreset ? 'Catalog prediction and field imagery. Source association and target measurements are unconfirmed.' : undefined,
        spectrum_data: currentPreset || hasOutsideCoverage ? null : spectrum,
      });
      setReportData(rep);
      setIsReportOpen(true);
    } catch (err) {
      console.error('Failed to generate report:', err);
      setErrorMessage('The report could not be generated. Please try again.');
    }
  };

  return (
    <>
    {showIntro && <OrbitalIntro />}
    <div id="observatory" tabIndex={-1} className="observatory observatory-shell flex flex-col w-full text-slate-100">
      {!showIntro && <h1 className="sr-only">SPHEREx Discovery observatory</h1>}
      <Header
        irsaConnected={irsaConnected}
        demoCacheOnly={demoCacheOnly}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenGuidedTour={() => setIsTourOpen(true)}
        onCopyShareLink={handleCopyShareLink}
        onExportReport={handleExportDiscoveryReport}
        copiedLink={copiedLink}
        onRefreshConnection={refreshConnectionStatus}
      />
      {shareError && <div role="alert" className="bg-rose-950/80 px-4 py-2 text-xs text-rose-100 flex justify-between gap-3">
        <span>{shareError}</span><button type="button" aria-label="Dismiss share message" onClick={() => setShareError(null)}>✕</button>
      </div>}

      {/* Main Workspace Layout */}
      <main id="main-workspace" className="observatory-main flex flex-col flex-1 min-h-0 relative">
        {activeTab === 'about' ? (
          <div className="observatory-panel observatory-about"><AboutPage onExplore={() => setActiveTab('explorer')} /></div>
        ) : activeTab === 'diff' ? (
          <ComparisonView observations={observations} fov={searchedQuery?.fov ?? fov} namedTarget={!!selectedPresetId} demoCacheOnly={demoCacheOnly} />
        ) : activeTab === 'cube' ? (
          <div className="observatory-panel flex-1 min-h-0 overflow-y-auto"><CubeView target={searchedTarget ?? cubeDraftPosition ?? presets.find(preset => preset.id === selectedPresetId) ?? null} onDisplayedPosition={setDisplayedCube} autoLoadPosition={autoLoadCube} onAutoLoadConsumed={consumeAutoLoadCube} /></div>
        ) : (
          <>
            {/* Mobile Panel Switcher & Observation Identity Strip (< lg) */}
          <div className="observatory-mobile lg:hidden flex flex-wrap items-center gap-2 shrink-0">
              <div role="tablist" aria-label="Mobile workspace view tabs" className="flex items-center gap-1">
                <button
                  role="tab"
                  aria-selected={mobilePanel === 'canvas'}
                  aria-label="View astronomical canvas and timeline"
                  onClick={() => setMobilePanel('canvas')}
                >
                  <Telescope aria-hidden="true" className="w-3.5 h-3.5" /> Canvas
                </button>
                <button
                  role="tab"
                  aria-selected={mobilePanel === 'search'}
                  aria-label="Target search and coordinate parameters"
                  onClick={() => setMobilePanel('search')}
                >
                  <Search aria-hidden="true" className="w-3.5 h-3.5" /> Target
                </button>
                <button
                  role="tab"
                  aria-selected={mobilePanel === 'telemetry'}
                  aria-label="Scientific telemetry and SED spectra"
                  onClick={() => setMobilePanel('telemetry')}
                >
                  <Activity aria-hidden="true" className="w-3.5 h-3.5" /> Analysis
                </button>
              </div>

            </div>

            <div className="observatory-grid explorer-layout flex flex-1 min-h-0 relative">
              {/* Left Controls Dock */}
              <div className={`${mobilePanel === 'search' ? 'flex' : 'hidden'} ${searchOpen ? 'lg:flex' : 'lg:hidden'} observatory-panel observatory-rail w-full lg:shrink-0 lg:h-full overflow-hidden`}>
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
                  observations={observations}
                  currentIndex={currentIndex}
                  onSelectObservation={handleSelectIndex}
                />
              </div>

              {/* Central Astronomical Viewing Canvas */}
              <div className={`${mobilePanel === 'canvas' ? 'flex' : 'hidden'} lg:flex observatory-panel sky-workspace flex-1 min-w-0 flex-col relative lg:h-full`}>
                <div className="observatory-context target-header">
                  <div className="min-w-0"><h2>{targetName}</h2><p className="observatory-coordinates">{searchedTarget ? `Search coordinate · RA ${searchedTarget.ra.toFixed(5)}° · Dec ${searchedTarget.dec.toFixed(5)}°` : 'Choose a target or search coordinates'}</p></div>
                  <div className="observatory-context-actions">
                    {workspaceStatus && <span className="observatory-status" role="status">{(loadingObs || loadingFrame) && <Loader2 aria-hidden="true" className="animate-spin" />}{workspaceStatus}</span>}
                    <button type="button" aria-expanded={searchOpen} onClick={() => setSearchOpen(!searchOpen)} className="observatory-action hidden lg:inline-flex" title={searchOpen ? 'Hide target search' : 'Show target search'}><PanelLeft aria-hidden="true" /><span className="sr-only">Target search</span></button>
                    <button type="button" aria-expanded={analysisOpen} onClick={() => setAnalysisOpen(!analysisOpen)} className="observatory-action hidden lg:inline-flex" title={analysisOpen ? 'Hide analysis' : 'Open analysis'}><PanelRight aria-hidden="true" /> Analysis</button>
                  </div>
                </div>
                {errorMessage && (
                  <div className="bg-rose-950/70 border-b border-rose-800 text-rose-300 text-xs px-4 py-2 flex items-center justify-between">
                    <span>{errorMessage}</span>
                    <button onClick={() => setErrorMessage(null)} aria-label="Dismiss search error" className="text-rose-400 hover:text-white">
                      ✕
                    </button>
                  </div>
                )}
                {observationWarning && <div role="alert" className="bg-amber-950/70 border-b border-amber-800 text-amber-100 text-xs px-4 py-2 flex items-center justify-between gap-2">
                  <span>{observationWarning}</span><button type="button" onClick={() => setObservationWarning(null)} aria-label="Dismiss observation warning">✕</button>
                </div>}
                {frameError && (
                  <div role="alert" className="bg-rose-950/70 border-b border-rose-800 text-rose-200 text-xs px-4 py-2 flex flex-wrap items-center justify-between gap-2">
                    <span>{frameError} Playback paused.</span>
                    {observations[currentIndex] && <button type="button" className="underline text-cyan-200"
                      onClick={() => loadFrame(observations[currentIndex].id, stretch, searchedQuery?.fov ?? fov)}>
                      Retry this image
                    </button>}
                  </div>
                )}

                {observations[currentIndex] && (
                  <p className="observation-source px-4 py-2 text-xs text-slate-300" role="status">
                    {currentFrame?.is_synthetic
                      ? 'Simulated fallback · the archive image could not be loaded. Target coverage is unavailable.'
                      : observations[currentIndex].search_provenance === 'cached_demo'
                      ? 'Demonstration observation · coverage is checked against the displayed FITS frame.'
                      : observations[currentIndex].search_provenance === 'saved_irsa_search'
                        ? `Historical IRSA search snapshot${observations[currentIndex].search_snapshot_saved ? ` saved ${observations[currentIndex].search_snapshot_saved}` : ''} · image availability checked separately.`
                      : observations[currentIndex].search_provenance === 'cloud_header_survey'
                        ? `Partial cloud image-header index${observations[currentIndex].search_snapshot_saved ? ` checked ${observations[currentIndex].search_snapshot_saved} UTC` : ''} · image availability checked separately.`
                      : observations[currentIndex].search_provenance === 'demo_metadata'
                        ? 'Checksum-verified packaged observation metadata · image availability checked separately.'
                      : observations[currentIndex].search_provenance === 'irsa_query'
                        ? 'IRSA archive search result · image may be served from cache'
                        : <>Observation search provenance unavailable. <button className="underline text-cyan-300" onClick={handleManualSearch}>Search again</button> to request current source details.</>}
                  </p>
                )}
                {demoCacheOnly && <p className="px-4 py-2 text-xs text-amber-100 bg-amber-950/40" role="status">Cached demo mode uses only locally available cutouts. Packaged metadata may refer to images that are absent; available saved cutouts have fixed sizes. Start the app in live mode to search for more observations.</p>}
                {!demoCacheOnly && observations[currentIndex]?.search_provenance === 'cached_demo' && <p className="px-4 py-2 text-xs text-amber-100 bg-amber-950/40" role="status">This observation is from the demonstration list; the image source is shown below. Live results may be unavailable or incomplete, and cached cutouts have fixed sizes. More observations depend on archive access. {searchedQuery && <><button type="button" className="underline text-cyan-200" onClick={retryAppliedSearch}>Retry this search</button>{' · '}<a className="underline text-cyan-200" target="_blank" rel="noopener noreferrer" href={`https://irsa.ipac.caltech.edu/applications/spherex/?${new URLSearchParams({api: 'spectral-images', ra: String(searchedQuery.ra), dec: String(searchedQuery.dec), sr: `${searchedQuery.fov}d`})}`}>Open in IRSA</a></>}</p>}
                {observations[currentIndex]?.search_provenance === 'saved_irsa_search' && <p className="px-4 py-2 text-xs text-amber-100 bg-amber-950/40" role="status">These results come from an earlier, narrow IRSA search near this coordinate and may omit newer observations. Images must still be downloaded or found in cache; more observations depend on archive access. {searchedQuery && <><button type="button" className="underline text-cyan-200" onClick={retryAppliedSearch}>Retry this search</button>{' · '}<a className="underline text-cyan-200" target="_blank" rel="noopener noreferrer" href={`https://irsa.ipac.caltech.edu/applications/spherex/?${new URLSearchParams({api: 'spectral-images', ra: String(searchedQuery.ra), dec: String(searchedQuery.dec), sr: `${searchedQuery.fov}d`})}`}>Open in IRSA</a></>}</p>}
                {observations[currentIndex]?.search_provenance === 'cloud_header_survey' && <p className="px-4 py-2 text-xs text-amber-100 bg-amber-950/40" role="status">These observations come from a partial cloud image-header survey, not a live archive search. Parent-image footprints were checked at the survey date; current image availability and coverage are checked separately. Source identity is unconfirmed and additional observations may exist. {searchedQuery && <><button type="button" className="underline text-cyan-200" onClick={retryAppliedSearch}>Retry this search</button>{' · '}<a className="underline text-cyan-200" target="_blank" rel="noopener noreferrer" href={`https://irsa.ipac.caltech.edu/applications/spherex/?${new URLSearchParams({api: 'spectral-images', ra: String(searchedQuery.ra), dec: String(searchedQuery.dec), sr: `${searchedQuery.fov}d`})}`}>Open in IRSA</a></>}</p>}
                {!demoCacheOnly && observations[currentIndex]?.search_provenance === 'demo_metadata' && <p className="px-4 py-2 text-xs text-amber-100 bg-amber-950/40" role="status">This checksum-verified packaged demonstration list is incomplete and is not a live archive search. It contains metadata, not image pixels; the image loads separately from the indicated source at the requested field size. Source identity is unconfirmed, and more observations may exist. {searchedQuery && <><button type="button" className="underline text-cyan-200" onClick={retryAppliedSearch}>Retry this search</button>{' · '}<a className="underline text-cyan-200" target="_blank" rel="noopener noreferrer" href={`https://irsa.ipac.caltech.edu/applications/spherex/?${new URLSearchParams({api: 'spectral-images', ra: String(searchedQuery.ra), dec: String(searchedQuery.dec), sr: `${searchedQuery.fov}d`})}`}>Open in IRSA</a></>}</p>}
                {observations.length > 0 && new Set(observations.map(obs => obs.obs_id)).size === 1 && (
                  <p className="px-4 py-1 text-xs text-amber-200">One unique exposure listed. A temporal comparison needs an independent exposure.</p>
                )}
                {observations.length > 0 && (isBlinkActive || activeTab === 'blink') && (
                  <p className="px-4 py-2 text-xs text-slate-300">Blink shows field changes, including changes caused by differing wavelengths or display contrast. Matching detectors alone do not guarantee matching passbands; a motion measurement needs the same confirmed source and validated astrometry.</p>
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
                  targetId={selectedPresetId || undefined}
                />

                {/* Bottom Multi-Epoch Timeline & Blink Player */}
                <TimelinePlayer
                  observations={observations}
                  currentIndex={currentIndex}
                  onSelectIndex={handleSelectIndex}
                  isBlinkActive={isBlinkActive || activeTab === 'blink'}
                  setIsBlinkActive={(active) => {
                    setIsBlinkActive(active);
                    if (!active && activeTab === 'blink') setActiveTab('explorer');
                  }}
                  loadingFrame={loadingFrame}
                  frameError={!!frameError}
                />
              </div>

              {/* Right Telemetry & Provenance Dock */}
              <div className={`${mobilePanel === 'telemetry' ? 'flex' : 'hidden'} ${analysisOpen ? 'lg:flex' : 'lg:hidden'} observatory-panel observatory-rail observatory-analysis w-full lg:shrink-0 lg:h-full overflow-hidden`}>
                <MetadataPanel
                  namedTarget={!!selectedPresetId}
                  samplePosition={searchedTarget}
                  analysisEnabled={analysisOpen || mobilePanel === 'telemetry'}
                  onOpenCube={() => setActiveTab('cube')}
                  catalogSources={catalogSources}
                  catalogEnabled={showCatalog}
                  loadingCatalog={loadingCatalog}
                  catalogQueryError={catalogQueryError}
                  frame={currentFrame}
                  lightCurve={lightCurve}
                  loadingPhotometry={loadingPhotometry}
                  spectrum={spectrum}
                  loadingSpectrum={loadingSpectrum}
                  onRefreshAnalysis={() => setAnalysisRefresh(value => value + 1)}
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
    </>
  );
};

export default App;
