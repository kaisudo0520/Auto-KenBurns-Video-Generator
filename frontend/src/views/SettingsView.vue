<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { SettingsOptions, SystemStatus } from '@/types'
import api from '@/services/api'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const settingsOptions = ref<SettingsOptions | null>(null)
const systemStatus = ref<SystemStatus | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  await loadSettings()
})

async function loadSettings() {
  loading.value = true
  error.value = null

  try {
    const [optionsRes, statusRes] = await Promise.all([
      api.getSettingsOptions(),
      api.getSystemStatus(),
    ])
    settingsOptions.value = optionsRes.data
    systemStatus.value = statusRes.data
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load settings'
  } finally {
    loading.value = false
  }
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

function getStoragePercentage(used: number, total: number): number {
  return Math.round((used / total) * 100)
}
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <h1 class="text-3xl font-bold font-display text-white mb-8 animate-fade-in-up">系統設定</h1>

    <!-- Loading State -->
    <div v-if="loading" class="py-20">
      <LoadingSpinner size="lg" text="載入設定中..." />
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="py-20 text-center">
      <div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-red-500/10 flex items-center justify-center">
        <svg class="w-10 h-10 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <p class="text-red-400 mb-4">{{ error }}</p>
      <button @click="loadSettings" class="btn-primary">
        重試
      </button>
    </div>

    <!-- Settings Content -->
    <div v-else class="space-y-8">
      <!-- System Status -->
      <div class="glass-card p-6 animate-fade-in-up stagger-1">
        <h2 class="text-xl font-semibold text-white mb-6 flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-cyan/20 to-accent-violet/20 flex items-center justify-center">
            <svg class="w-5 h-5 text-accent-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
            </svg>
          </div>
          系統狀態
        </h2>

        <div v-if="systemStatus" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <!-- GPU Status -->
          <div class="bg-bg-tertiary/50 rounded-xl p-4">
            <div class="flex items-center gap-2 mb-3">
              <div
                class="w-2.5 h-2.5 rounded-full"
                :class="systemStatus.gpu.available ? 'bg-emerald-500' : 'bg-red-500'"
              ></div>
              <span class="text-zinc-400 text-sm">GPU</span>
            </div>
            <p class="text-white font-medium">
              {{ systemStatus.gpu.available ? systemStatus.gpu.name : '不可用' }}
            </p>
            <p v-if="systemStatus.gpu.available" class="text-zinc-500 text-xs mt-2">
              {{ systemStatus.gpu.memory_used }}MB / {{ systemStatus.gpu.memory_total }}MB
            </p>
          </div>

          <!-- Render Queue -->
          <div class="bg-bg-tertiary/50 rounded-xl p-4">
            <div class="flex items-center gap-2 mb-3">
              <div class="w-2.5 h-2.5 rounded-full bg-accent-cyan"></div>
              <span class="text-zinc-400 text-sm">渲染隊列</span>
            </div>
            <p class="text-white font-medium">
              {{ systemStatus.render_queue.running }} 執行中 / {{ systemStatus.render_queue.queued }} 排隊中
            </p>
            <p class="text-zinc-500 text-xs mt-2">
              最多 {{ systemStatus.render_queue.max_concurrent }} 個並行任務
            </p>
          </div>

          <!-- Temp Storage -->
          <div class="bg-bg-tertiary/50 rounded-xl p-4">
            <div class="flex items-center gap-2 mb-3">
              <div class="w-2.5 h-2.5 rounded-full bg-accent-amber"></div>
              <span class="text-zinc-400 text-sm">暫存空間</span>
            </div>
            <p class="text-white font-medium">
              {{ formatBytes(systemStatus.storage.temp_used) }} / {{ formatBytes(systemStatus.storage.temp_total) }}
            </p>
            <div class="mt-3 bg-bg-secondary rounded-full h-2">
              <div
                class="h-full rounded-full bg-gradient-to-r from-accent-amber to-accent-fuchsia transition-all"
                :style="{ width: `${getStoragePercentage(systemStatus.storage.temp_used, systemStatus.storage.temp_total)}%` }"
              ></div>
            </div>
          </div>

          <!-- Version Info -->
          <div class="bg-bg-tertiary/50 rounded-xl p-4">
            <div class="flex items-center gap-2 mb-3">
              <div class="w-2.5 h-2.5 rounded-full bg-accent-violet"></div>
              <span class="text-zinc-400 text-sm">版本</span>
            </div>
            <p class="text-white font-medium">API {{ systemStatus.version.api }}</p>
            <p class="text-zinc-500 text-xs mt-2">
              FFmpeg {{ systemStatus.version.ffmpeg }}
            </p>
          </div>
        </div>
      </div>

      <!-- Available Options -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Resolutions -->
        <div class="glass-card p-6 animate-fade-in-up stagger-2">
          <h3 class="text-lg font-semibold text-white mb-4">可用解析度</h3>
          <div class="space-y-2">
            <div
              v-for="res in settingsOptions?.resolutions"
              :key="res.value"
              class="flex items-center justify-between bg-bg-tertiary/50 rounded-lg p-3"
            >
              <span class="text-white">{{ res.label }}</span>
              <span class="text-zinc-500 text-sm font-mono">{{ res.width }} x {{ res.height }}</span>
            </div>
          </div>
        </div>

        <!-- Frame Rates -->
        <div class="glass-card p-6 animate-fade-in-up stagger-3">
          <h3 class="text-lg font-semibold text-white mb-4">可用幀率</h3>
          <div class="space-y-2">
            <div
              v-for="fps in settingsOptions?.frame_rates"
              :key="fps.value"
              class="flex items-center justify-between bg-bg-tertiary/50 rounded-lg p-3"
            >
              <span class="text-white">{{ fps.label }}</span>
            </div>
          </div>
        </div>

        <!-- Output Formats -->
        <div class="glass-card p-6 animate-fade-in-up stagger-4">
          <h3 class="text-lg font-semibold text-white mb-4">輸出格式</h3>
          <div class="space-y-2">
            <div
              v-for="fmt in settingsOptions?.output_formats"
              :key="fmt.value"
              class="flex items-center justify-between bg-bg-tertiary/50 rounded-lg p-3"
            >
              <span class="text-white">{{ fmt.label }}</span>
              <span class="text-zinc-500 text-sm">{{ fmt.description }}</span>
            </div>
          </div>
        </div>

        <!-- Ken-Burns Effects -->
        <div class="glass-card p-6 animate-fade-in-up stagger-5">
          <h3 class="text-lg font-semibold text-white mb-4">Ken-Burns 特效</h3>
          <div class="grid grid-cols-2 gap-2">
            <div
              v-for="effect in settingsOptions?.kenburns_effects"
              :key="effect.value"
              class="bg-bg-tertiary/50 rounded-lg p-3 text-center"
              :class="effect.default ? 'ring-2 ring-accent-violet/50' : ''"
            >
              <span class="text-white text-sm">{{ effect.label }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
