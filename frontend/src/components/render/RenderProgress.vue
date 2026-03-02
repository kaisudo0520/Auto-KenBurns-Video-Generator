<script setup lang="ts">
import { computed } from 'vue'
import type { RenderProgress } from '@/types'
import { RENDER_STAGE_LABELS } from '@/types'

const props = defineProps<{
  progress: RenderProgress | null
  status: string
  eta?: number
  elapsed?: number
}>()

const emit = defineEmits<{
  (e: 'cancel'): void
}>()

const percentage = computed(() => props.progress?.percentage || 0)
const stage = computed(() => props.progress?.stage || 'preparing')
const stageLabel = computed(() => RENDER_STAGE_LABELS[stage.value] || '準備中')
const stageProgress = computed(() => props.progress?.stage_progress?.percentage || 0)
const stageMessage = computed(() => props.progress?.stage_progress?.current || '')
const currentFrame = computed(() => props.progress?.current_frame || 0)
const totalFrames = computed(() => props.progress?.total_frames || 0)
const fps = computed(() => props.progress?.fps || 0)

const formattedEta = computed(() => {
  if (!props.eta || props.eta <= 0) return '--'
  const mins = Math.floor(props.eta / 60)
  const secs = props.eta % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
})

const formattedElapsed = computed(() => {
  if (!props.elapsed || props.elapsed <= 0) return '0:00'
  const mins = Math.floor(props.elapsed / 60)
  const secs = props.elapsed % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
})

const isCompleted = computed(() => props.status === 'completed')
const isFailed = computed(() => props.status === 'failed')
const isProcessing = computed(() => ['queued', 'preparing', 'rendering', 'encoding'].includes(props.status))

const statusColor = computed(() => {
  if (isCompleted.value) return 'text-emerald-400'
  if (isFailed.value) return 'text-red-400'
  return 'text-accent-cyan'
})
</script>

<template>
  <div class="glass-card p-6 space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <!-- Icon -->
        <div
          class="w-12 h-12 rounded-xl flex items-center justify-center"
          :class="{
            'bg-accent-cyan/20': isProcessing,
            'bg-emerald-500/20': isCompleted,
            'bg-red-500/20': isFailed,
          }"
        >
          <svg
            v-if="isProcessing"
            class="w-6 h-6 text-accent-cyan animate-spin"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <svg
            v-else-if="isCompleted"
            class="w-6 h-6 text-emerald-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          <svg
            v-else-if="isFailed"
            class="w-6 h-6 text-red-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>

        <div>
          <h3 class="text-white font-semibold">{{ stageLabel }}</h3>
          <p v-if="stageMessage" class="text-zinc-400 text-sm">{{ stageMessage }}</p>
        </div>
      </div>

      <div class="text-right">
        <p class="text-3xl font-bold" :class="statusColor">{{ percentage.toFixed(1) }}%</p>
        <p v-if="isProcessing" class="text-zinc-500 text-sm">預估剩餘: {{ formattedEta }}</p>
      </div>
    </div>

    <!-- Progress Bar -->
    <div class="relative">
      <div class="w-full h-3 bg-zinc-800 rounded-full overflow-hidden">
        <div
          class="h-full rounded-full progress-gradient transition-all duration-500 ease-out"
          :style="{ width: `${percentage}%` }"
        ></div>
      </div>
      <!-- Glow effect -->
      <div
        v-if="isProcessing"
        class="absolute top-1/2 left-0 h-1 -translate-y-1/2 rounded-full transition-all duration-500"
        :style="{
          width: `${percentage}%`,
          boxShadow: '0 0 20px rgba(6, 182, 212, 0.8), 0 0 40px rgba(139, 92, 246, 0.4)'
        }"
      ></div>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-4 gap-3">
      <div class="bg-bg-tertiary/50 rounded-lg py-3 text-center">
        <p class="text-zinc-500 text-xs mb-1">已耗時</p>
        <p class="text-white font-medium font-mono text-sm">{{ formattedElapsed }}</p>
      </div>
      <div class="bg-bg-tertiary/50 rounded-lg py-3 text-center">
        <p class="text-zinc-500 text-xs mb-1">幀數</p>
        <p class="text-white font-medium font-mono text-sm">{{ currentFrame.toLocaleString() }} <span class="text-zinc-600">/</span> {{ totalFrames.toLocaleString() }}</p>
      </div>
      <div class="bg-bg-tertiary/50 rounded-lg py-3 text-center">
        <p class="text-zinc-500 text-xs mb-1">速度</p>
        <p class="text-white font-medium font-mono text-sm">{{ fps.toFixed(1) }} <span class="text-zinc-600">fps</span></p>
      </div>
      <div class="bg-bg-tertiary/50 rounded-lg py-3 text-center">
        <p class="text-zinc-500 text-xs mb-1">階段進度</p>
        <p class="text-white font-medium font-mono text-sm">{{ stageProgress }}<span class="text-zinc-600">%</span></p>
      </div>
    </div>

    <!-- Actions -->
    <div v-if="isProcessing" class="flex justify-center pt-2">
      <button
        @click="emit('cancel')"
        class="btn-secondary text-red-400 hover:text-white hover:bg-red-500/20"
      >
        取消渲染
      </button>
    </div>

    <!-- Completion Message -->
    <div v-if="isCompleted" class="text-center pt-2">
      <div class="inline-flex items-center gap-2 text-emerald-400">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="font-medium">渲染完成！</span>
      </div>
    </div>

    <!-- Error Message -->
    <div v-if="isFailed" class="text-center pt-2">
      <div class="inline-flex items-center gap-2 text-red-400">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="font-medium">渲染失敗，請重試或檢查設定</span>
      </div>
    </div>
  </div>
</template>
