import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';
import { SearchControls } from './components/controls/SearchControls';
import { CanvasViewer } from './components/viewer/CanvasViewer';
import { TimelinePlayer } from './components/timeline/TimelinePlayer';
import { MetadataPanel } from './components/metadata/MetadataPanel';
import { ComparisonView } from './components/viewer/ComparisonView';
import { AboutPage } from './pages/AboutPage';
import { ObservationRecord, FrameResponse, DemoPreset } from './types/astronomy';
import { checkHealth, fetchObservations, fetchFrame, fetchDemoPresets } from './services/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'explorer' | 'blink' | 'diff' | 'about'>('explorer');
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

          if (urlRa && urlDec) {
            setRa(urlRa);
            setDec(urlDec);
            if (urlFov) setFov(Number(urlFov));
            searchWithCoords(urlRa, urlDec, urlFov ? Number(urlFov) : 0.04, 'spherex_dr1');
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

    // Update URL without reload
    const url = new URL(window.location.href);
    url.searchParams.set('ra', String(preset.ra));
    url.searchParams.set('dec', String(preset.dec));
    window.history.replaceState({}, '', url.toString());
  };

  const handleManualSearch = () => {
    searchWithCoords(ra, dec, fov, collection);
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden">
      <Header
        irsaConnected={irsaConnected}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      {/* Main Workspace Layout */}
      <div className="flex flex-1 overflow-hidden relative">
        {activeTab === 'about' ? (
          <AboutPage />
        ) : activeTab === 'diff' ? (
          <ComparisonView observations={observations} />
        ) : (
          <>
            {/* Left Controls Dock */}
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

            {/* Central Astronomical Viewing Canvas */}
            <div className="flex-1 flex flex-col overflow-hidden relative">
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
                title={observations[currentIndex]?.obs_id}
                subtitle={
                  observations[currentIndex]
                    ? `${observations[currentIndex].collection.toUpperCase()} • ${observations[currentIndex].detector} • ${observations[currentIndex].utc_date || ''}`
                    : undefined
                }
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
            <MetadataPanel frame={currentFrame} />
          </>
        )}
      </div>

      <Footer />
    </div>
  );
};

export default App;
