// ========================================
// Project Types
// ========================================

import {
  ProjectStatus,
  Resolution,
  FrameRate,
  OutputFormat,
  KenBurnsEffect,
  EasingFunction,
  SubjectRegion,
  Timestamp,
  SortOrder,
} from './common';

/**
 * Ken-Burns effect settings
 */
export interface KenBurnsSettings {
  effect_type: KenBurnsEffect;
  duration: number;           // seconds per image
  easing: EasingFunction;
  min_zoom: number;
  max_zoom: number;
}

/**
 * Audio fade settings
 */
export interface AudioFadeSettings {
  fade_in: number;     // seconds
  fade_out: number;     // seconds
  crossfade: boolean;
}

/**
 * Render settings for a project
 */
export interface RenderSettings {
  resolution: Resolution;
  fps: FrameRate;
  output_format: OutputFormat;
  video_bitrate: number;
  audio_bitrate: number;
  kenburns: KenBurnsSettings;
  audio_fade: AudioFadeSettings;
}

/**
 * Default render settings
 */
export const DEFAULT_RENDER_SETTINGS: RenderSettings = {
  resolution: '1080p',
  fps: 30,
  output_format: 'mp4_h264',
  video_bitrate: 8000000,
  audio_bitrate: 192000,
  kenburns: {
    effect_type: 'compose_pan_zoom',
    duration: 5.0,
    easing: 'ease_in_out',
    min_zoom: 1.0,
    max_zoom: 1.5,
  },
  audio_fade: {
    fade_in: 2.0,
    fade_out: 2.0,
    crossfade: true,
  },
};

/**
 * Image asset in a project
 */
export interface ImageAsset {
  id: string;
  file_id: string;
  filename: string;
  width: number;
  height: number;
  duration: number;     // seconds to display
  order: number;
  subject_regions?: SubjectRegion[];
}

/**
 * Audio asset in a project
 */
export interface AudioAsset {
  id: string;
  file_id: string;
  filename: string;
  duration: number;
  order: number;
}

/**
 * Latest render summary
 */
export interface LatestRender {
  job_id: string;
  status: string;
  output_path?: string;
  created_at: Timestamp;
}

/**
 * Full project data
 */
export interface Project {
  id: string;
  name: string;
  description: string;
  created_at: Timestamp;
  updated_at: Timestamp;
  status: ProjectStatus;
  images: ImageAsset[];
  audio: AudioAsset[];
  settings: RenderSettings;
  latest_render?: LatestRender;
}

/**
 * Project list item (summary)
 */
export interface ProjectListItem {
  id: string;
  name: string;
  description: string;
  created_at: Timestamp;
  updated_at: Timestamp;
  status: ProjectStatus;
  images_count: number;
  audio_count: number;
  thumbnail?: string;
}

/**
 * Create project request
 */
export interface CreateProjectRequest {
  name: string;
  description?: string;
  settings?: Partial<RenderSettings>;
}

/**
 * Update project request
 */
export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  settings?: Partial<RenderSettings>;
  images?: Array<{
    id: string;
    duration?: number;
    order?: number;
  }>;
}

/**
 * Add images to project request
 */
export interface AddImagesRequest {
  file_ids: string[];
  order?: number;
  duration?: number;
}

/**
 * Add audio to project request
 */
export interface AddAudioRequest {
  file_ids: string[];
  order?: number;
}

/**
 * Project list query parameters
 */
export interface ProjectListParams {
  page?: number;
  page_size?: number;
  status?: ProjectStatus;
  sort_by?: 'created_at' | 'updated_at' | 'name';
  sort_order?: SortOrder;
}

/**
 * Project validation result
 */
export interface ProjectValidation {
  valid: boolean;
  errors: Array<{
    field: string;
    message: string;
  }>;
  warnings?: Array<{
    field: string;
    message: string;
  }>;
}
