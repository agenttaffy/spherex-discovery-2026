import type { CubeChannel } from './cubeCsv';

/** Keep detector grouping tied to archive metadata, not inferred brightness. */
export function detectorChannels(channels: CubeChannel[], detector: number): CubeChannel[] {
  return channels.filter(point => point.detector === detector);
}

export function firstUsefulChannel(channels: CubeChannel[], detector: number): number | null {
  const group = detectorChannels(channels, detector);
  return (group.find(point => point.status === 'measured') ?? group[0])?.channel ?? null;
}

/** Loop through measured channels only; unavailable values must remain gaps. */
export function nextMeasuredChannel(channels: CubeChannel[], current: number): number | null {
  const selected = channels.find(point => point.channel === current);
  if (!selected) return null;
  const available = detectorChannels(channels, selected.detector).filter(point => point.status === 'measured');
  if (available.length < 2) return null;
  const index = available.findIndex(point => point.channel === current);
  return available[(index + 1) % available.length].channel;
}
