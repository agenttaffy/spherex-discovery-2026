import type { ObservationRecord } from '../types/astronomy';

/** Detector must match for both local IDs and portable observation IDs. */
export function findRequestedObservation(observations: ObservationRecord[], requestedId: string, detector?: string | null): number {
  return observations.findIndex(observation => (observation.id === requestedId || observation.obs_id === requestedId)
    && (!detector || observation.detector === detector));
}

export function unavailableObservationMessage(requestedId: string, hasResults: boolean): string {
  return `The requested observation ${requestedId} is not in these search results. ${hasResults ? 'Showing the first available observation instead.' : 'No observation is displayed.'} Results may be limited or the archive unavailable.`;
}
