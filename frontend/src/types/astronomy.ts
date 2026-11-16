export interface ObservationRecord {
  search_provenance?: string;
  search_snapshot_saved?: string | null;
  catalog_coverage?: 'inside' | 'outside' | null;
  id: string;
  obs_id: string;
  collection: string;
  detector: string;
  mjd?: number;
  utc_date?: string;
  em_min?: number;
  em_max?: number;
  access_url: string;
  ra: number;
  dec: number;
}

export interface PixelStats {
  min_mjy_sr: number;
  max_mjy_sr: number;
  mean_mjy_sr: number;
  std_mjy_sr: number;
  median_mjy_sr: number;
}

export interface FlagSummary {
  quality_state?: string;
  flagged_pixels: number;
  total_pixels: number;
  flag_breakdown: Record<string, number>;
}

export interface WCSInfo {
  crval1?: number;
  crval2?: number;
  crpix1?: number;
  crpix2?: number;
  cdelt1?: number;
  cdelt2?: number;
  ctype1?: string;
  ctype2?: string;
}

export interface TargetPrediction {
  ra: number;
  dec: number;
  mjd: number;
  pixel: { x: number; y: number; inside: boolean } | null;
  reference_url: string;
}

export interface PhotometryEvidence {
  status: 'unavailable';
  aperture_status: 'not_checked' | 'unavailable' | 'field_sample_only';
  reason: string;
  epsf_present: boolean;
  core_pixels: number | null;
  usable_core_pixels: number | null;
  background_pixels: number | null;
}

export interface FrameResponse {
  target_predictions?: Record<string, TargetPrediction>;
  target_photometry?: Record<string, PhotometryEvidence>;
  footprint_icrs_deg?: number[][] | null;
  frame_id: string;
  obs_id: string;
  collection: string;
  detector: string;
  utc_date?: string;
  dimensions: number[];
  pixel_stats: PixelStats;
  flag_summary: FlagSummary;
  wcs: WCSInfo;
  image_base64: string;
  colormapped_base64?: string;
  provenance_url: string;
  is_synthetic?: boolean;
  image_provenance?: string;
}

export interface DemoPreset {
  id: string;
  name: string;
  ra: number;
  dec: number;
  description: string;
  target_type: string;
  default_collection: string;
  notable_feature: string;
}

export interface ComparisonCalibration {
  alignment: string;
  compatibility: string;
  minimum_passband_overlap: number;
  minimum_retained_overlap: number;
  retained_pixels: number;
  reference_pixels: number;
  calibrations: Array<{
    observation_id: string;
    science_release: string;
    plane_id: string;
    calibration_url: string;
    md5: string;
  }>;
}

export interface DiffResult {
  eligible: boolean;
  frame_1: string;
  frame_2: string;
  calibration: ComparisonCalibration;
  diff_stats: {
    rms_diff_mjy_sr: number;
    peak_positive_flux: number;
    peak_negative_flux: number;
    sigma_mjy_sr: number;
    alignment_method?: string;
  };
  dimensions?: [number, number];
  image_base64: string;
  colormapped_base64?: string;
}

export interface CatalogSource {
  source_id: string;
  ra: number;
  dec: number;
  g_mag?: number | null;
  bp_rp?: number | null;
  pm_ra?: number | null;
  pm_dec?: number | null;
  parallax_mas?: number | null;
  designation: string;
  catalog: string;
  star_type: string;
  separation_arcsec: number;
  provenance?: string;
  catalog_source?: string;
}

export interface PhotometryPoint {
  obs_id: string;
  frame_id: string;
  mjd?: number | null;
  utc_date?: string | null;
  detector: string;
  collection: string;
  status?: string;
  valid?: boolean;
  reason?: string | null;
  net_flux_mjy_sr: number | null;
  flux_err_mjy_sr?: number | null;
  peak_flux_mjy_sr: number | null;
  aperture_flux_sum: number | null;
  background_median: number | null;
  snr: number | null;
  coverage_fraction?: number;
}

export interface LightCurveSeries {
  total_points: number;
  is_variable: boolean;
  variability_index: number;
  mean_flux_mjy_sr: number;
  std_flux_mjy_sr: number;
  min_flux_mjy_sr: number;
  max_flux_mjy_sr: number;
  amplitude_delta_mjy_sr: number;
  points: PhotometryPoint[];
  target?: {
    ra: number;
    dec: number;
  };
}

export interface AstrometricMotion {
  dx_pixels: number;
  dy_pixels: number;
  displacement_pixels: number;
  displacement_arcsec: number;
  position_angle_deg: number;
  delta_time_days: number;
  delta_time_years: number;
  proper_motion_arcsec_yr: number;
  proper_motion_mas_yr: number;
  motion_class: string;
  centroid_detected: boolean;
  centroid_1?: [number, number] | null;
  centroid_2?: [number, number] | null;
  pixel_scale_arcsec: number;
  confidence_score: number;
}

export interface DiscoveryReport {
  report_id: string;
  timestamp: string;
  target: {
    name: string;
    ra_deg: number;
    dec_deg: number;
    sexagesimal: string;
    target_type?: string;
  };
  motion_analysis?: AstrometricMotion;
  photometry_analysis?: LightCurveSeries;
  observations_summary: any[];
  markdown_report: string;
  irsa_doi: string;
}

export interface SpectrumBandPoint {
  uncertainty_source?: string;
  detector: string;
  band_idx: number;
  wavelength_um: number;
  wavelength_min_um: number;
  wavelength_max_um: number;
  bandwidth_um?: number;
  calibration_source?: string;
  color: string;
  flux_mjy_sr: number;
  flux_density_mjy: number | null;
  peak_flux_mjy_sr: number;
  flux_err_mjy_sr: number;
  snr: number;
  is_observed: boolean;
  obs_id?: string | null;
}

export interface SpectralChannel {
  channel_index: number;
  detector: string;
  color: string;
  wavelength_um: number;
  flux_mjy_sr: number;
  flux_density_mjy: number;
  is_observed_band: boolean;
}

export interface SpectrumSummary {
  peak_wavelength_um?: number | null;
  peak_detector?: string | null;
  peak_flux_mjy_sr?: number | null;
  peak_is_measured?: boolean;
  estimated_temperature_k?: number | null;
  continuum_shape: string;
  integrated_flux_mjy_sr_um?: number | null;
  total_channels: number;
  temperature_fit?: any;
}

export interface SpectrumResponse {
  target: {
    ra: number;
    dec: number;
  };
  total_observed_bands: number;
  bands: SpectrumBandPoint[];
  channels_102: SpectralChannel[];
  continuum_curve: Array<{ wavelength_um: number; flux_mjy_sr: number }>;
  summary: SpectrumSummary;
}

export interface StackResult {
  success: boolean;
  method: 'mean' | 'median' | 'sum';
  frame_count: number;
  frame_ids: string[];
  calibration: ComparisonCalibration;
  dimensions: [number, number];
  snr_improvement_factor: number | null;
  snr_gain_status?: string;
  theoretical_snr_gain: number | null;
  theoretical_gain_model?: string;
  noise_stats: {
    reference_noise_sigma: number | null;
    stacked_noise_sigma: number;
    mean_flux_mjy_sr: number;
    max_flux_mjy_sr: number;
    min_flux_mjy_sr: number;
  };
  alignment_method: string;
  image_base64?: string;
}

