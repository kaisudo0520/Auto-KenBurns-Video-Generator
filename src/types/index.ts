// ========================================
// Ken-Burns Video Generator - Type Definitions
// Project: click-merge-ken-burn
// Version: 1.0
// ========================================

// Re-export all types
export * from './project';
export * from './upload';
export * from './render';
export * from './settings';
export * from './websocket';
export * from './common';

// ========================================
// Common Types
// ========================================

/**
 * Standard API response wrapper
 */
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

/**
 * Paginated response wrapper
 */
export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: Pagination;
}

/**
 * Pagination metadata
 */
export interface Pagination {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

/**
 * Error response structure
 */
export interface ErrorResponse {
  success: false;
  error: ErrorDetail;
}

/**
 * Error details
 */
export interface ErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  request_id?: string;
}

/**
 * Timestamp helper type
 */
export type Timestamp = string; // ISO 8601 format: "2026-03-01T10:30:00Z"
