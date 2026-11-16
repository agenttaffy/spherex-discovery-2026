export interface CubeChannel {
  channel: number;
  detector: number;
  subchannel: number;
  wavelength_um: number | null;
  wavelength_min_um: number | null;
  wavelength_max_um: number | null;
  bandwidth_um: number | null;
  surface_brightness_mjy_sr: number | null;
  archive_brightness_mjy_sr: number | null;
  hits: number;
  flags: number;
  status: string;
}

export interface CubeData {
  source: 'irsa_archive' | 'cloud_dr1_pinned' | 'cached_dr1_preview';
  tile: number;
  fits_url: string;
  ra: number;
  dec: number;
  pixel: { x: number; y: number; ra: number; dec: number };
  cloud?: { cloud_url: string; etag: string; bytes_transferred: number; discovery: string; pinned_version: string | null };
  preview?: {
    generated_on: string;
    sample_coordinate: { ra: number; dec: number };
    archive_failure: 'archive_unreachable' | 'archive_unreadable' | 'cached_preview_requested';
    provenance: { etag_md5: string; sha256: string | null };
  };
  channels: CubeChannel[];
  channel_map: { channel: number; center_x: number; center_y: number; pixels: (number | null)[][] };
}

/** Export sky-pixel samples, retaining gaps and explicitly labeling unfiltered values. */
export function cubeSpectrumCsv(data: CubeData): string {
  const fields = ['channel', 'detector', 'detector_channel', 'wavelength_um', 'wavelength_min_um', 'wavelength_max_um', 'bandwidth_um', 'surface_brightness_mjy_sr', 'archive_brightness_unfiltered_mjy_sr', 'hits', 'flags', 'status', 'sample_kind', 'requested_ra_deg', 'requested_dec_deg', 'sample_ra_deg', 'sample_dec_deg', 'tile', 'pixel_x', 'pixel_y', 'source', 'fits_url', 'cloud_url', 'cloud_etag', 'cloud_discovery', 'preview_generated_on', 'archive_etag_md5', 'fits_sha256'];
  const quote = (value: string | number | null) => `"${String(value ?? '').replace(/"/g, '""')}"`;
  const rows = data.channels.map(point => [point.channel, point.detector, point.subchannel,
    point.wavelength_um, point.wavelength_min_um, point.wavelength_max_um, point.bandwidth_um,
    point.surface_brightness_mjy_sr, point.archive_brightness_mjy_sr, point.hits, point.flags,
    point.status, 'coadded_sky_pixel_not_target_photometry', data.ra, data.dec, data.pixel.ra,
    data.pixel.dec, data.tile, data.pixel.x, data.pixel.y, data.source, data.fits_url,
    data.cloud?.cloud_url ?? null, data.cloud?.etag ?? null, data.cloud?.discovery ?? null,
    data.preview?.generated_on ?? null, data.preview?.provenance.etag_md5 ?? null,
    data.preview?.provenance.sha256 ?? null].map(quote).join(','));
  return [fields.join(','), ...rows].join('\r\n');
}
