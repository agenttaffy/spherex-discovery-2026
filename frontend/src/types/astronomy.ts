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
  image_base64: string;
}
