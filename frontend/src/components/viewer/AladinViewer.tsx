import React, { useEffect, useRef, useState } from 'react';
import { ExternalLink, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';

interface AladinViewerProps {
  ra: number;
  dec: number;
  fov?: number;
  footprint?: number[][] | null;
}

type Phase = 'library' | 'webgl' | 'tiles' | 'ready' | 'error';
const SURVEYS = [
  { id: '2mass', name: '2MASS color', url: 'https://irsa.ipac.caltech.edu/data/hips/CDS/2MASS/Color', credit: 'University of Massachusetts & IPAC/Caltech; HiPS by CDS, served by IRSA', terms: 'https://www.ipac.caltech.edu/2mass/releases/second/faq.html' },
  { id: 'allwise', name: 'AllWISE color', url: 'https://irsa.ipac.caltech.edu/data/hips/CDS/AllWISE/RGB-W4-W2-W1', credit: 'NASA/IPAC AllWISE; color HiPS by CDS, served by IRSA', terms: 'https://irsa.ipac.caltech.edu/data/WISE/docs/release/allwise/' },
  { id: 'dss', name: 'DSS2 color', url: 'https://irsa.ipac.caltech.edu/data/hips/CDS/DSS2/color', credit: 'STScI/NASA; color HiPS by CDS, served by IRSA. DSS data: CC BY-NC-SA 4.0', terms: 'https://archive.stsci.edu/publishing/data-use' },
] as const;

function fitFieldOfView(ra: number, dec: number, fov: number, footprint: number[][] | null | undefined, element: HTMLElement | null): number {
  const aspect = element && element.clientHeight > 0 ? element.clientWidth / element.clientHeight : 1;
  let halfWidth = fov / 2;
  let halfHeight = fov / 2;
  for (const [pointRa, pointDec] of footprint || []) {
    const deltaRa = ((pointRa - ra + 540) % 360) - 180;
    halfWidth = Math.max(halfWidth, Math.abs(deltaRa * Math.cos(dec * Math.PI / 180)));
    halfHeight = Math.max(halfHeight, Math.abs(pointDec - dec));
  }
  return Math.min(180, Math.max(0.02, 2.6 * Math.max(halfWidth, halfHeight * aspect)));
}

async function hasRenderedSky(instance: any): Promise<boolean> {
  const dataUrl = await instance.getViewDataURL({ format: 'image/png', logo: false });
  const image = new Image();
  await new Promise<void>((resolve, reject) => {
    image.onload = () => resolve();
    image.onerror = () => reject(new Error('Unable to inspect the sky view'));
    image.src = dataUrl;
  });
  const canvas = document.createElement('canvas');
  canvas.width = 32;
  canvas.height = 32;
  const context = canvas.getContext('2d');
  if (!context) return false;
  context.drawImage(image, 0, 0, 32, 32);
  const pixels = context.getImageData(0, 0, 32, 32).data;
  let min = 255;
  let max = 0;
  for (let y = 4; y < 28; y++) for (let x = 4; x < 28; x++) {
    const index = (y * 32 + x) * 4;
    const value = (pixels[index] + pixels[index + 1] + pixels[index + 2]) / 3;
    min = Math.min(min, value);
    max = Math.max(max, value);
  }
  return max - min > 8;
}

export const AladinViewer: React.FC<AladinViewerProps> = ({ ra, dec, fov = 0.04, footprint }) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<HTMLDivElement | null>(null);
  const instanceRef = useRef<any>(null);
  const apiRef = useRef<any>(null);
  const overlayRef = useRef<any>(null);
  const targetRef = useRef<any>(null);
  const latestRef = useRef({ ra, dec, fov, footprint });
  latestRef.current = { ra, dec, fov, footprint };
  const [surveyId, setSurveyId] = useState<string>('2mass');
  const [attempt, setAttempt] = useState(0);
  const [phase, setPhase] = useState<Phase>('library');
  const [message, setMessage] = useState('Loading Aladin Lite library…');
  const survey = SURVEYS.find(item => item.id === surveyId) || SURVEYS[0];

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    // Aladin cancels wheel scrolling on its canvas. Let the browser scroll
    // the surrounding workspace unless the user explicitly asks to zoom.
    const preserveScroll = (event: WheelEvent) => {
      if (!event.shiftKey || event.ctrlKey) event.stopPropagation();
    };
    map.addEventListener('wheel', preserveScroll, { capture: true, passive: true });
    return () => map.removeEventListener('wheel', preserveScroll, true);
  }, []);

  useEffect(() => {
    let cancelled = false;
    let instance: any = null;
    let mount: HTMLDivElement | null = null;
    let stage: 'library' | 'webgl' | 'tiles' = 'library';
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20000);
    const run = async () => {
      try {
        setPhase('library');
        setMessage('Loading Aladin Lite library…');
        const A = (await import('aladin-lite')).default;
        if (cancelled) return;
        apiRef.current = A;
        stage = 'webgl';
        setPhase('webgl');
        setMessage('Initializing WebGL sky viewer…');
        await A.init;
        if (cancelled || !mountRef.current) return;
        mount = mountRef.current;
        const target = latestRef.current;
        instance = A.aladin(mountRef.current, {
          survey: survey.url,
          target: `${target.ra} ${target.dec}`,
          fov: fitFieldOfView(target.ra, target.dec, target.fov, target.footprint, mountRef.current),
          showReticle: false,
          showZoomControl: false,
          showFullscreenControl: false,
          showLayersControl: false,
          showGotoControl: false,
          hipsList: [],
          log: false,
        });
        instanceRef.current = instance;
        stage = 'tiles';
        setPhase('tiles');
        setMessage('Loading context survey tiles…');
        const [properties, tiles] = await Promise.all([
          fetch(`${survey.url}/properties`, { signal: controller.signal }),
          fetch(`${survey.url}/Norder3/Allsky.jpg`, { signal: controller.signal }),
        ]);
        if (!properties.ok || !tiles.ok || !tiles.headers.get('content-type')?.startsWith('image/')) {
          throw new Error('The survey service did not return its metadata and image tiles.');
        }
        if (cancelled) return;
        let rendered = false;
        for (let i = 0; i < 20 && !cancelled && !controller.signal.aborted; i++) {
          await new Promise(resolve => window.setTimeout(resolve, 500));
          try {
            const layer = instance.getBaseImageLayer?.();
            const actualUrl = typeof layer?.url === 'string' ? layer.url.replace(/\/$/, '') : '';
            rendered = actualUrl === survey.url.replace(/\/$/, '') && await hasRenderedSky(instance);
          } catch { rendered = false; }
          if (rendered) break;
        }
        if (cancelled) return;
        if (!rendered) throw new Error('Survey tiles are reachable, but the sky image could not be confirmed in this view.');
        setPhase('ready');
        setMessage('Survey connected; image tiles may still be loading.');
      } catch (error) {
        if (cancelled) return;
        setPhase('error');
        const detail = error instanceof Error ? error.message : String(error);
        setMessage(controller.signal.aborted ? 'The sky context request timed out.' :
          stage === 'library' ? `Aladin library could not load: ${detail}` :
          stage === 'webgl' ? `WebGL initialization failed: ${detail}` : `Survey tile failure: ${detail}`);
      } finally {
        window.clearTimeout(timeout);
      }
    };
    void run();
    return () => {
      cancelled = true;
      window.clearTimeout(timeout);
      controller.abort();
      try { instance?.remove?.(); } catch { /* Viewer may already be gone. */ }
      mount?.replaceChildren();
      instanceRef.current = null;
      overlayRef.current = null;
      targetRef.current = null;
    };
  }, [surveyId, attempt]);

  useEffect(() => {
    const instance = instanceRef.current;
    const A = apiRef.current;
    if (!instance || !A || phase !== 'ready') return;
    instance.gotoRaDec(ra, dec);
    instance.setFoV(fitFieldOfView(ra, dec, fov, footprint, mountRef.current));
    if (!overlayRef.current) {
      overlayRef.current = A.graphicOverlay({ name: 'SPHEREx cutout footprint', color: '#38bdf8', lineWidth: 2 });
      instance.addOverlay(overlayRef.current);
    }
    overlayRef.current.removeAll();
    if (footprint?.length === 4) {
      // Aladin draws great-circle edges and handles polygons crossing RA=0°.
      overlayRef.current.add(A.polygon(footprint.map(point => [point[0], point[1]])));
    }
    if (targetRef.current) instance.removeCatalog?.(targetRef.current);
    const catalog = A.catalog({ name: 'Selected target coordinate', sourceSize: 14, color: '#fbbf24', shape: 'cross' });
    catalog.addSources([A.marker(ra, dec, { popupTitle: 'Selected search coordinate' })]);
    instance.addCatalog(catalog);
    targetRef.current = catalog;
  }, [ra, dec, fov, footprint, phase]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    let previousWidth = mount.clientWidth;
    let previousHeight = mount.clientHeight;
    const observer = new ResizeObserver(() => {
      if (mount.clientWidth === previousWidth && mount.clientHeight === previousHeight) return;
      previousWidth = mount.clientWidth;
      previousHeight = mount.clientHeight;
      const target = latestRef.current;
      instanceRef.current?.setFoV(fitFieldOfView(target.ra, target.dec, target.fov, target.footprint, mount));
    });
    observer.observe(mount);
    return () => observer.disconnect();
  }, []);

  const reset = () => {
    instanceRef.current?.gotoRaDec(ra, dec);
    instanceRef.current?.setFoV(fitFieldOfView(ra, dec, fov, footprint, mountRef.current));
  };

  return (
    <section className="flex-1 min-h-[390px] lg:min-h-0 flex flex-col bg-slate-950" aria-label="Sky context survey">
      <div className="shrink-0 flex flex-wrap items-center gap-2 px-3 py-2 border-b border-slate-800 text-xs">
        <label htmlFor="context-survey" className="text-slate-300">Context survey</label>
        <select id="context-survey" value={surveyId} onChange={e => setSurveyId(e.target.value)} className="bg-slate-900 text-slate-100 rounded px-2 py-1.5 border border-slate-700">
          {SURVEYS.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <span className="text-slate-300">Background imagery, not SPHEREx measurements</span>
        <div className="ml-auto flex items-center gap-1" role="toolbar" aria-label="Sky context navigation">
          <span className="hidden sm:inline mr-1 text-slate-400">Shift + wheel to zoom</span>
          <button aria-label="Zoom in sky context" className="p-2 rounded hover:bg-slate-800" onClick={() => instanceRef.current?.increaseZoom()}><ZoomIn size={16} /></button>
          <button aria-label="Zoom out sky context" className="p-2 rounded hover:bg-slate-800" onClick={() => instanceRef.current?.decreaseZoom()}><ZoomOut size={16} /></button>
          <button aria-label="Recenter on selected coordinates" className="p-2 rounded hover:bg-slate-800" onClick={reset}><RotateCcw size={16} /></button>
        </div>
      </div>
      <div ref={mapRef} className="relative flex-1 min-h-[220px]" aria-label="Aladin sky map">
        <div ref={mountRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} />
        {phase !== 'ready' && <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-950/90 p-5 text-center" role="status">
          <div className="max-w-md space-y-3">
            <p className="text-sm text-slate-100">{phase === 'error' ? 'Sky context could not load' : message}</p>
            {phase === 'error' && <>
              <p className="text-xs text-slate-300">{message} The SPHEREx canvas remains available.</p>
              <button onClick={() => setAttempt(value => value + 1)} className="px-3 py-2 rounded bg-cyan-700 text-white">Retry</button>
              <a className="inline-flex items-center gap-1 ml-3 text-cyan-300 underline" href={`https://aladin.cds.unistra.fr/AladinLite/?target=${encodeURIComponent(`${ra} ${dec}`)}&fov=${Math.max(fov * 2.5, 0.02)}`} target="_blank" rel="noreferrer">Open external Aladin <ExternalLink size={13} /></a>
            </>}
          </div>
        </div>}
      </div>
      <div className="shrink-0 px-3 py-2 border-t border-slate-800 text-[11px] text-slate-300 flex flex-wrap gap-x-4 gap-y-1">
        <span>Selected coordinate: RA {ra.toFixed(5)}°, Dec {dec >= 0 ? '+' : ''}{dec.toFixed(5)}°</span>
        <span>Amber marker: selected coordinate · Cyan outline: {footprint?.length === 4 ? 'SPHEREx image footprint' : 'footprint unavailable'}</span>
        <span>{survey.name}: {survey.credit}</span>
        <a className="text-cyan-300 underline" href={survey.terms} target="_blank" rel="noreferrer">Survey data terms</a>
        <span role="status">{message}</span>
      </div>
    </section>
  );
};
