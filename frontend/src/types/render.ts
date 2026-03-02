// ========================================
// Render Types
// ========================================

import { JobStatus, RenderStage, Timestamp } from './common';

/**
 * Start render request
 */
export interface StartRenderRequest {
  project_id: string;
}

/**
 * Render job information
 */
export interface RenderJob {
  job_id: string;
  project_id: string;
  status: JobStatus;
  created_at: Timestamp;
  started_at?: Timestamp;
  updated_at?: Timestamp;
  completed_at?: Timestamp;
}

/**
 * Render progress information
 */
export interface RenderProgress {
  percentage: number;
  current_frame: number;
  total_frames: number;
  fps: number;
  eta_seconds: number;
  stage: RenderStage;
  stage_progress: {
    current: string;
    percentage: number;
  };
}

/**
 * Render job with progress
 */
export interface RenderJobStatus extends RenderJob {
  progress: RenderProgress;
}

/**
 * Render start response
 */
export interface StartRenderResponse {
  job_id: string;
  project_id: string;
  status: JobStatus;
  estimated_duration: number;
  webSocket_url: string;
}

/**
 * Cancel render response
 */
export interface CancelRenderResponse {
  job_id: string;
  status: 'cancelled';
}

/**
 * Render history item
 */
export interface RenderHistoryItem {
  job_id: string;
  status: JobStatus;
  progress: number;
  output_path?: string;
  file_size?: number;
  duration?: number;
  error?: string;
  created_at: Timestamp;
  completed_at?: Timestamp;
  failed_at?: Timestamp;
}

/**
 * Download quality options
 */
export type DownloadQuality = 'original' | 'high' | 'medium' | 'low';

/**
 * Download render request params
 */
export interface DownloadRenderParams {
  quality?: DownloadQuality;
}

/**
 * Preview frame request params
 */
export interface PreviewFrameParams {
  frame: number;
}

/**
 * Render queue status
 */
export interface RenderQueueStatus {
  running: number;
  queued: number;
  max_concurrent: number;
}

/**
 * Render stage labels
 */
export const RENDER_STAGE_LABELS: Record<RenderStage, string> = {
  preparing: '準備階段',
  loading_images: '載入圖片',
  detecting_subjects: '偵測主體',
  generating_paths: '生成路徑',
  processing_audio: '處理音訊',
  rendering_frames: '渲染幀',
  encoding_video: '編碼影片',
  finalizing: '完成階段',
};

/**
 * Render stage weights (percentage)
 */
export const RENDER_STAGE_WEIGHTS: Record<RenderStage, number> = {
  preparing: 5,
  loading_images: 10,
  detecting_subjects: 20,
  generating_paths: 10,
  processing_audio: 15,
  rendering_frames: 30,
  encoding_video: 8,
  finalizing: 2,
};

/**
 * Job status labels
 */
export const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  queued: '已排隊',
  preparing: '準備中',
  rendering: '渲染中',
  encoding: '編碼中',
  completed: '已完成',
  failed: '失敗',
  cancelled: '已取消',
  paused: '已暫停',
};

/**
 * Error codes for render failures
 */
export const RENDER_ERROR_CODES = {
  INVALID_PROJECT_STATE: 'INVALID_PROJECT_STATE',
  INVALID_FILE_TYPE: 'INVALID_FILE_TYPE',
  FILE_CORRUPTED: 'FILE_CORRUPTED',
  AUDIO_PROCESSING_FAILED: 'AUDIO_PROCESSING_FAILED',
  GPU_NOT_AVAILABLE: 'GPU_NOT_AVAILABLE',
  RENDER_FAILED: 'RENDER_FAILED',
  OUTPUT_NOT_FOUND: 'OUTPUT_NOT_FOUND',
  JOB_NOT_FOUND: 'JOB_NOT_FOUND',
  JOB_CANCELLED: 'JOB_CANCELLED',
  INVALID_JOB_STATE: 'INVALID_JOB_STATE',
} as const;
