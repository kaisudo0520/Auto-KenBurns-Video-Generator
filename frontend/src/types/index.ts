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

// Pagination, ErrorResponse, ErrorDetail, Timestamp 已透過 export * from './common' 匯出
// 避免重複定義
