import type { ObservationRecord } from '../types/astronomy';

/** Sample at most 12 distinct same-detector exposures across available times. */
export function comparisonCandidates(observations: ObservationRecord[], anchor: ObservationRecord, limit = 12, preferredId?: string): ObservationRecord[] {
  const time = (row: ObservationRecord) => typeof row.mjd === 'number' && Number.isFinite(row.mjd) ? row.mjd : Infinity;
  const ordered = observations.filter(row => row.id !== anchor.id && row.obs_id !== anchor.obs_id && row.detector === anchor.detector)
    .slice().sort((a, b) => (time(a) - time(b)) || a.id.localeCompare(b.id));
  const preferred = ordered.find(row => row.id === preferredId);
  const seen = new Set<string>();
  const unique = ordered.filter(row => {
    if (preferred && row.obs_id === preferred.obs_id && row.id !== preferred.id) return false;
    if (seen.has(row.obs_id)) return false;
    seen.add(row.obs_id);
    return true;
  });
  if (limit <= 0) return [];
  const remaining = preferred ? unique.filter(row => row.id !== preferred.id) : unique;
  const slots = limit - (preferred ? 1 : 0);
  const sampled = remaining.length <= slots ? remaining : slots === 1 ? remaining.slice(0, 1)
    : slots > 1 ? Array.from({ length: slots }, (_, i) => remaining[Math.round(i * (remaining.length - 1) / (slots - 1))]) : [];
  return preferred ? [preferred, ...sampled] : sampled;
}
