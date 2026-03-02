import type {
  WSConnectionState,
  WSProgressMessage,
  WSStatusMessage,
  WSErrorMessage,
  WSCompleteMessage,
  WSConnectedMessage,
} from '@/types'
import { createProgressWSUrl, parseWSMessage, createSubscribeMessage, createUnsubscribeMessage } from '@/types'

type ProgressCallback = (data: WSProgressMessage['data']) => void
type StatusCallback = (data: WSStatusMessage['data']) => void
type ErrorCallback = (data: WSErrorMessage['data']) => void
type CompleteCallback = (data: WSCompleteMessage['data']) => void
type ConnectedCallback = (data: WSConnectedMessage['data']) => void
type DisconnectedCallback = (reason?: string) => void

class WebSocketService {
  private ws: WebSocket | null = null
  private currentJobId: string | null = null
  private state: WSConnectionState = 'disconnected'
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectInterval = 3000
  private shouldReconnect = true

  private onProgressCallback?: ProgressCallback
  private onStatusCallback?: StatusCallback
  private onErrorCallback?: ErrorCallback
  private onCompleteCallback?: CompleteCallback
  private onConnectedCallback?: ConnectedCallback
  private onDisconnectedCallback?: DisconnectedCallback

  private baseUrl: string

  constructor() {
    this.baseUrl = import.meta.env.VITE_WS_URL || (import.meta.env.VITE_API_URL?.replace('http', 'ws') || '').replace('/api/v1', '') || 'ws://localhost:8000'
  }

  connect(jobId: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.disconnect()
    }

    this.currentJobId = jobId
    this.shouldReconnect = true
    this.reconnectAttempts = 0

    const url = createProgressWSUrl(this.baseUrl, jobId)
    this.setState('connecting')

    try {
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.setState('connected')
        this.reconnectAttempts = 0
        this.onConnectedCallback?.({ job_id: jobId, message: '已連接到渲染進度服務' })
        this.subscribe(jobId)
      }

      this.ws.onmessage = (event) => {
        const message = parseWSMessage(event.data)
        if (!message) return

        switch (message.type) {
          case 'progress':
            this.onProgressCallback?.(message.data)
            break
          case 'status':
            this.onStatusCallback?.(message.data)
            break
          case 'error':
            this.onErrorCallback?.(message.data)
            break
          case 'complete':
            this.onCompleteCallback?.(message.data)
            this.shouldReconnect = false
            break
          case 'connected':
            this.onConnectedCallback?.(message.data)
            break
          case 'disconnected':
            this.onDisconnectedCallback?.(message.data.reason)
            break
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.setState('error')
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket closed', event.reason)
        this.setState('disconnected')

        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          console.log(`Reconnecting... Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`)
          setTimeout(() => {
            if (this.currentJobId && this.shouldReconnect) {
              this.connect(this.currentJobId)
            }
          }, this.reconnectInterval)
        }

        this.onDisconnectedCallback?.(event.reason)
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      this.setState('error')
    }
  }

  disconnect(): void {
    this.shouldReconnect = false
    if (this.ws) {
      this.setState('disconnecting')
      if (this.currentJobId) {
        this.unsubscribe(this.currentJobId)
      }
      this.ws.close()
      this.ws = null
      this.currentJobId = null
      this.setState('disconnected')
    }
  }

  subscribe(jobId: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(createSubscribeMessage(jobId))
    }
  }

  unsubscribe(jobId: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(createUnsubscribeMessage(jobId))
    }
  }

  getState(): WSConnectionState {
    return this.state
  }

  isConnected(): boolean {
    return this.state === 'connected'
  }

  getCurrentJobId(): string | null {
    return this.currentJobId
  }

  onProgress(callback: ProgressCallback): void {
    this.onProgressCallback = callback
  }

  onStatus(callback: StatusCallback): void {
    this.onStatusCallback = callback
  }

  onError(callback: ErrorCallback): void {
    this.onErrorCallback = callback
  }

  onComplete(callback: CompleteCallback): void {
    this.onCompleteCallback = callback
  }

  onConnected(callback: ConnectedCallback): void {
    this.onConnectedCallback = callback
  }

  onDisconnected(callback: DisconnectedCallback): void {
    this.onDisconnectedCallback = callback
  }

  offProgress(): void {
    this.onProgressCallback = undefined
  }

  offStatus(): void {
    this.onStatusCallback = undefined
  }

  offError(): void {
    this.onErrorCallback = undefined
  }

  offComplete(): void {
    this.onCompleteCallback = undefined
  }

  offConnected(): void {
    this.onConnectedCallback = undefined
  }

  offDisconnected(): void {
    this.onDisconnectedCallback = undefined
  }

  private setState(state: WSConnectionState): void {
    this.state = state
  }
}

export const wsService = new WebSocketService()
export default wsService
