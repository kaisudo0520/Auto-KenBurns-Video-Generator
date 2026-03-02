// ========================================
// Upload Types
// ========================================

import { FileStatus, BoundingBox } from './common';

/**
 * Image file information after upload
 */
export interface ImageFile {
  file_id: string;
  filename: string;
  content_type: string;
  size: number;
  width: number;
  height: number;
  uploaded_at: string;
  status: FileStatus;
}

/**
 * Audio file information after upload
 */
export interface AudioFile {
  file_id: string;
  filename: string;
  content_type: string;
  size: number;
  duration: number;
  sample_rate: number;
  loudness: number;
  uploaded_at: string;
  status: FileStatus;
}

/**
 * Upload result for single file
 */
export interface UploadResult<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
}

/**
 * Batch upload result
 */
export interface BatchUploadResult<T> {
  uploaded: Array<{
    file_id: string;
    filename: string;
    status: 'success';
    data?: T;
  }>;
  failed: Array<{
    filename: string;
    status: 'failed';
    error: string;
  }>;
}

/**
 * Upload progress event
 */
export interface UploadProgress {
  file_id: string;
  filename: string;
  progress: number; // 0-100
  bytes_uploaded: number;
  bytes_total: number;
}

/**
 * File type validation
 */
export interface FileTypeValidation {
  allowed_types: string[];
  max_size: number;
}

/**
 * Image file type validation
 */
export const IMAGE_FILE_TYPES: FileTypeValidation = {
  allowed_types: ['image/jpeg', 'image/png', 'image/webp', 'image/bmp'],
  max_size: 50 * 1024 * 1024, // 50 MB
};

/**
 * Audio file type validation
 */
export const AUDIO_FILE_TYPES: FileTypeValidation = {
  allowed_types: ['audio/mpeg', 'audio/wav', 'audio/aac', 'audio/flac', 'audio/ogg'],
  max_size: 100 * 1024 * 1024, // 100 MB
};

/**
 * Image file extensions
 */
export const IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp'];

/**
 * Audio file extensions
 */
export const AUDIO_EXTENSIONS = ['.mp3', '.wav', '.aac', '.flac', '.ogg'];
