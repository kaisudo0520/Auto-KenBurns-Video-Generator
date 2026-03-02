// ========================================
// Common Types
// ========================================

/**
 * Timestamp type (ISO 8601 string)
 */
export type Timestamp = string;

/**
 * Pagination info
 */
export interface Pagination {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

/**
 * Project status enumeration
 */
export type ProjectStatus = 'draft' | 'processing' | 'completed' | 'failed';

/**
 * Job status enumeration
 */
export type JobStatus =
  | 'queued'
  | 'preparing'
  | 'rendering'
  | 'encoding'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'paused';

/**
 * Render stage enumeration
 */
export type RenderStage =
  | 'preparing'
  | 'loading_images'
  | 'detecting_subjects'
  | 'generating_paths'
  | 'processing_audio'
  | 'rendering_frames'
  | 'encoding_video'
  | 'finalizing';

/**
 * Output format enumeration
 */
export type OutputFormat = 'mp4_h264' | 'mp4_h265';

/**
 * Resolution enumeration
 */
export type Resolution = '720p' | '1080p' | '1440p' | '4k';

/**
 * Frame rate options
 */
export type FrameRate = 24 | 30 | 60;

/**
 * Encoder options
 */
export type Encoder = 'h264_nvenc' | 'h265_nvenc' | 'libx264' | 'libx265';

/**
 * Ken-Burns effect type
 */
export type KenBurnsEffect =
  | 'auto'
  | 'pan_left'
  | 'pan_right'
  | 'pan_up'
  | 'pan_down'
  | 'zoom_in'
  | 'zoom_out'
  | 'compose_pan_zoom'
  | 'random';

/**
 * Easing function type
 */
export type EasingFunction = 'linear' | 'ease_in' | 'ease_out' | 'ease_in_out';

/**
 * File status
 */
export type FileStatus = 'uploading' | 'processing' | 'ready' | 'error';

/**
 * Sort order
 */
export type SortOrder = 'asc' | 'desc';

/**
 * Bounding box for region detection
 */
export interface BoundingBox {
  x: number;      // Normalized 0-1
  y: number;      // Normalized 0-1
  width: number;  // Normalized 0-1
  height: number; // Normalized 0-1
}

/**
 * Region type for subject detection
 */
export type RegionType = 'person' | 'face' | 'object';

/**
 * Subject region detected in image
 */
export interface SubjectRegion {
  type: RegionType;
  bounds: BoundingBox;
  confidence: number;
}

/**
 * Resolution configuration
 */
export interface ResolutionConfig {
  value: Resolution;
  label: string;
  width: number;
  height: number;
}

/**
 * Frame rate configuration
 */
export interface FrameRateConfig {
  value: FrameRate;
  label: string;
}

/**
 * Output format configuration
 */
export interface OutputFormatConfig {
  value: OutputFormat;
  label: string;
  description: string;
}

/**
 * Encoder configuration
 */
export interface EncoderConfig {
  value: Encoder;
  label: string;
  hardware: boolean;
}

/**
 * Ken-Burns effect configuration
 */
export interface KenBurnsEffectConfig {
  value: KenBurnsEffect;
  label: string;
  default?: boolean;
}

/**
 * Easing function configuration
 */
export interface EasingFunctionConfig {
  value: EasingFunction;
  label: string;
  default?: boolean;
}

/**
 * Validation warning
 */
export interface ValidationWarning {
  field: string;
  message: string;
}

/**
 * Validation result
 */
export interface ValidationResult {
  valid: boolean;
  warnings?: ValidationWarning[];
  errors?: ValidationWarning[];
}
