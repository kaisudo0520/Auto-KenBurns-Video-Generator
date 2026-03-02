<script setup lang="ts">
import { ref, watch } from 'vue'
import type { RenderSettings, Resolution, FrameRate, OutputFormat } from '@/types'

const props = defineProps<{
  settings: RenderSettings
}>()

const emit = defineEmits<{
  (e: 'update', settings: Partial<RenderSettings>): void
}>()

// Local state for form
const resolution = ref<Resolution>(props.settings.resolution)
const fps = ref<FrameRate>(props.settings.fps)
const outputFormat = ref<OutputFormat>(props.settings.output_format)
const videoBitrate = ref(props.settings.video_bitrate)
const audioBitrate = ref(props.settings.audio_bitrate)

// Ken-Burns settings (auto mode - only zoom range)
const minZoom = ref(props.settings.kenburns.min_zoom)
const maxZoom = ref(props.settings.kenburns.max_zoom)

// Image fade settings
const fadeIn = ref(props.settings.audio_fade.fade_in)
const fadeOut = ref(props.settings.audio_fade.fade_out)

// Resolution options
const resolutionOptions = [
  { value: '720p', label: 'HD (1280x720)' },
  { value: '1080p', label: 'Full HD (1920x1080)' },
  { value: '1440p', label: 'QHD (2560x1440)' },
  { value: '4k', label: '4K (3840x2160)' },
]

// FPS options
const fpsOptions = [
  { value: 24, label: '24 fps (電影)' },
  { value: 30, label: '30 fps (標準)' },
  { value: 60, label: '60 fps (流暢)' },
]

// Output format options
const formatOptions = [
  { value: 'mp4_h264', label: 'MP4 (H.264)', desc: '相容性最佳' },
  { value: 'mp4_h265', label: 'MP4 (H.265/HEVC)', desc: '壓縮率較高' },
]

// Watch for prop changes
watch(() => props.settings, (newSettings) => {
  resolution.value = newSettings.resolution
  fps.value = newSettings.fps
  outputFormat.value = newSettings.output_format
  videoBitrate.value = newSettings.video_bitrate
  audioBitrate.value = newSettings.audio_bitrate
  minZoom.value = newSettings.kenburns.min_zoom
  maxZoom.value = newSettings.kenburns.max_zoom
  fadeIn.value = newSettings.audio_fade.fade_in
  fadeOut.value = newSettings.audio_fade.fade_out
}, { deep: true })

function updateSettings() {
  emit('update', {
    resolution: resolution.value,
    fps: fps.value,
    output_format: outputFormat.value,
    video_bitrate: videoBitrate.value,
    audio_bitrate: audioBitrate.value,
    kenburns: {
      effect_type: 'auto',  // 自動根據BPM調整
      duration: 0,           // 由系統計算
      easing: 'ease_in_out',
      min_zoom: minZoom.value,
      max_zoom: maxZoom.value,
    },
    audio_fade: {
      fade_in: fadeIn.value,
      fade_out: fadeOut.value,
      crossfade: true,  // 預設啟用交叉淡化
    },
  })
}

function formatBitrate(value: number) {
  return (value / 1000000).toFixed(1) + ' Mbps'
}
</script>

<template>
  <div class="space-y-6">
    <h2 class="text-xl font-semibold text-white flex items-center gap-2">
      <svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
      輸出設定
    </h2>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Basic Settings -->
      <div class="space-y-4 bg-slate-800 rounded-xl p-5">
        <h3 class="text-lg font-medium text-white">基本設定</h3>

        <!-- Resolution -->
        <div>
          <label class="block text-sm text-slate-400 mb-2">解析度</label>
          <select v-model="resolution" @change="updateSettings" class="select-field w-full">
            <option v-for="opt in resolutionOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <!-- Frame Rate -->
        <div>
          <label class="block text-sm text-slate-400 mb-2">幀率</label>
          <select v-model="fps" @change="updateSettings" class="select-field w-full">
            <option v-for="opt in fpsOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <!-- Output Format -->
        <div>
          <label class="block text-sm text-slate-400 mb-2">輸出格式</label>
          <select v-model="outputFormat" @change="updateSettings" class="select-field w-full">
            <option v-for="opt in formatOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }} - {{ opt.desc }}
            </option>
          </select>
        </div>

        <!-- Video Bitrate -->
        <div>
          <label class="block text-sm text-slate-400 mb-2">
            影片位元率: {{ formatBitrate(videoBitrate) }}
          </label>
          <input
            type="range"
            v-model.number="videoBitrate"
            @change="updateSettings"
            min="1000000"
            max="50000000"
            step="1000000"
            class="w-full accent-blue-500"
          />
        </div>

        <!-- Audio Bitrate -->
        <div>
          <label class="block text-sm text-slate-400 mb-2">
            音訊位元率: {{ (audioBitrate / 1000).toFixed(0) }} kbps
          </label>
          <input
            type="range"
            v-model.number="audioBitrate"
            @change="updateSettings"
            min="64000"
            max="512000"
            step="64000"
            class="w-full accent-purple-500"
          />
        </div>
      </div>

      <!-- Ken-Burns Auto Mode -->
      <div class="space-y-4 bg-slate-800 rounded-xl p-5">
        <h3 class="text-lg font-medium text-white flex items-center gap-2">
          <svg class="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Ken-Burns 特效
          <span class="text-xs font-normal text-green-400 bg-green-400/10 px-2 py-0.5 rounded">自動模式</span>
        </h3>

        <!-- Auto Mode Description -->
        <div class="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-4 mb-4">
          <p class="text-sm text-cyan-200">
            系統會根據上傳音樂的 <strong>BPM</strong> 自動調整動作切換頻率和速度，
            為每張圖片生成流暢的 Ken-Burns 效果。
          </p>
          <ul class="text-xs text-slate-400 mt-2 space-y-1">
            <li>• 低BPM (&lt;80): 緩慢悠長的動作 (1.5-3秒)</li>
            <li>• 中BPM (80-140): 標準動作 (1-2秒)</li>
            <li>• 高BPM (&gt;140): 快速動態動作 (0.5-1秒)</li>
          </ul>
        </div>

        <!-- Zoom Range -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-slate-400 mb-2">最小縮放</label>
            <input
              type="number"
              v-model.number="minZoom"
              @change="updateSettings"
              min="1"
              max="3"
              step="0.1"
              class="input-field w-full"
            />
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-2">最大縮放</label>
            <input
              type="number"
              v-model.number="maxZoom"
              @change="updateSettings"
              min="1"
              max="3"
              step="0.1"
              class="input-field w-full"
            />
          </div>
        </div>

        <!-- Fade In/Out -->
        <div class="mt-4">
          <label class="block text-sm text-slate-400 mb-2">淡入淡出效果</label>
          <p class="text-xs text-slate-500 mb-3">系統會自動為每張圖片添加淡入淡出效果</p>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs text-slate-500 mb-1">淡入時間</label>
              <input
                type="number"
                v-model.number="fadeIn"
                @change="updateSettings"
                min="0"
                max="3"
                step="0.1"
                class="input-field w-full"
              />
            </div>
            <div>
              <label class="block text-xs text-slate-500 mb-1">淡出時間</label>
              <input
                type="number"
                v-model.number="fadeOut"
                @change="updateSettings"
                min="0"
                max="3"
                step="0.1"
                class="input-field w-full"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
