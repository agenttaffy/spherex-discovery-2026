import type { CubeChannel } from './cubeCsv';

/** Only plot finite, quality-accepted measured values; never fill missing bands. */
export function measuredSkyPixels(channels: CubeChannel[]): CubeChannel[] {
  return channels.filter(point => point.status === 'measured' && point.hits > 0
    && point.wavelength_um != null && Number.isFinite(point.wavelength_um)
    && point.surface_brightness_mjy_sr != null && Number.isFinite(point.surface_brightness_mjy_sr));
}
