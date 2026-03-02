<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { StatusIndicator } from '@/components/progress'
import RenderProgressCard from '@/components/render/RenderProgress.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { useRenderStore } from '@/stores/renderStore'
import api from '@/services/api'

interface RenderJob {
  id: string
  status: 'queued' | 'preparing' | 'rendering' | 'encoding' | 'completed' | 'failed' | 'cancelled' | 'paused'
  progress?: number
  current_stage?: string
  output_size?: number
  output_duration?: number
  resolution?: string
  output_path?: string
  project_id?: string
  error_message?: string
}

const route = useRoute()
const router = useRouter()
const renderStore = useRenderStore()

const jobId = computed(() => route.params.jobId as string)
const loading = ref(true)
const error = ref<string | null>(null)
const job = ref<RenderJob | null>(null)
let pollInterval: ReturnType<typeof setInterval> | null = null

// 計時器
const elapsedSeconds = ref(0)
let timerInterval: ReturnType<typeof setInterval> | null = null
const cancelling = ref(false)

const fileSize = computed(() => {
  if (job.value?.output_size) {
    const bytes = job.value.output_size
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }
  return '--'
})

const duration = computed(() => {
  if (job.value?.output_duration) {
    const mins = Math.floor(job.value.output_duration / 60)
    const secs = Math.floor(job.value.output_duration % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }
  return '--:--'
})

const isProcessing = computed(() => {
  const s = job.value?.status
  return s === 'queued' || s === 'preparing' || s === 'rendering' || s === 'encoding'
})

const statusVariant = computed(() => {
  switch (job.value?.status) {
    case 'completed': return 'completed'
    case 'queued':
    case 'preparing':
    case 'rendering':
    case 'encoding': return 'processing'
    case 'failed': return 'error'
    case 'cancelled': return 'idle'
    case 'paused': return 'pending'
    default: return 'idle'
  }
})

// 合併進度資料（優先使用 renderStore 的 WebSocket 即時資料）
const mergedProgress = computed(() => {
  if (renderStore.progress) return renderStore.progress
  if (job.value?.progress != null) {
    return {
      percentage: job.value.progress,
      current_frame: 0,
      total_frames: 0,
      fps: 0,
      eta_seconds: 0,
      stage: (job.value.current_stage || 'preparing') as any,
      stage_progress: { current: '', percentage: 0 },
    }
  }
  return null
})

const mergedEta = computed(() => renderStore.etaSeconds || 0)

// 計時器控制
function startTimer() {
  if (timerInterval) return
  timerInterval = setInterval(() => { elapsedSeconds.value++ }, 1000)
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

// 取消渲染
async function handleCancel() {
  cancelling.value = true
  try {
    await api.cancelRender(jobId.value)
    stopPolling()
    stopTimer()
    renderStore.disconnectProgressWS()
    if (job.value) job.value.status = 'cancelled'
  } catch (err: any) {
    console.error('Cancel error:', err)
  } finally {
    cancelling.value = false
  }
}

async function fetchJobStatus() {
  try {
    loading.value = true
    const response = await api.getRenderStatus(jobId.value)
    job.value = response as any as RenderJob

    if (isProcessing.value) {
      startPolling()
      startTimer()
      // 初始化 renderStore 的 jobStatus 以便 WebSocket 進度更新能寫入
      try { await renderStore.fetchJobStatus(jobId.value) } catch {}
      // 若尚未建立 WebSocket 連線（例如重新整理頁面），則建立連線
      if (!renderStore.currentJob) {
        renderStore.connectProgressWS(jobId.value)
      }
    }
  } catch (err: any) {
    error.value = err.message || '無法取得渲染狀態'
  } finally {
    loading.value = false
  }
}

function startPolling() {
  if (pollInterval) return

  pollInterval = setInterval(async () => {
    try {
      const response = await api.getRenderStatus(jobId.value)
      job.value = response as any as RenderJob

      if (job.value?.status === 'completed' || job.value?.status === 'failed' || job.value?.status === 'cancelled') {
        stopPolling()
      }
    } catch (err) {
      console.error('Polling error:', err)
    }
  }, 3000)
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

async function handleOpenFolder() {
  try {
    await api.openOutputFolder(jobId.value)
  } catch (err: any) {
    console.error('Open folder error:', err)
    error.value = '無法開啟資料夾'
  }
}

function handleBackToHome() {
  router.push('/')
}

// 監聽處理狀態變化以控制計時器
watch(isProcessing, (val) => {
  if (val) {
    startTimer()
  } else {
    stopTimer()
  }
})

onMounted(() => {
  fetchJobStatus()
})

onUnmounted(() => {
  stopPolling()
  stopTimer()
  renderStore.disconnectProgressWS()
})
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Back Button -->
    <button
      @click="handleBackToHome"
      class="flex items-center gap-2 text-zinc-400 hover:text-white mb-6 transition-colors group"
    >
      <svg class="w-5 h-5 group-hover:-translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      返回首頁
    </button>

    <!-- Loading State -->
    <div v-if="loading" class="py-20">
      <LoadingSpinner size="lg" text="載入渲染結果中..." />
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="py-20 text-center">
      <div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-red-500/10 flex items-center justify-center">
        <svg class="w-10 h-10 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
      <p class="text-red-400 text-lg mb-4">{{ error }}</p>
      <button @click="fetchJobStatus" class="btn-primary">
        重試
      </button>
    </div>

    <!-- Result Content -->
    <div v-else class="space-y-6">
      <!-- Header -->
      <div class="flex items-start justify-between animate-fade-in-up">
        <div>
          <h1 class="text-3xl font-bold font-display text-white mb-2">渲染結果</h1>
          <div class="flex items-center gap-3">
            <StatusIndicator :status="statusVariant" :show-label="true" />
          </div>
        </div>
        <div class="text-right">
          <p class="text-sm text-zinc-500">Job ID</p>
          <p class="text-zinc-400 font-mono text-sm">{{ jobId.slice(0, 8) }}...</p>
        </div>
      </div>

      <!-- Completed: 輸出檔案資訊 -->
      <div v-if="job?.status === 'completed'" class="animate-fade-in-up stagger-1">
        <div class="glass-card p-8 text-center">
          <div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-emerald-500/10 flex items-center justify-center">
            <svg class="w-10 h-10 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 class="text-xl font-semibold text-white mb-4">渲染完成</h2>
          <!-- 檔案路徑 -->
          <div v-if="job?.output_path" class="mb-6">
            <p class="text-zinc-500 text-sm mb-2">輸出路徑</p>
            <div class="bg-zinc-800/50 rounded-lg px-4 py-3 border border-zinc-700/50">
              <p class="text-zinc-300 font-mono text-sm break-all select-all">{{ job.output_path }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Processing State - 使用 RenderProgress 元件 -->
      <div v-else-if="isProcessing" class="animate-fade-in-up stagger-1">
        <RenderProgressCard
          :progress="mergedProgress"
          :status="job?.status || 'preparing'"
          :eta="mergedEta"
          :elapsed="elapsedSeconds"
          @cancel="handleCancel"
        />
      </div>

      <!-- Failed State -->
      <div v-else-if="job?.status === 'failed'" class="animate-fade-in-up stagger-1">
        <div class="glass-card p-8 text-center">
          <div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-red-500/10 flex items-center justify-center">
            <svg class="w-10 h-10 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 class="text-xl font-semibold text-white mb-2">渲染失敗</h2>
          <p class="text-zinc-400 mb-6">{{ job?.error_message || '發生未知錯誤' }}</p>
          <button @click="handleBackToHome" class="btn-primary">
            返回首頁
          </button>
        </div>
      </div>

      <!-- Cancelled State -->
      <div v-else-if="job?.status === 'cancelled'" class="animate-fade-in-up stagger-1">
        <div class="glass-card p-8 text-center">
          <div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-amber-500/10 flex items-center justify-center">
            <svg class="w-10 h-10 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
          </div>
          <h2 class="text-xl font-semibold text-white mb-2">渲染已取消</h2>
          <p class="text-zinc-400 mb-6">
            已耗時 {{ Math.floor(elapsedSeconds / 60) }}:{{ (elapsedSeconds % 60).toString().padStart(2, '0') }}
          </p>
          <button @click="handleBackToHome" class="btn-primary">
            返回首頁
          </button>
        </div>
      </div>

      <!-- Stats -->
      <div v-if="job?.status === 'completed'" class="grid grid-cols-3 gap-4 animate-fade-in-up stagger-2">
        <div class="glass-card p-4 text-center">
          <p class="text-zinc-500 text-sm">檔案大小</p>
          <p class="text-2xl font-bold text-white">{{ fileSize }}</p>
        </div>
        <div class="glass-card p-4 text-center">
          <p class="text-zinc-500 text-sm">時長</p>
          <p class="text-2xl font-bold text-white">{{ duration }}</p>
        </div>
        <div class="glass-card p-4 text-center">
          <p class="text-zinc-500 text-sm">解析度</p>
          <p class="text-2xl font-bold text-white">{{ job?.resolution || '1080p' }}</p>
        </div>
      </div>

      <!-- Actions -->
      <div v-if="job?.status === 'completed'" class="flex gap-4 animate-fade-in-up stagger-3">
        <button @click="handleOpenFolder" class="flex-1 btn-primary py-4 flex items-center justify-center gap-3">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
          </svg>
          開啟輸出資料夾
        </button>
        <button @click="handleBackToHome" class="btn-secondary px-6">
          返回首頁
        </button>
      </div>
    </div>
  </div>
</template>
