import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { RenderJobStatus, RenderProgress, StartRenderResponse, RenderHistoryItem, JobStatus } from '@/types'
import { RENDER_STAGE_LABELS, JOB_STATUS_LABELS } from '@/types'
import api from '@/services/api'
import wsService from '@/services/websocket'

export const useRenderStore = defineStore('render', () => {
  const currentJob = ref<StartRenderResponse | null>(null)
  const jobStatus = ref<RenderJobStatus | null>(null)
  const renderHistory = ref<RenderHistoryItem[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Polling fallback
  const usePolling = ref(false)
  const pollingInterval = ref<ReturnType<typeof setInterval> | null>(null)
  const pollingJobId = ref<string | null>(null)

  // 啟動輪詢（當 WebSocket 失敗時使用）
  function startPolling(jobId: string) {
    stopPolling()
    pollingJobId.value = jobId
    usePolling.value = true

    // 每 2 秒獲取一次狀態
    pollingInterval.value = setInterval(async () => {
      if (!pollingJobId.value) return

      try {
        const status = await api.getRenderStatus(pollingJobId.value).then(r => r.data)

        // 更新狀態
        if (currentJob.value) {
          currentJob.value.status = status.status
        }
        if (jobStatus.value) {
          jobStatus.value.status = status.status
          jobStatus.value.progress = status.progress
        }

        // 如果完成或失敗，停止輪詢
        if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
          stopPolling()
        }
      } catch (e) {
        console.error('Polling error:', e)
      }
    }, 2000)
  }

  // 停止輪詢
  function stopPolling() {
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value)
      pollingInterval.value = null
    }
    pollingJobId.value = null
    usePolling.value = false
  }

  const isRendering = computed(() => {
    if (!currentJob.value) return false
    const status = currentJob.value.status
    return status === 'queued' || status === 'preparing' || status === 'rendering' || status === 'encoding'
  })

  const progress = computed<RenderProgress | null>(() => jobStatus.value?.progress || null)
  const progressPercentage = computed(() => progress.value?.percentage || 0)
  const currentStage = computed(() => progress.value?.stage || null)
  const currentStageLabel = computed(() => {
    const stage = currentStage.value
    return stage ? RENDER_STAGE_LABELS[stage] : ''
  })
  const etaSeconds = computed(() => progress.value?.eta_seconds || 0)
  const etaFormatted = computed(() => {
    const seconds = etaSeconds.value
    if (seconds <= 0) return '--'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  })

  const jobStatusLabel = computed(() => {
    const status = currentJob.value?.status || jobStatus.value?.status
    return status ? JOB_STATUS_LABELS[status as JobStatus] : ''
  })

  async function startRender(projectId: string) {
    loading.value = true
    error.value = null
    try {
      const response = await api.startRender({ project_id: projectId })
      currentJob.value = response.data
      return response.data
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to start render'
      throw e
    } finally {
      loading.value = false
    }
  }

  // 快速渲染 - 直接上傳圖片和音樂
  async function quickRender(images: File[], audio: File | null, imageDurations: number[] = []) {
    loading.value = true
    error.value = null
    try {
      const response = await api.quickRender(images, audio, imageDurations)
      currentJob.value = {
        job_id: response.job_id,
        project_id: '',
        status: response.status,
        estimated_duration: response.estimated_duration,
        webSocket_url: response.webSocket_url,
      }
      return response
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to start render'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchJobStatus(jobId: string) {
    loading.value = true
    error.value = null
    try {
      const response = await api.getRenderStatus(jobId)
      jobStatus.value = response.data
      return response.data
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch job status'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function cancelRender(jobId: string) {
    loading.value = true
    error.value = null
    try {
      await api.cancelRender(jobId)
      currentJob.value = null
      jobStatus.value = null
      wsService.disconnect()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to cancel render'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchRenderHistory(projectId: string) {
    loading.value = true
    error.value = null
    try {
      const response = await api.getRenderHistory(projectId)
      renderHistory.value = response.data
      return response.data
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch render history'
      throw e
    } finally {
      loading.value = false
    }
  }

  function connectProgressWS(jobId: string) {
    wsService.onProgress((data) => {
      if (jobStatus.value) {
        jobStatus.value.progress = {
          percentage: data.progress,
          current_frame: data.current_frame,
          total_frames: data.total_frames,
          fps: data.fps,
          eta_seconds: data.eta_seconds,
          stage: data.stage,
          stage_progress: {
            current: data.stage_message,
            percentage: data.stage_percentage,
          },
        }
      }
    })

    wsService.onStatus((data) => {
      if (currentJob.value) {
        currentJob.value.status = data.status
      }
      if (jobStatus.value) {
        jobStatus.value.status = data.status
      }
    })

    wsService.onComplete((data) => {
      if (currentJob.value) {
        currentJob.value.status = 'completed'
      }
      if (jobStatus.value) {
        jobStatus.value.status = 'completed'
        jobStatus.value.progress = {
          percentage: 100,
          current_frame: data.duration * 30,
          total_frames: data.duration * 30,
          fps: data.fps,
          eta_seconds: 0,
          stage: 'finalizing',
          stage_progress: {
            current: '完成',
            percentage: 100,
          },
        }
      }
    })

    wsService.onError((data) => {
      error.value = data.error
      if (currentJob.value) {
        currentJob.value.status = 'failed'
      }
      if (jobStatus.value) {
        jobStatus.value.status = 'failed'
      }
    })

    // WebSocket 斷開時，如果正在渲染則切換到輪詢
    wsService.onDisconnected((reason) => {
      console.log('WebSocket disconnected:', reason)
      if (currentJob.value && (currentJob.value.status === 'rendering' || currentJob.value.status === 'encoding' || currentJob.value.status === 'preparing' || currentJob.value.status === 'queued')) {
        console.log('Falling back to polling...')
        startPolling(jobId)
      }
    })

    // 嘗試連接 WebSocket
    wsService.connect(jobId)

    // 5 秒後如果仍未連接，則切換到輪詢
    setTimeout(() => {
      if (wsService.getState() !== 'connected' && currentJob.value && (currentJob.value.status === 'rendering' || currentJob.value.status === 'encoding' || currentJob.value.status === 'preparing' || currentJob.value.status === 'queued')) {
        console.log('WebSocket timeout, falling back to polling...')
        startPolling(jobId)
      }
    }, 5000)
  }

  function disconnectProgressWS() {
    wsService.disconnect()
    wsService.offProgress()
    wsService.offStatus()
    wsService.offComplete()
    wsService.offError()
    wsService.offDisconnected()
    stopPolling()
  }

  function clearRender() {
    currentJob.value = null
    jobStatus.value = null
    error.value = null
    disconnectProgressWS()
  }

  function clearError() {
    error.value = null
  }

  return {
    currentJob,
    jobStatus,
    renderHistory,
    loading,
    error,
    usePolling,
    isRendering,
    progress,
    progressPercentage,
    currentStage,
    currentStageLabel,
    etaSeconds,
    etaFormatted,
    jobStatusLabel,
    startRender,
    quickRender,
    fetchJobStatus,
    cancelRender,
    fetchRenderHistory,
    connectProgressWS,
    disconnectProgressWS,
    startPolling,
    stopPolling,
    clearRender,
    clearError,
  }
})
