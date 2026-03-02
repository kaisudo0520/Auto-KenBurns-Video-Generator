import { ref, onMounted, onUnmounted } from 'vue'
import wsService from '@/services/websocket'
import type { WSConnectionState, WSProgressMessage, WSStatusMessage, WSErrorMessage, WSCompleteMessage } from '@/types'

export function useWebSocket(jobId: ref<string | null>) {
  const connectionState = ref<WSConnectionState>('disconnected')
  const error = ref<string | null>(null)

  const onProgress = ref<((data: WSProgressMessage['data']) => void) | null>(null)
  const onStatus = ref<((data: WSStatusMessage['data']) => void) | null>(null)
  const onError = ref<((data: WSErrorMessage['data']) => void) | null>(null)
  const onComplete = ref<((data: WSCompleteMessage['data']) => void) | null>(null)
  const onConnected = ref<((data: { job_id: string; message: string }) => void) | null>(null)
  const onDisconnected = ref<((reason?: string) => void) | null>(null)

  function connect(id: string) {
    if (!id) return

    wsService.onConnected((data) => {
      connectionState.value = 'connected'
      onConnected.value?.(data)
    })

    wsService.onDisconnected((reason) => {
      connectionState.value = 'disconnected'
      onDisconnected.value?.(reason)
    })

    wsService.onProgress((data) => {
      onProgress.value?.(data)
    })

    wsService.onStatus((data) => {
      onStatus.value?.(data)
    })

    wsService.onError((data) => {
      error.value = data.error
      onError.value?.(data)
    })

    wsService.onComplete((data) => {
      onComplete.value?.(data)
    })

    wsService.connect(id)
    connectionState.value = 'connecting'
  }

  function disconnect() {
    wsService.disconnect()
    connectionState.value = 'disconnected'
  }

  function subscribe(id: string) {
    wsService.subscribe(id)
  }

  function unsubscribe(id: string) {
    wsService.unsubscribe(id)
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    connectionState,
    error,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    onProgress,
    onStatus,
    onError,
    onComplete,
    onConnected,
    onDisconnected,
  }
}
