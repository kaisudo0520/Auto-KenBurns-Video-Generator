<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { VideoPlayer } from '@/components/player'
import { ProgressBar } from '@/components/progress'
import { StatusIndicator } from '@/components/progress'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import api from '@/services/api'

// Job 類型定義
interface RenderJob {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress?: number
  current_stage?: string
  output_file_size?: number
  duration?: number
  resolution?: string
  output_filename?: string
  project_id?: string
  error_message?: string
}

const route = useRoute()
const router = useRouter()

const jobId = computed(() => route.params.jobId as string)
const loading = ref(true)
const error = ref<string | null>(null)
const job = ref<RenderJob | null>(null)
let pollInterval: ReturnType<typeof setInterval> | null = null

const videoUrl = computed(() => {
  if (job.value?.status === 'completed') {
    return `/api/v1/render/download/${jobId.value}`
  }
  return null
})

const fileSize = computed(() => {
  if (job.value?.output_file_size) {
    const bytes = job.value.output_file_size
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }
  return '--'
})

const duration = computed(() => {
  if (job.value?.duration) {
    const mins = Math.floor(job.value.duration / 60)
    const secs = Math.floor(job.value.duration % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }
  return '--:--'
})

const statusVariant = computed(() => {
  switch (job.value?.status) {
    case 'completed': return 'completed'
    case 'processing': return 'processing'
    case 'failed': return 'error'
    case 'pending': return 'pending'
    default: return 'idle'
  }
})

async function fetchJobStatus() {
  try {
    loading.value = true
    const response = await api.getRenderStatus(jobId.value)
    job.value = response.data as RenderJob

    // 如果狀態是 processing 或 pending，繼續輪詢
    if (job.value?.status === 'processing' || job.value?.status === 'pending') {
      startPolling()
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
      job.value = response.data as RenderJob

      // 如果完成或失敗，停止輪詢
      if (job.value?.status === 'completed' || job.value?.status === 'failed') {
        stopPolling()
      }
    } catch (err) {
      console.error('Polling error:', err)
    }
  }, 3000) // 每 3 秒輪詢一次
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

function handleDownload() {
  if (videoUrl.value && job.value) {
    const link = document.createElement('a')
    link.href = videoUrl.value
    link.download = job.value.output_filename || 'video.mp4'
    link.click()
  }
}

function handleBackToProject() {
  if (job.value?.project_id) {
    router.push(`/project/${job.value.project_id}`)
  } else {
    router.push('/')
  }
}

onMounted(() => {
  fetchJobStatus()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Back Button -->
    <button
      @click="handleBackToProject"
      class="flex items-center gap-2 text-zinc-400 hover:text-white mb-6 transition-colors group"
    >
      <svg class="w-5 h-5 group-hover:-translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      返回專案
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

      <!-- Video Player -->
      <div v-if="job?.status === 'completed'" class="animate-fade-in-up stagger-1">
        <VideoPlayer
          :src="videoUrl!"
          :title="job?.output_filename || '輸出影片'"
          autoplay
        />
      </div>

      <!-- Processing State -->
      <div v-else-if="job?.status === 'processing'" class="animate-fade-in-up stagger-1">
        <div class="glass-card p-8 text-center">
          <div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-accent-violet/20 to-accent-cyan/20 flex items-center justify-center">
            <svg class="w-10 h-10 text-accent-cyan animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
          <h2 class="text-xl font-semibold text-white mb-2">正在渲染影片...</h2>
          <p class="text-zinc-400 mb-6">請稍候，這可能需要幾分鐘時間</p>
          <ProgressBar :value="job?.progress || 0" size="lg" />
          <p class="text-zinc-500 text-sm mt-4">
            {{ job?.current_stage || '處理中' }}
          </p>
        </div>
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
          <button @click="handleBackToProject" class="btn-primary">
            返回專案
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
        <button @click="handleDownload" class="flex-1 btn-primary py-4 flex items-center justify-center gap-3">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          下載影片
        </button>
        <button @click="handleBackToProject" class="btn-secondary px-6">
          返回專案
        </button>
      </div>
    </div>
  </div>
</template>
