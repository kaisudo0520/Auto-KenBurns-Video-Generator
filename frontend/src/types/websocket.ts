// ========================================
// WebSocket Types
// ========================================

import { JobStatus, RenderStage, Timestamp } from './common';

/**
 * WebSocket message types
 */
export type WSMessageType =
  | 'connected'
  | 'disconnected'
  | 'subscribe'
  | 'unsubscribe'
  | 'progress'
  | 'status'
  | 'error'
  | 'complete';

/**
 * Base WebSocket message
 */
export interface WSMessage<T = unknown> {
  type: WSMessageType;
  data: T;
  timestamp: Timestamp;
}

/**
 * Client to server: Subscribe to job progress
 */
export interface WSSubscribeMessage {
  type: 'subscribe';
  job_id: string;
}

/**
 * Client to server: Unsubscribe from job progress
 */
export interface WSUnsubscribeMessage {
  type: 'unsubscribe';
  job_id: string;
}

/**
 * Server to client: Connection established
 */
export interface WSConnectedMessage {
  type: 'connected';
  data: {
    job_id: string;
    message: string;
  };
}

/**
 * Server to client: Disconnected
 */
export interface WSDisconnectedMessage {
  type: 'disconnected';
  data: {
    job_id: string;
    reason?: string;
  };
}

/**
 * Server to client: Progress update
 */
export interface WSProgressMessage {
  type: 'progress';
  data: {
    job_id: string;
    progress: number;
    current_frame: number;
    total_frames: number;
    fps: number;
    eta_seconds: number;
    stage: RenderStage;
    stage_label: string;
    stage_percentage: number;
    stage_message: string;
  };
}

/**
 * Server to client: Status update
 */
export interface WSStatusMessage {
  type: 'status';
  data: {
    job_id: string;
    status: JobStatus;
    message: string;
    timestamp: Timestamp;
  };
}

/**
 * Server to client: Error
 */
export interface WSErrorMessage {
  type: 'error';
  data: {
    job_id: string;
    error: string;
    code: string;
    timestamp: Timestamp;
  };
}

/**
 * Server to client: Render complete
 */
export interface WSCompleteMessage {
  type: 'complete';
  data: {
    job_id: string;
    status: 'completed';
    output_path: string;
    file_size: number;
    duration: number;
    resolution: string;
    fps: number;
    timestamp: Timestamp;
  };
}

/**
 * All possible server messages
 */
export type WSServerMessage =
  | WSConnectedMessage
  | WSDisconnectedMessage
  | WSProgressMessage
  | WSStatusMessage
  | WSErrorMessage
  | WSCompleteMessage;

/**
 * All possible client messages
 */
export type WSClientMessage = WSSubscribeMessage | WSUnsubscribeMessage;

/**
 * WebSocket connection options
 */
export interface WSConnectionOptions {
  url: string;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onConnected?: () => void;
  onDisconnected?: (reason?: string) => void;
  onError?: (error: Error) => void;
  onProgress?: (progress: WSProgressMessage['data']) => void;
  onStatus?: (status: WSStatusMessage['data']) => void;
  onErrorMsg?: (error: WSErrorMessage['data']) => void;
  onComplete?: (complete: WSCompleteMessage['data']) => void;
}

/**
 * WebSocket connection state
 */
export type WSConnectionState = 'connecting' | 'connected' | 'disconnecting' | 'disconnected' | 'error';

/**
 * WebSocket manager interface
 */
export interface WebSocketManager {
  connect(jobId: string): void;
  disconnect(): void;
  subscribe(jobId: string): void;
  unsubscribe(jobId: string): void;
  getState(): WSConnectionState;
  isConnected(): boolean;
  on(event: string, callback: (...args: unknown[]) => void): void;
  off(event: string, callback: (...args: unknown[]) => void): void;
}

/**
 * WebSocket event names
 */
export const WS_EVENTS = {
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  PROGRESS: 'progress',
  STATUS: 'status',
  ERROR: 'error',
  COMPLETE: 'complete',
  SUBSCRIBED: 'subscribed',
  UNSUBSCRIBED: 'unsubscribed',
} as const;

/**
 * Default WebSocket configuration
 */
export const DEFAULT_WS_CONFIG: Partial<WSConnectionOptions> = {
  reconnect: true,
  reconnectInterval: 3000,
  maxReconnectAttempts: 5,
};

/**
 * Create WebSocket URL for job progress
 */
export function createProgressWSUrl(baseUrl: string, jobId: string, token?: string): string {
  const url = new URL(`${baseUrl}/ws/render/${jobId}`);
  if (token) {
    url.searchParams.set('token', token);
  }
  return url.toString();
}

/**
 * Parse WebSocket message
 */
export function parseWSMessage(data: string): WSServerMessage | null {
  try {
    const parsed: unknown = JSON.parse(data);
    if (typeof parsed !== 'object' || parsed === null) return null;
    const msg = parsed as Record<string, unknown>;
    if (typeof msg.type !== 'string' || msg.data === undefined) {
      console.warn('Invalid WebSocket message structure:', data);
      return null;
    }
    return parsed as WSServerMessage;
  } catch {
    console.error('Failed to parse WebSocket message:', data);
    return null;
  }
}

/**
 * Create subscribe message
 */
export function createSubscribeMessage(jobId: string): string {
  return JSON.stringify({
    type: 'subscribe',
    job_id: jobId,
  });
}

/**
 * Create unsubscribe message
 */
export function createUnsubscribeMessage(jobId: string): string {
  return JSON.stringify({
    type: 'unsubscribe',
    job_id: jobId,
  });
}
