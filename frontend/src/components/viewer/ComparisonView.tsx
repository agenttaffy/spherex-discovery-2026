import React, { useState, useEffect, useRef } from 'react';
import { ObservationRecord, DiffResult, FrameResponse, AstrometricMotion, StackResult, CompatiblePartners } from '../../types/astronomy';
import { computeDiff, fetchDemoComparison, fetchFrame, stackFrames, findCompatiblePartners } from '../../services/api';
import { comparisonCandidates } from '../../services/comparisonCandidates';
import { imageProvenanceLabel } from '../../services/imageProvenance';
import { ArrowRight, Sparkles, Loader2, AlertCircle, Move, Layers, Plus, Minus, TrendingUp, Palette, Table } from 'lucide-react';

interface ComparisonViewProps {
  observations: ObservationRecord[];
  fov: number;
  namedTarget?: boolean;
  demoCacheOnly?: boolean;
}

export const ComparisonView: React.FC<ComparisonViewProps> = ({ observations: searchObservations, fov, namedTarget, demoCacheOnly }) => {
  const [index1, setIndex1] = useState(0);
  const [index2, setIndex2] = useState(1);
  const [opMode, setOpMode] = useState<'diff' | 'stack'>('diff');
  const [diffColormap, setDiffColormap] = useState<'coolwarm' | 'grayscale'>('coolwarm');
  const [stackMethod, setStackMethod] = useState<'mean' | 'median' | 'sum'>('mean');
  const [extraStackIds, setExtraStackIds] = useState<string[]>([]);
  const [draftExtraIds, setDraftExtraIds] = useState<string[]>([]);

  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);
  const [stackResult, setStackResult] = useState<StackResult | null>(null);
  const [motionResult, setMotionResult] = useState<AstrometricMotion | null>(null);
  const [frame1, setFrame1] = useState<FrameResponse | null>(null);
  const [frame2, setFrame2] = useState<FrameResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [demoPair, setDemoPair] = useState<ObservationRecord[] | null>(null);
  const [demoError, setDemoError] = useState<string | null>(null);
  const [useDemoPair, setUseDemoPair] = useState(false);
  const [partnerResult, setPartnerResult] = useState<{ context: string; value: CompatiblePartners } | null>(null);
  const [partnerError, setPartnerError] = useState<string | null>(null);
  const [findingPartners, setFindingPartners] = useState(false);
  const partnerRequest = useRef<AbortController | null>(null);
  const partnerGeneration = useRef(0);
  const curated = useDemoPair && demoPair;
  const observations = curated || searchObservations;

  useEffect(() => {
    const request = new AbortController();
    fetchDemoComparison(request.signal).then(setDemoPair).catch((problem: Error) => {
      if (!request.signal.aborted) setDemoError(problem.message);
    });
    return () => request.abort();
  }, []);

  // Safely clamp indices to current observations array
  const safeIndex1 = curated ? 0 : Math.min(Math.max(0, index1), Math.max(0, observations.length - 1));
  const safeIndex2 = curated ? 1 : Math.min(Math.max(0, index2), Math.max(0, observations.length - 1));

  const obs1 = observations[safeIndex1];
  const obs2 = observations[safeIndex2];
  const partnerCandidates = obs1 ? comparisonCandidates(observations, obs1, 12, obs2?.id) : [];
  const partnerEligible = obs1 ? comparisonCandidates(observations, obs1, Number.MAX_SAFE_INTEGER).length : 0;
  const partnerContext = `${obs1?.id ?? ''}|${fov}|${!!curated}|${partnerCandidates.map(row => row.id).join('|')}`;
  const visiblePartners = partnerResult?.context === partnerContext ? partnerResult.value : null;
  const knownRdraFirst = searchObservations.findIndex(o => o.obs_id === '2026W01_1A_0257_4' && o.detector === 'SPHEREx-D6' && Math.abs(o.ra - 248.16722768733652) < 0.00015 && Math.abs(o.dec - 66.75502445923215) < 0.00015);
  const knownRdraSecond = searchObservations.findIndex(o => o.obs_id === '2026W20_1A_0101_1' && o.detector === 'SPHEREx-D6' && Math.abs(o.ra - 248.16722768733652) < 0.00015 && Math.abs(o.dec - 66.75502445923215) < 0.00015);
  const knownRdraThird = searchObservations.findIndex(o => o.obs_id === '2026W17_1B_0434_4' && o.detector === 'SPHEREx-D6' && Math.abs(o.ra - 248.16722768733652) < 0.00015 && Math.abs(o.dec - 66.75502445923215) < 0.00015);
  const knownEpsilonFirst = searchObservations.findIndex(o => o.obs_id === '2025W17_4B_0027_3' && o.detector === 'SPHEREx-D5' && Math.abs(o.ra - 331.09813086506205) < 0.00015 && Math.abs(o.dec + 56.801144263858404) < 0.00015);
  const knownEpsilonSecond = searchObservations.findIndex(o => o.obs_id === '2026W17_2A_0308_3' && o.detector === 'SPHEREx-D5' && Math.abs(o.ra - 331.09813086506205) < 0.00015 && Math.abs(o.dec + 56.801144263858404) < 0.00015);
  const knownRwFirst = searchObservations.findIndex(o => o.obs_id === '2025W36_1A_0606_2' && o.detector === 'SPHEREx-D1' && o.collection === 'spherex_dr1' && Math.abs(o.ra - 76.95658820303035) < 0.00015 && Math.abs(o.dec - 30.401287398865755) < 0.00015);
  const knownRwSecond = searchObservations.findIndex(o => o.obs_id === '2026W10_1A_0445_2' && o.detector === 'SPHEREx-D1' && o.collection === 'spherex_dr1' && Math.abs(o.ra - 76.95658820303035) < 0.00015 && Math.abs(o.dec - 30.401287398865755) < 0.00015);
  const extraIds = extraStackIds.filter(id => observations.some(o => o.id === id && o.detector === obs1?.detector) && id !== obs1?.id && id !== obs2?.id);
  const draftIds = draftExtraIds.filter(id => observations.some(o => o.id === id && o.detector === obs1?.detector) && id !== obs1?.id && id !== obs2?.id);
  const extraKey = extraIds.join('|');

  useEffect(() => {
    setPartnerResult(null);
    setPartnerError(null);
    setFindingPartners(false);
    return () => {
      partnerGeneration.current += 1;
      partnerRequest.current?.abort();
      partnerRequest.current = null;
    };
  }, [partnerContext]);

  const checkPartners = async () => {
    if (!obs1 || !partnerCandidates.length) return;
    partnerRequest.current?.abort();
    const controller = new AbortController();
    partnerRequest.current = controller;
    const generation = ++partnerGeneration.current;
    setPartnerResult(null);
    setPartnerError(null);
    setFindingPartners(true);
    try {
      const result = await findCompatiblePartners(obs1.id, partnerCandidates.map(row => row.id), fov, controller.signal);
      if (!controller.signal.aborted && generation === partnerGeneration.current) setPartnerResult({ context: partnerContext, value: result });
    } catch (problem) {
      if (!controller.signal.aborted && generation === partnerGeneration.current)
        setPartnerError(problem instanceof Error ? problem.message : 'Could not check cached comparison partners.');
    } finally {
      if (!controller.signal.aborted && generation === partnerGeneration.current) setFindingPartners(false);
    }
  };

  // Prefer a second epoch with the same detector; that alone does not establish compatibility.
  useEffect(() => {
    if (observations.length >= 2) {
      const d1 = observations[safeIndex1]?.detector;
      if (d1 && observations[safeIndex2]?.detector !== d1) {
        const matchIdx = observations.findIndex((o, idx) => idx !== safeIndex1 && o.detector === d1);
        if (matchIdx >= 0) {
          setIndex2(matchIdx);
        }
      }
    }
  }, [observations, safeIndex1]);

  // Load preview thumbnails for both epochs
  useEffect(() => {
    let active = true;
    setFrame1(null);
    if (obs1) {
      fetchFrame(obs1.id, 'asinh', fov)
        .then(frame => { if (active) setFrame1(frame); })
        .catch(() => {});
    }
    return () => { active = false; };
  }, [obs1?.id, fov]);

  useEffect(() => {
    let active = true;
    setFrame2(null);
    if (obs2) {
      fetchFrame(obs2.id, 'asinh', fov)
        .then(frame => { if (active) setFrame2(frame); })
        .catch(() => {});
    }
    return () => { active = false; };
  }, [obs2?.id, fov]);

  // Compute differential image or co-addition stack
  useEffect(() => {
    if (observations.length < 2 || !obs1 || !obs2) return;

    if (opMode === 'diff' && obs1.id === obs2.id) {
      setLoading(false);
      setDiffResult(null);
      setStackResult(null);
      setMotionResult(null);
      setError('Select two different exposures for a difference image.');
      return;
    }

    if (opMode === 'stack' && obs1.id === obs2.id) {
      setLoading(false);
      setDiffResult(null);
      setStackResult(null);
      setMotionResult(null);
      setError('Select two different exposures for co-addition.');
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);
    setDiffResult(null);
    setStackResult(null);
    setMotionResult(null);

    if (opMode === 'diff') {
      computeDiff(obs1.id, obs2.id, 'webp', fov)
        .then(diff => {
          if (!active) return;
          setDiffResult(diff);
        })
        .catch((err) => {
          if (active) setError(err.message);
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    } else {
      // Co-Add Stacking Mode
      stackFrames([obs1.id, obs2.id, ...extraIds], stackMethod, 'png', 'asinh', fov)
        .then((res) => {
          if (active) setStackResult(res);
        })
        .catch((err) => {
          if (active) setError(err.message);
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }

    return () => {
      active = false;
    };
  }, [obs1?.id, obs2?.id, observations, opMode, stackMethod, fov, namedTarget, curated, extraKey]);

  const calibration = opMode === 'diff' ? diffResult?.calibration : stackResult?.calibration;
  const demoSelector = (demoCacheOnly || demoPair) ? (
    <section className="glass-card mb-4 w-full p-3 text-left text-sm" aria-label="Local comparison pair">
      <button
        type="button"
        aria-pressed={!!curated}
        disabled={!demoPair}
        className="min-h-9 rounded-md border border-cyan-700 px-3 py-1 text-cyan-200 aria-pressed:bg-cyan-900 disabled:border-slate-600 disabled:text-slate-400"
        onClick={() => {
          setDiffResult(null);
          setStackResult(null);
          setMotionResult(null);
          setError(null);
          setUseDemoPair(!useDemoPair);
        }}
      >
        {curated ? 'Using tested example · Epsilon Indi D5' : 'Try tested example · Epsilon Indi D5'}
      </button>
      {curated && <span className="ml-2 text-xs text-slate-300">Select again to return to search results.</span>}
      {demoError && <p role="status" className="mt-2 text-amber-200">{demoError}</p>}
      {!demoError && !demoPair && <p role="status" className="mt-2 text-slate-400">Checking the local D5 cache…</p>}
      {demoPair && (
        <div className="mt-2 space-y-1 text-xs text-slate-300">
          <p>Tested field comparison · cached IRSA Level 2 · fixed cutouts · {demoPair.map(row => row.utc_date?.slice(0, 10)).join(' and ')} UTC</p>
          {curated && <>
            <p>Calibrated field comparison near the epoch-propagated Epsilon Indi position. Epsilon Indi Ba/Bb are unresolved. No detection, motion, target flux, or variability is established.</p>
            {calibration && <details className="text-cyan-200">
              <summary className="cursor-pointer">IRSA spectral WCS · {calibration.retained_pixels}/{calibration.reference_pixels} pixels matched · {(calibration.minimum_retained_overlap * 100).toFixed(4)}% lowest overlap</summary>
              <ul className="mt-2 space-y-2 break-words">
                {calibration.calibrations.map(source => <li key={source.observation_id}>
                  <a className="underline" href={source.calibration_url}>{source.observation_id} calibration</a>
                  <p className="text-slate-300">Plane {source.plane_id}</p>
                  <p className="text-slate-300">MD5 {source.md5} · {source.checksum_source}</p>
                  {source.sha256 && <p className="text-slate-300">SHA-256 {source.sha256}</p>}
                  {source.association_url && <a className="underline" href={source.association_url}>IRSA association for a checked example using this calibration ID</a>}
                </li>)}
              </ul>
            </details>}
          </>}
        </div>
      )}
    </section>
  ) : null;

  if (observations.length < 2) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
        {demoSelector}
        <Sparkles className="w-12 h-12 text-cyan-500/40 mb-3" />
        <h3 className="text-base font-semibold text-slate-200">Insufficient observations</h3>
        <p className="text-xs text-slate-400 max-w-md mt-1">
          At least two independent exposures are needed. Matching detector bands does not establish wavelength compatibility.
        </p>
      </div>
    );
  }

  // Calculate baseline delta days if MJD available
  let deltaDays: number | null = null;
  if (obs1?.mjd && obs2?.mjd) {
    deltaDays = Math.abs(obs2.mjd - obs1.mjd);
  }

  return (
    <div className="flex-1 flex flex-col p-3 sm:p-6 overflow-y-auto max-w-full">
      {demoSelector}
      {/* Top Header & Mode Switcher */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-4 border-b border-slate-800 gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="observatory-title flex flex-wrap items-center gap-2">
              {opMode === 'diff' ? (
                <span>Difference image</span>
              ) : (
                <span>Co-added image</span>
              )}
              {deltaDays !== null && (
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/60 font-normal">
                  {deltaDays < 1 ? `${(deltaDays * 24).toFixed(2)} h apart` : `${deltaDays.toFixed(2)} days apart`}
                </span>
              )}
            </h2>

            {/* Mode Switcher Tabs */}
            <div role="tablist" aria-label="Comparison operation mode" className="flex bg-slate-900 border border-slate-800 rounded-lg p-0.5 text-xs font-mono">
              <button
                role="tab"
                aria-selected={opMode === 'diff'}
                aria-label="Differential Image Mode"
                onClick={() => setOpMode('diff')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                  opMode === 'diff'
                    ? 'bg-amber-500/20 text-amber-200 border border-amber-500/40 font-semibold'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                <Minus className="w-3.5 h-3.5 text-amber-400" />
                <span>Difference</span>
              </button>
              <button
                role="tab"
                aria-selected={opMode === 'stack'}
                aria-label="Co-Addition Stacking Mode"
                onClick={() => setOpMode('stack')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none ${
                  opMode === 'stack'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                <Plus className="w-3.5 h-3.5 text-cyan-400" />
                <span>Co-add</span>
              </button>
            </div>
          </div>

          <p className="text-xs text-slate-300 mt-1">
            {opMode === 'diff'
              ? 'Subtract the first exposure from the second where both sample a matching passband.'
              : 'Combine two to six independent exposures from one detector where their calibrated passbands match.'}
          </p>
          {opMode === 'diff' && <p className="text-xs text-slate-400 mt-1">Automatic proper-motion measurement is unavailable until the same source and its astrometric uncertainty are independently verified.</p>}
        </div>

        {/* Epoch & Stacking Selectors */}
        <div className="flex items-center flex-wrap gap-3 text-xs" role="toolbar" aria-label="Observation comparison and co-addition settings">
          {opMode === 'stack' && (
            <>
              <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded px-2 py-1">
                <span className="text-slate-300 text-[11px] font-medium">Method:</span>
                <select
                  value={stackMethod}
                  aria-label="Co-addition stacking statistical algorithm"
                  onChange={(e) => setStackMethod(e.target.value as any)}
                  className="bg-transparent text-cyan-300 font-mono text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                >
                  <option value="mean" className="bg-slate-900 text-slate-200">Mean</option>
                  <option value="median" disabled={extraIds.length > 0} className="bg-slate-900 text-slate-200">Median (equals pair mean)</option>
                  <option value="sum" className="bg-slate-900 text-slate-200">Sum</option>
                </select>
              </div>
            </>
          )}

          <div className="flex items-center gap-2">
            <label htmlFor="epoch1-select" className="text-slate-300 font-medium">Observation 1:</label>
            <select
              id="epoch1-select"
              value={safeIndex1}
              disabled={!!curated}
              aria-label="Select first observation for comparison"
              onChange={(e) => setIndex1(Number(e.target.value))}
              className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-slate-200 font-mono text-xs focus:outline-none focus:border-cyan-500 focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              {observations.map((o, idx) => (
                <option key={o.id} value={idx}>
                  {idx + 1}. {o.utc_date?.slice(0, 16).replace('T', ' ')} · {o.detector} · {o.obs_id}
                </option>
              ))}
            </select>
          </div>

          <ArrowRight className="w-4 h-4 text-slate-500 hidden sm:block" />

          <div className="flex items-center gap-2">
            <label htmlFor="epoch2-select" className="text-slate-300 font-medium">Observation 2:</label>
            <select
              id="epoch2-select"
              value={safeIndex2}
              disabled={!!curated}
              aria-label="Select second observation for comparison"
              onChange={(e) => setIndex2(Number(e.target.value))}
              className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-slate-200 font-mono text-xs focus:outline-none focus:border-cyan-500 focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              {observations.map((o, idx) => (
                <option key={o.id} value={idx}>
                  {idx + 1}. {o.utc_date?.slice(0, 16).replace('T', ' ')} · {o.detector} · {o.obs_id}
                </option>
              ))}
            </select>
          </div>
        </div>
        {!curated && obs1 && <details className="mt-3 rounded-lg border border-slate-700 bg-slate-950/70 p-3 text-xs text-slate-300">
          <summary className="cursor-pointer font-medium text-cyan-200">Find compatible cached partners</summary>
          <p className="mt-2">Anchor: {obs1.obs_id} · {obs1.detector}. This checks up to {partnerCandidates.length} of {partnerEligible} other listed same-detector exposures. The selected second observation is included if eligible; remaining candidates are sampled across time. It reads only cached images and calibrations; unavailable means not checked, not incompatible. Open observations in Explorer to cache their images. Results are not exhaustive.</p>
          <button type="button" onClick={checkPartners} disabled={findingPartners || partnerCandidates.length === 0}
            className="mt-2 rounded border border-cyan-700 px-3 py-1.5 text-cyan-100 hover:bg-cyan-950 disabled:opacity-50">
            {findingPartners ? 'Checking cached data…' : 'Check cached partners'}
          </button>
          {partnerCandidates.length === 0 && <p className="mt-2">No other same-detector exposures are listed.</p>}
          {partnerError && <p role="alert" className="mt-2 text-amber-200">{partnerError}</p>}
          {visiblePartners && <div className="mt-2 space-y-2">
            <p role="status">Checked {visiblePartners.checked}; unavailable {visiblePartners.unavailable}; compatible {visiblePartners.matches.length}.</p>
            {visiblePartners.matches.length === 0 && <p>No compatible partners were found among the completed checks. Unavailable entries may still be compatible.</p>}
            {visiblePartners.matches.map(match => {
              const index = observations.findIndex(row => row.id === match.frame_id);
              const row = observations[index];
              if (!row || !partnerCandidates.some(candidate => candidate.id === match.frame_id)) return null;
              return <div key={match.frame_id} className="border-t border-slate-800 pt-2">
                <p>{row.utc_date?.slice(0, 10) || 'Date unavailable'} · {row.obs_id} · {match.retained_pixels}/{match.reference_pixels} pixels · {(match.minimum_retained_overlap * 100).toFixed(1)}% minimum overlap</p>
                {index === safeIndex2 ? <p className="mt-1 text-slate-400">Current observation 2</p> : <button type="button" className="mt-1 text-cyan-200 underline" onClick={() => {
                  setIndex2(index);
                  setExtraStackIds([]);
                  setDraftExtraIds([]);
                }}>Use as observation 2</button>}
              </div>;
            })}
            <p className="text-slate-400">Selecting a match runs the regular strict comparison again; it does not establish a target detection.</p>
          </div>}
        </details>}
        {opMode === 'stack' && !curated && obs1 && observations.length > 2 && (
          <details className="mt-3 text-xs text-slate-300">
            <summary className="cursor-pointer">Add exposures from {obs1.detector} ({extraIds.length} applied; maximum 4)</summary>
            <p className="my-2">Same detector is only a starting filter. Each added exposure must also pass alignment, quality, timing and wavelength checks.</p>
            <div className="max-h-36 overflow-auto space-y-1">
              {observations.filter(o => o.detector === obs1.detector && o.id !== obs1.id && o.id !== obs2?.id).map(o => (
                <label key={o.id} className="flex items-center gap-2">
                  <input type="checkbox" checked={draftIds.includes(o.id)} disabled={!draftIds.includes(o.id) && draftIds.length >= 4}
                    onChange={e => {
                      const checked = e.target.checked;
                      setDraftExtraIds(ids => checked ? [...ids.filter(id => draftIds.includes(id)), o.id] : ids.filter(id => id !== o.id));
                    }} />
                  {o.utc_date?.replace('T', ' ').slice(0, 19) || 'Date unavailable'} · {o.detector} · {o.obs_id}
                </label>
              ))}
            </div>
            <button type="button" className="mt-2 rounded border border-cyan-700 px-2 py-1 text-cyan-200 hover:bg-cyan-950" onClick={() => {
              setExtraStackIds(draftIds);
              if (draftIds.length && stackMethod === 'median') setStackMethod('mean');
            }}>Apply {draftIds.length} additional exposure{draftIds.length === 1 ? '' : 's'}</button>
          </details>
        )}
        {!curated && Math.abs(fov - 0.04) < 0.000001 && knownRwFirst >= 0 && knownRwSecond >= 0 && (
          <div className="mt-3">
            <button type="button" className="rounded border border-cyan-700 px-3 py-1.5 text-xs text-cyan-200 hover:bg-cyan-950" onClick={() => {
              setIndex1(knownRwFirst);
              setIndex2(knownRwSecond);
              setExtraStackIds([]);
              setDraftExtraIds([]);
              setOpMode('diff');
            }}>Try checked RW Aurigae D1 field pair</button>
            <p className="mt-1 text-xs text-slate-300">A previous run retained 218 of 529 field pixels. Each run rechecks compatibility; target detection and motion are unconfirmed.</p>
          </div>
        )}
        {!curated && Math.abs(fov - 0.04) < 0.000001 && knownEpsilonFirst >= 0 && knownEpsilonSecond >= 0 && (
          <div className="mt-3">
            <button type="button" className="rounded border border-cyan-700 px-3 py-1.5 text-xs text-cyan-200 hover:bg-cyan-950" onClick={() => {
              setIndex1(knownEpsilonFirst);
              setIndex2(knownEpsilonSecond);
              setExtraStackIds([]);
              setDraftExtraIds([]);
              setOpMode('diff');
            }}>Try checked Epsilon Indi D5 field pair</button>
            <p className="mt-1 text-xs text-slate-300">A previous run retained 485 of 529 field pixels. Each run rechecks compatibility; target detection and motion are unconfirmed.</p>
          </div>
        )}
        {!curated && Math.abs(fov - 0.04) < 0.000001 && knownRdraFirst >= 0 && knownRdraSecond >= 0 && (
          <button type="button" title="Checks this pair again; images must be in cache or available from IRSA." className="mt-3 rounded border border-cyan-700 px-3 py-1.5 text-xs text-cyan-200 hover:bg-cyan-950" onClick={() => {
            setIndex1(knownRdraFirst);
            setIndex2(knownRdraSecond);
            setExtraStackIds([]);
            setDraftExtraIds([]);
          }}>Try checked R Draconis D6 field pair</button>
        )}
        {!curated && Math.abs(fov - 0.04) < 0.000001 && knownRdraFirst >= 0 && knownRdraSecond >= 0 && knownRdraThird >= 0 && (
          <div className="mt-3">
            <button type="button" title="Rechecks the three field images; they must be cached or available from IRSA."
              className="rounded border border-cyan-700 px-3 py-1.5 text-xs text-cyan-200 hover:bg-cyan-950" onClick={() => {
                const extraId = searchObservations[knownRdraThird].id;
                setIndex1(knownRdraFirst);
                setIndex2(knownRdraSecond);
                setStackMethod('mean');
                setExtraStackIds([extraId]);
                setDraftExtraIds([extraId]);
                setOpMode('stack');
              }}>Try checked three-exposure R Draconis field co-add</button>
            <p className="mt-1 text-xs text-slate-300">A previous check retained 123 of 529 field pixels. Source detection and motion remain unconfirmed; each run rechecks compatibility.</p>
          </div>
        )}
        {!curated && searchObservations.some(o => Math.abs(o.ra - 248.16722768733652) < 0.00015 && Math.abs(o.dec - 66.75502445923215) < 0.00015) && (knownRdraFirst < 0 || knownRdraSecond < 0) && (
          <p className="mt-2 text-xs text-slate-400">For a checked R Draconis field pair, search the DR1 release with detector D6 and a 2.4′ field of view.</p>
        )}
      </div>

      {obs1 && obs2 && obs1.detector !== obs2.detector && (
        <div className="mt-4 p-3 bg-amber-950/40 border border-amber-800/60 rounded-lg text-xs text-amber-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-amber-400" />
          <span>
            Notice: Selected exposures belong to different detector bands ({obs1.detector} vs {obs2.detector}). SPHEREx Linear Variable Filters (LVF) disperse distinct wavelength ranges per band; comparison across different detectors is rejected for scientific validity.
          </span>
        </div>
      )}

      {error && (
        <div role="alert" className="mt-4 p-3 bg-amber-950/40 border border-amber-800/60 rounded-lg text-xs text-amber-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-amber-400" />
          <span>{obs1?.detector} / {obs2?.detector} comparison unavailable. {error} Use Blink to inspect the exposures visually.</span>
        </div>
      )}

      {error && !loading && (frame1 || frame2) && (
        <section className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4" aria-label="Selected observation previews">
          {[frame1, frame2].map((frame, index) => <figure key={index} className="glass-card p-3">
            <figcaption className="text-sm text-slate-200 mb-2">Observation {index + 1} · {[obs1, obs2][index]?.utc_date?.slice(0, 10) || 'Date unavailable'} · {[obs1, obs2][index]?.detector}{frame && ` · Preview: ${imageProvenanceLabel(frame.image_provenance)}`}</figcaption>
            {frame ? <img src={frame.image_base64} alt={`Observation ${index + 1} field preview`} className="w-full max-w-64 mx-auto [image-rendering:pixelated]" /> : <p className="text-sm text-slate-300">Image unavailable.</p>}
          </figure>)}
          <p className="sm:col-span-2 text-xs text-slate-300">These are separate display previews. The images have not been combined or verified as compatible.</p>
        </section>
      )}

      {loading && (
        <div className="flex-1 flex flex-col items-center justify-center p-12 text-cyan-400 gap-2">
          <Loader2 className="w-8 h-8 animate-spin" />
          <span className="text-xs font-mono">
            {opMode === 'diff'
              ? 'Checking calibrated passbands and computing difference…'
              : 'Registering celestial WCS grids & computing co-add stack...'}
          </span>
        </div>
      )}

      {/* Main Analysis Display */}
      {!loading && (opMode === 'diff' ? diffResult : stackResult) && (
        <div className="mt-6 flex flex-col gap-6 flex-1">
          {/* Side-by-Side Comparison: Epoch 1, Epoch 2, [Difference | Co-Add] */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Epoch 1 Thumbnail */}
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-3 flex flex-col items-center">
              <div className="w-full flex items-center justify-between text-[11px] font-mono text-slate-400 mb-2">
                <span className="text-cyan-400 font-semibold">Observation 1 (I₁)</span>
                <span>{obs1?.utc_date?.split('T')[0]}</span>
              </div>
              <div className="w-full aspect-square bg-black rounded-lg border border-slate-800 overflow-hidden flex items-center justify-center">
                {frame1 ? (
                  <img
                    src={frame1.image_base64}
                    alt="Observation 1"
                    className="w-full h-full object-contain [image-rendering:pixelated]"
                  />
                ) : (
                  <span className="text-xs text-slate-600 font-mono">Loading...</span>
                )}
              </div>
              <span className="text-[10px] text-slate-400 font-mono mt-2">{obs1?.detector}{frame1 && ` · Preview: ${imageProvenanceLabel(frame1.image_provenance)}`}</span>
            </div>

            {/* Epoch 2 Thumbnail */}
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-3 flex flex-col items-center">
              <div className="w-full flex items-center justify-between text-[11px] font-mono text-slate-400 mb-2">
                <span className="text-indigo-400 font-semibold">Observation 2 (I₂)</span>
                <span>{obs2?.utc_date?.split('T')[0]}</span>
              </div>
              <div className="w-full aspect-square bg-black rounded-lg border border-slate-800 overflow-hidden flex items-center justify-center">
                {frame2 ? (
                  <img
                    src={frame2.image_base64}
                    alt="Observation 2"
                    className="w-full h-full object-contain [image-rendering:pixelated]"
                  />
                ) : (
                  <span className="text-xs text-slate-600 font-mono">Loading...</span>
                )}
              </div>
              <span className="text-[10px] text-slate-400 font-mono mt-2">{obs2?.detector}{frame2 && ` · Preview: ${imageProvenanceLabel(frame2.image_provenance)}`}</span>
            </div>

            {/* Third Card: Difference or Co-Add Stack */}
            {opMode === 'diff' && diffResult ? (
              <div className="bg-slate-900/60 border border-amber-800/40 rounded-xl p-3 flex flex-col items-center shadow-lg shadow-amber-950/20">
                <div className="w-full flex items-center justify-between text-[11px] font-mono mb-2">
                  <span className="text-amber-300 font-semibold">Difference (I₂ − I₁)</span>
                  {/* Palette toggle */}
                  {diffResult.colormapped_base64 && (
                    <button
                      type="button"
                      onClick={() => setDiffColormap(diffColormap === 'coolwarm' ? 'grayscale' : 'coolwarm')}
                      aria-label={`Toggle difference colormap. Current: ${diffColormap === 'coolwarm' ? 'Diverging Cool-Warm' : 'Grayscale'}`}
                      className="px-2 py-0.5 rounded text-[10px] bg-slate-800 border border-slate-700 hover:text-white flex items-center gap-1 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none text-slate-300 transition"
                    >
                      <Palette className="w-3 h-3 text-cyan-400" />
                      <span>{diffColormap === 'coolwarm' ? 'Diverging' : 'Grayscale'}</span>
                    </button>
                  )}
                  <span className="text-slate-400">RMS {diffResult.diff_stats.rms_diff_mjy_sr.toPrecision(4)}</span>
                </div>
                <div className="comparison-mask w-full aspect-square rounded-lg border border-slate-700 overflow-hidden flex items-center justify-center relative">
                  <img
                    src={diffColormap === 'coolwarm' && diffResult.colormapped_base64 ? diffResult.colormapped_base64 : diffResult.image_base64}
                    alt="Difference Frame"
                    className="w-full h-full object-contain [image-rendering:pixelated]"
                  />
                </div>
                <div className="w-full flex flex-col items-center gap-1 mt-2">
                  <span className="text-[10px] text-slate-400 font-mono">
                    Mid-scale = 0 residual · Checkerboard = excluded pixels
                  </span>
                  {/* Diverging palette colorbar legend */}
                  <div className="w-full flex items-center justify-between text-[9px] font-mono text-slate-400 px-1 pt-1 border-t border-slate-800/60">
                    <span className="text-blue-400 font-semibold">◄ Lower brightness (−ΔF)</span>
                    <span className="text-slate-300">0 Residual</span>
                    <span className="text-rose-400 font-semibold">Higher brightness (+ΔF) ►</span>
                  </div>
                </div>
              </div>
            ) : stackResult ? (
              <div className="bg-slate-900/60 border border-cyan-800/40 rounded-xl p-3 flex flex-col items-center shadow-lg shadow-cyan-950/20">
                <div className="w-full flex items-center justify-between text-[11px] font-mono mb-2">
                  <span className="text-cyan-300 font-semibold flex items-center gap-1">
                    <Layers className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Co-Add Stack ({stackResult.method.toUpperCase()})</span>
                  </span>
                </div>
                <div className="comparison-mask w-full aspect-square rounded-lg border border-slate-700 overflow-hidden flex items-center justify-center relative">
                  <img
                    src={stackResult.image_base64}
                    alt="Stacked Co-Add Frame"
                    className="w-full h-full object-contain [image-rendering:pixelated]"
                  />
                </div>
                <span className="text-[10px] text-cyan-400 font-mono mt-2">
                  N={stackResult.frame_count} Co-added frames • {stackResult.dimensions.join('×')} px
                </span>
                <span className="text-[10px] text-slate-400 font-mono mt-1">Checkerboard = excluded pixels</span>
              </div>
            ) : null}
          </div>

          {calibration && (
            <details className="rounded-lg border border-slate-700 bg-slate-900 p-3 text-sm">
              <summary className="cursor-pointer text-cyan-200">
                Verified CWAVE/CBAND · {obs1?.detector} · {calibration.retained_pixels}/{calibration.reference_pixels} pixels matched
              </summary>
              <p className="mt-2 text-slate-300">Aligned by celestial WCS to the nearest native pixel within 0.5 pixels.</p>
              <p className="text-slate-300">
                Minimum nominal passband overlap {(calibration.minimum_passband_overlap * 100).toFixed(0)}%.
                Lowest retained overlap {(calibration.minimum_retained_overlap * 100).toFixed(1)}%.
                Excluded pixels are transparent.
              </p>
              <p className="text-slate-300">Propagated variance assumes independent exposures. PSF differences and common calibration errors are outside this estimate.</p>
              {calibration.retained_pixels / calibration.reference_pixels < 0.1 && <p className="text-amber-200">Fewer than 10% of reference pixels passed the checks. This sparse result may not support a useful field comparison.</p>}
              <ul className="mt-2 space-y-1">
                {calibration.calibrations.map(source => (
                  <li key={source.observation_id}>
                    <a className="text-cyan-200 underline" href={source.calibration_url}>
                      {source.observation_id} · {source.science_release.toUpperCase()} calibration
                    </a>
                    <span className="block text-slate-300">{source.checksum_source}</span>
                    {source.sha256 && <span className="block break-all text-slate-300">SHA-256 {source.sha256}</span>}
                    {source.association_url && <a className="text-cyan-200 underline" href={source.association_url}>IRSA association for a checked example using this calibration ID</a>}
                  </li>
                ))}
              </ul>
            </details>
          )}

          {/* Mode 1 Details: Astrometric Motion & Differencing */}
          {opMode === 'diff' && motionResult && (
            <div className="bg-slate-900/60 border border-indigo-900/50 rounded-xl p-5 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-indigo-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Move className="w-4 h-4 text-cyan-400" />
                  Candidate motion estimate
                </h4>
                <span className={`text-[10px] font-semibold px-2.5 py-0.5 rounded-full border ${
                  motionResult.motion_class.includes('High')
                    ? 'bg-amber-950/80 text-amber-300 border-amber-800'
                    : 'bg-slate-800 text-slate-300 border-slate-700'
                }`}>
                  {motionResult.motion_class}
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 font-mono text-xs">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Candidate annualized shift</span>
                  <span className="text-cyan-300 font-bold text-sm">
                    {motionResult.proper_motion_arcsec_yr}″/yr
                  </span>
                  <span className="text-[9px] text-slate-500 block">({motionResult.proper_motion_mas_yr} mas/yr)</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Net Angular Shift</span>
                  <span className="text-slate-100 font-bold text-sm">{motionResult.displacement_arcsec}″</span>
                  <span className="text-[9px] text-slate-500 block">({motionResult.displacement_pixels} pixels)</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Vector (Δx, Δy)</span>
                  <span className="text-indigo-300 font-bold text-sm">
                    ({motionResult.dx_pixels}, {motionResult.dy_pixels}) px
                  </span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Position Angle (PA)</span>
                  <span className="text-amber-400 font-bold text-sm">{motionResult.position_angle_deg}°</span>
                  <span className="text-[9px] text-slate-500 block">N through E</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Heuristic score</span>
                  <span className="text-emerald-400 font-bold text-sm">
                    {motionResult.confidence_score.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {opMode === 'diff' && diffResult && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Difference image statistics
                </h4>
                {diffResult.diff_stats.alignment_method && (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold">
                    {diffResult.diff_stats.alignment_method === 'wcs_reproject'
                      ? 'Astropy / Reproject WCS Alignment'
                      : diffResult.diff_stats.alignment_method === 'fft_shift'
                      ? '2D FFT Cross-Correlation Shift'
                      : 'Nearest native pixel via celestial WCS'}
                  </span>
                )}
              </div>
              <div className="comparison-metrics grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">RMS Difference</span>
                  <span className="text-cyan-400 font-bold text-sm">{diffResult.diff_stats.rms_diff_mjy_sr.toPrecision(5)} MJy/sr</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">Peak Positive Flux</span>
                  <span className="text-emerald-400 font-bold text-sm">+{diffResult.diff_stats.peak_positive_flux.toPrecision(5)} MJy/sr</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">Peak Negative Flux</span>
                  <span className="text-rose-400 font-bold text-sm">{diffResult.diff_stats.peak_negative_flux.toPrecision(5)} MJy/sr</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">Median propagated uncertainty</span>
                  <span className="text-slate-200 font-bold text-sm">±{diffResult.diff_stats.sigma_mjy_sr.toPrecision(5)} MJy/sr</span>
                </div>
              </div>

              <div className="p-3 bg-cyan-950/20 border border-cyan-800/40 rounded-lg text-[11px] text-cyan-300 space-y-1">
                <p className="font-semibold">Differencing Interpretation:</p>
                <p className="text-slate-400">
                  A positive residual means the second sample is brighter. Point-spread changes, small offsets, and background changes can also produce residuals.
                </p>
              </div>
            </div>
          )}

          {/* Mode 2 Details: Co-Addition & Stacking Telemetry */}
          {opMode === 'stack' && stackResult && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-cyan-300 uppercase tracking-wider flex items-center gap-1.5">
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                  Co-addition statistics
                </h4>
                {stackResult.alignment_method && (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold">
                    {stackResult.alignment_method === 'wcs_reproject'
                      ? 'Astropy / Reproject WCS Registration'
                      : stackResult.alignment_method === 'fft_shift'
                      ? 'FFT Sub-Pixel Registration'
                      : 'Nearest native pixel via celestial WCS'}
                  </span>
                )}
              </div>

              <div className="comparison-metrics grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">SNR Improvement</span>
                  <span className="text-emerald-400 font-bold text-sm">
                    {stackResult.snr_improvement_factor != null ? `${stackResult.snr_improvement_factor}×` : 'Unavailable'}
                  </span>
                  <span className="text-[10px] text-slate-500 block"></span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">Median propagated uncertainty</span>
                  <span className="text-cyan-300 font-bold text-sm">
                    ±{stackResult.noise_stats.stacked_noise_sigma.toPrecision(5)} MJy/sr
                  </span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">Peak co-add brightness</span>
                  <span className="text-amber-400 font-bold text-sm">
                    {stackResult.noise_stats.max_flux_mjy_sr.toPrecision(5)} MJy/sr
                  </span>
                  <span className="text-[10px] text-slate-400 block">Mean: {stackResult.noise_stats.mean_flux_mjy_sr.toPrecision(5)}</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400 text-[11px] block">Co-added exposures</span>
                  <span className="text-slate-100 font-bold text-sm">
                    {stackResult.frame_count} Frames
                  </span>
                  <span className="text-[10px] text-indigo-300 block">Method: {stackResult.method.toUpperCase()}</span>
                </div>
              </div>

              {curated ? (
                <p className="text-xs text-slate-300">
                  Co-add values describe the matched field pixels. The reported uncertainty is propagated from the two exposures.
                </p>
              ) : <div className="p-3 bg-cyan-950/20 border border-cyan-800/40 rounded-lg text-[11px] text-cyan-300 space-y-1">
                <p className="font-semibold flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-cyan-400" />
                  Astronomical Co-Addition Discovery Benefit:
                </p>
                <p className="text-slate-400">
                  Combining compatible exposures can reduce independent random noise, but the gain depends on the data and is not measured here. Moving sources can be blurred; a difference or blink can help identify changes that warrant further investigation.
                </p>
              </div>}
            </div>
          )}

          {/* Accessible Tabular Data View for Screen Readers & Keyboard Users */}
          <details className="text-[10px] font-mono group border border-slate-800 rounded bg-slate-950/70 p-2.5">
            <summary className="cursor-pointer text-slate-300 hover:text-cyan-300 font-sans font-medium flex items-center justify-between select-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded px-1 py-0.5 outline-none">
              <span className="flex items-center gap-1.5">
                <Table className="w-3.5 h-3.5 text-cyan-400" />
                <span>View Accessible Comparison Metrics Table</span>
              </span>
              <span className="text-[9px] text-slate-400 font-mono">
                {opMode === 'diff' ? 'Difference image statistics' : 'Co-addition statistics'}
              </span>
            </summary>
            <div className="mt-2.5 overflow-x-auto max-h-48 overflow-y-auto">
              <table className="w-full text-left border-collapse" role="table" aria-label="SPHEREx Comparison Quantitative Metrics">
                <caption className="sr-only">SPHEREx quantitative comparison and astrometric motion metrics</caption>
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 text-[9px] uppercase tracking-wider">
                    <th scope="col" className="py-1 px-1.5 font-semibold">Metric</th>
                    <th scope="col" className="py-1 px-1.5 font-semibold text-right">Value</th>
                    <th scope="col" className="py-1 px-1.5 font-semibold text-left pl-3">Units / Meaning</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {opMode === 'diff' && diffResult ? (
                    <>
                      <tr className="hover:bg-slate-900/60 transition">
                        <td className="py-1 px-1.5 font-medium text-slate-200">RMS Difference</td>
                        <td className="py-1 px-1.5 text-right font-mono text-cyan-300">{diffResult.diff_stats.rms_diff_mjy_sr}</td>
                        <td className="py-1 px-1.5 pl-3 text-slate-400">MJy/sr (Root mean square residual)</td>
                      </tr>
                      <tr className="hover:bg-slate-900/60 transition">
                        <td className="py-1 px-1.5 font-medium text-slate-200">Peak Positive Flux</td>
                        <td className="py-1 px-1.5 text-right font-mono text-emerald-400">+{diffResult.diff_stats.peak_positive_flux}</td>
                        <td className="py-1 px-1.5 pl-3 text-slate-400">MJy/sr (Maximum brightened pixel)</td>
                      </tr>
                      <tr className="hover:bg-slate-900/60 transition">
                        <td className="py-1 px-1.5 font-medium text-slate-200">Peak Negative Flux</td>
                        <td className="py-1 px-1.5 text-right font-mono text-rose-400">{diffResult.diff_stats.peak_negative_flux}</td>
                        <td className="py-1 px-1.5 pl-3 text-slate-400">MJy/sr (Maximum dimmed pixel)</td>
                      </tr>
                      <tr className="hover:bg-slate-900/60 transition">
                        <td className="py-1 px-1.5 font-medium text-slate-200">Median propagated uncertainty</td>
                        <td className="py-1 px-1.5 text-right font-mono text-slate-200">±{diffResult.diff_stats.sigma_mjy_sr}</td>
                        <td className="py-1 px-1.5 pl-3 text-slate-400">MJy/sr (1-sigma background dispersion)</td>
                      </tr>
                      {motionResult && (
                        <>
                          <tr className="hover:bg-slate-900/60 transition">
                            <td className="py-1 px-1.5 font-medium text-slate-200">Candidate annualized shift (μ)</td>
                            <td className="py-1 px-1.5 text-right font-mono text-cyan-300 font-bold">{motionResult.proper_motion_arcsec_yr}″/yr</td>
                            <td className="py-1 px-1.5 pl-3 text-slate-400">{motionResult.proper_motion_mas_yr} mas/yr ({motionResult.motion_class})</td>
                          </tr>
                          <tr className="hover:bg-slate-900/60 transition">
                            <td className="py-1 px-1.5 font-medium text-slate-200">Position Angle (PA)</td>
                            <td className="py-1 px-1.5 text-right font-mono text-amber-300">{motionResult.position_angle_deg}°</td>
                            <td className="py-1 px-1.5 pl-3 text-slate-400">Degrees (North through East)</td>
                          </tr>
                          <tr className="hover:bg-slate-900/60 transition">
                            <td className="py-1 px-1.5 font-medium text-slate-200">Net Angular Shift</td>
                            <td className="py-1 px-1.5 text-right font-mono text-slate-200">{motionResult.displacement_arcsec}″</td>
                            <td className="py-1 px-1.5 pl-3 text-slate-400">{motionResult.displacement_pixels} pixels across baseline</td>
                          </tr>
                        </>
                      )}
                    </>
                  ) : stackResult ? (
                    <>
                      <tr className="hover:bg-slate-900/60 transition">
                        <td className="py-1 px-1.5 font-medium text-slate-200">SNR Improvement</td>
                        <td className="py-1 px-1.5 text-right font-mono text-emerald-400 font-bold">
                          {stackResult.snr_improvement_factor != null ? `${stackResult.snr_improvement_factor}×` : 'N/A'}
                        </td>
                        <td className="py-1 px-1.5 pl-3 text-slate-400">No measured SNR gain</td>
                      </tr>
                      <tr className="hover:bg-slate-900/60 transition">
                        <td className="py-1 px-1.5 font-medium text-slate-200">Co-Added Frames (N)</td>
                        <td className="py-1 px-1.5 text-right font-mono text-cyan-300">{stackResult.frame_count}</td>
                        <td className="py-1 px-1.5 pl-3 text-slate-400">Method: {stackResult.method.toUpperCase()}</td>
                      </tr>
                      <tr className="hover:bg-slate-900/60 transition">
                        <td className="py-1 px-1.5 font-medium text-slate-200">Stacked Noise (σ)</td>
                        <td className="py-1 px-1.5 text-right font-mono text-slate-200">±{stackResult.noise_stats.stacked_noise_sigma}</td>
                        <td className="py-1 px-1.5 pl-3 text-slate-400">MJy/sr</td>
                      </tr>
                      <tr className="hover:bg-slate-900/60 transition">
                        <td className="py-1 px-1.5 font-medium text-slate-200">Peak Co-Add Brightness</td>
                        <td className="py-1 px-1.5 text-right font-mono text-slate-200">{stackResult.noise_stats.max_flux_mjy_sr}</td>
                        <td className="py-1 px-1.5 pl-3 text-slate-400">MJy/sr</td>
                      </tr>
                      <tr className="hover:bg-slate-900/60 transition">
                        <td className="py-1 px-1.5 font-medium text-slate-200">Mean Co-Add Brightness</td>
                        <td className="py-1 px-1.5 text-right font-mono text-slate-200">{stackResult.noise_stats.mean_flux_mjy_sr}</td>
                        <td className="py-1 px-1.5 pl-3 text-slate-400">MJy/sr</td>
                      </tr>
                    </>
                  ) : null}
                </tbody>
              </table>
            </div>
          </details>
        </div>
      )}
    </div>
  );
};
