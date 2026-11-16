const labels: Record<string, string> = {
  live_archive_cutout: 'live IRSA cutout service',
  cached_archive_cutout: 'cached IRSA service cutout',
  live_cloud_cutout: 'IRSA public AWS cloud image cutout',
  cached_cloud_cutout: 'cached IRSA AWS cloud image cutout',
  cached_demo_cutout: 'cached demonstration cutout',
  simulated: 'simulated fixture',
  local_fixture: 'local fixture',
};

/** Image source describes the pixels; it is separate from search provenance. */
export function imageProvenanceLabel(provenance?: string | null): string {
  return (provenance && labels[provenance]) || 'unknown';
}
