export interface ObservationRecord {
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

export interface FrameResponse {
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

export interface DiffResult {
  eligible: boolean;
  frame_1: string;
  frame_2: string;
  diff_stats: {
    rms_diff_mjy_sr: number;
    peak_positive_flux: number;
    peak_negative_flux: number;
    sigma_mjy_sr: number;
  };
  dimensions?: [number, number];
  image_base64: string;
}

export interface CatalogSource {
  source_id: string;
  ra: number;
  dec: number;
  g_mag?: number | null;
  bp_rp?: number | null;
  pm_ra?: number;
  pm_dec?: number;
  parallax_mas?: number | null;
  designation: string;
  catalog: string;
  star_type: string;
  separation_arcsec: number;
}

export interface PhotometryPoint {
  obs_id: string;
  frame_id: string;
  mjd?: number | null;
  utc_date?: string | null;
  detector: string;
  collection: string;
  net_flux_mjy_sr: number;
  peak_flux_mjy_sr: number;
  aperture_flux_sum: number;
  background_median: number;
  snr: number;
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
