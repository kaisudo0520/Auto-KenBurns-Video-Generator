// ========================================
// Settings Types
// ========================================

import {
  Resolution,
  FrameRate,
  OutputFormat,
  Encoder,
  KenBurnsEffect,
  EasingFunction,
  ResolutionConfig,
  FrameRateConfig,
  OutputFormatConfig,
  EncoderConfig,
  KenBurnsEffectConfig,
  EasingFunctionConfig,
  ValidationResult,
} from './common';

/**
 * All available settings options
 */
export interface SettingsOptions {
  resolutions: ResolutionConfig[];
  frame_rates: FrameRateConfig[];
  output_formats: OutputFormatConfig[];
  encoders: EncoderConfig[];
  kenburns_effects: KenBurnsEffectConfig[];
  easing_functions: EasingFunctionConfig[];
}

/**
 * GPU information
 */
export interface GPUInfo {
  available: boolean;
  name?: string;
  memory_total?: number;      // MB
  memory_used?: number;       // MB
  cuda_version?: string;
  nvenc_available?: boolean;
}

/**
 * Storage information
 */
export interface StorageInfo {
  temp_used: number;         // bytes
  temp_total: number;        // bytes
  output_used: number;       // bytes
  output_total: number;      // bytes
}

/**
 * Version information
 */
export interface VersionInfo {
  api: string;
  ffmpeg: string;
  engine: string;
}

/**
 * System status
 */
export interface SystemStatus {
  gpu: GPUInfo;
  storage: StorageInfo;
  render_queue: {
    running: number;
    queued: number;
    max_concurrent: number;
  };
  version: VersionInfo;
}

/**
 * Validate settings request
 */
export interface ValidateSettingsRequest {
  project_id?: string;
  settings?: {
    resolution?: Resolution;
    fps?: FrameRate;
    images_total_duration?: number;
    audio_total_duration?: number;
  };
}

/**
 * Storage format helpers
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * Get resolution dimensions
 */
export function getResolutionDimensions(resolution: Resolution): { width: number; height: number } {
  const dimensions: Record<Resolution, { width: number; height: number }> = {
    '720p': { width: 1280, height: 720 },
    '1080p': { width: 1920, height: 1080 },
    '1440p': { width: 2560, height: 1440 },
    '4k': { width: 3840, height: 2160 },
  };
  return dimensions[resolution];
}

/**
 * Calculate video bitrate for resolution
 */
export function calculateVideoBitrate(resolution: Resolution, fps: FrameRate): number {
  // Base bitrate per megapixel
  const baseBitratePerMP = {
    '720p': 8,     // Mbps per megapixel
    '1080p': 8,
    '1440p': 10,
    '4k': 12,
  };

  const { width, height } = getResolutionDimensions(resolution);
  const megapixels = (width * height) / 1000000;
  const fpsMultiplier = fps / 30;

  return Math.round(baseBitratePerMP[resolution] * megapixels * fpsMultiplier * 1000000);
}

/**
 * Common settings constants
 */
export const MAX_IMAGES_PER_PROJECT = 50;
export const MAX_AUDIO_TRACKS_PER_PROJECT = 10;
export const MAX_CONCURRENT_RENDER_JOBS = 3;
export const MIN_IMAGE_DURATION = 1.0;    // seconds
export const MAX_IMAGE_DURATION = 30.0;    // seconds
export const MIN_AUDIO_FADE = 0.0;          // seconds
export const MAX_AUDIO_FADE = 10.0;         // seconds

/**
 * Default encoder selection based on GPU availability
 */
export function getDefaultEncoder(hasGPU: boolean): Encoder {
  return hasGPU ? 'h265_nvenc' : 'libx265';
}

/**
 * Recommended settings for different use cases
 */
export const PRESET_SETTINGS = {
  social: {
    resolution: '1080p' as Resolution,
    fps: 30 as FrameRate,
    output_format: 'mp4_h264' as OutputFormat,
    video_bitrate: 8000000,
    audio_bitrate: 192000,
  },
  high_quality: {
    resolution: '4k' as Resolution,
    fps: 60 as FrameRate,
    output_format: 'mp4_h265' as OutputFormat,
    video_bitrate: 35000000,
    audio_bitrate: 256000,
  },
  quick_preview: {
    resolution: '720p' as Resolution,
    fps: 30 as FrameRate,
    output_format: 'mp4_h264' as OutputFormat,
    video_bitrate: 4000000,
    audio_bitrate: 128000,
  },
} as const;
