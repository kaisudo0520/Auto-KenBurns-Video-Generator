<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useRenderStore } from '@/stores/renderStore'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ImageUploader from '@/components/upload/ImageUploader.vue'
import AudioUploader from '@/components/upload/AudioUploader.vue'

const router = useRouter()
const renderStore = useRenderStore()

const images = ref<File[]>([])
const audios = ref<File[]>([])
const imagePreviews = ref<string[]>([])
const isRendering = ref(false)
const renderError = ref<string | null>(null)

// 格式化檔案大小
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function handleImagesSelected(files: File[]) {
  images.value = [...images.value, ...files]

  // 生成預覽
  files.forEach(file => {
    const reader = new FileReader()
    reader.onload = (e) => {
      imagePreviews.value.push(e.target?.result as string)
    }
    reader.readAsDataURL(file)
  })
}

function handleImageRemove(index: number) {
  images.value.splice(index, 1)
  imagePreviews.value.splice(index, 1)
}

function handleAudiosSelected(files: File[]) {
  audios.value = [...audios.value, ...files]
}

function handleAudioRemove(index: number) {
  audios.value.splice(index, 1)
}

async function startRender() {
  if (images.value.length === 0) {
    renderError.value = '請上傳至少一張圖片'
    return
  }

  isRendering.value = true
  renderError.value = null

  // 清除前次渲染狀態
  renderStore.clearRender()

  try {
    const result = await renderStore.quickRender(images.value, audios.value)

    // 連接 WebSocket
    renderStore.connectProgressWS(result.job_id)

    // 跳轉到結果頁面
    router.push(`/result/${result.job_id}`)
  } catch (error: any) {
    console.error('Render error:', error)
    const errMsg = error?.response?.data?.detail || error?.message || '渲染失敗，請稍後再試'
    renderError.value = Array.isArray(errMsg) ? errMsg[0]?.msg || JSON.stringify(errMsg) : errMsg
    isRendering.value = false
  }
}

function clearAll() {
  images.value = []
  imagePreviews.value = []
  audios.value = []
  renderError.value = null
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Hero Section -->
    <div class="text-center mb-8 animate-fade-in-up">
      <h1 class="text-4xl md:text-5xl font-bold font-display mb-4">
        <span class="text-white">自動生成 </span>
        <span class="gradient-text">Ken-Burns</span>
        <span class="text-white"> 影片</span>
      </h1>
      <p class="text-zinc-400 text-lg max-w-2xl mx-auto">
        將您的圖片轉換為帶有流暢平移與縮放特效的專業影片
      </p>
    </div>

    <!-- 上傳區域 -->
    <div class="glass-card p-6 md:p-8 animate-fade-in-up stagger-2">
      <!-- 圖片上傳 -->
      <div class="mb-8">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-1 h-6 rounded-full bg-gradient-to-b from-accent-cyan to-accent-violet"></div>
          <h2 class="text-xl font-bold font-display text-white">圖片</h2>
          <span class="text-zinc-500 text-sm">({{ images.length }} 張)</span>
        </div>

        <!-- 已選擇的圖片 -->
        <div v-if="imagePreviews.length > 0" class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3 mb-4">
          <div
            v-for="(preview, index) in imagePreviews"
            :key="index"
            class="relative aspect-square rounded-lg overflow-hidden group"
          >
            <img
              :src="preview"
              :alt="`圖片 ${index + 1}`"
              class="w-full h-full object-cover"
            />
            <button
              @click="handleImageRemove(index)"
              class="absolute top-1 right-1 w-6 h-6 rounded-full bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 上傳按鈕 -->
        <ImageUploader @upload="handleImagesSelected" />
      </div>

      <!-- 分割線 -->
      <div class="border-t border-zinc-700/50 my-8"></div>

      <!-- 音樂上傳 -->
      <div class="mb-8">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-1 h-6 rounded-full bg-gradient-to-b from-accent-fuchsia to-accent-cyan"></div>
          <h2 class="text-xl font-bold font-display text-white">音樂（可選）</h2>
          <span v-if="audios.length > 0" class="text-zinc-500 text-sm">({{ audios.length }} 首)</span>
        </div>

        <!-- 已選擇的音樂列表 -->
        <div v-if="audios.length > 0" class="space-y-2 mb-4">
          <div
            v-for="(audioFile, index) in audios"
            :key="index"
            class="flex items-center justify-between p-4 rounded-lg bg-bg-secondary border border-zinc-700/50"
          >
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-10 h-10 shrink-0 rounded-lg bg-accent-fuchsia/20 flex items-center justify-center">
                <svg class="w-5 h-5 text-accent-fuchsia" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                </svg>
              </div>
              <div class="min-w-0">
                <p class="text-white truncate">{{ audioFile.name }}</p>
                <p class="text-zinc-500 text-xs">{{ formatFileSize(audioFile.size) }}</p>
              </div>
            </div>
            <button @click="handleAudioRemove(index)" class="shrink-0 ml-3 text-zinc-400 hover:text-white transition-colors">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 上傳按鈕（始終顯示，可累積添加） -->
        <AudioUploader @upload="handleAudiosSelected" />
      </div>

      <!-- 錯誤訊息 -->
      <div v-if="renderError" class="mb-4 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
        {{ renderError }}
      </div>

      <!-- 操作按鈕 -->
      <div class="flex gap-4">
        <button
          @click="clearAll"
          class="btn-secondary flex-1"
          :disabled="isRendering || (images.length === 0 && audios.length === 0)"
        >
          清除全部
        </button>
        <button
          @click="startRender"
          class="btn-primary flex-1 flex items-center justify-center gap-2"
          :disabled="isRendering || images.length === 0"
        >
          <LoadingSpinner v-if="isRendering" size="sm" />
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{{ isRendering ? '處理中...' : '開始渲染' }}</span>
        </button>
      </div>

      <!-- 提示文字 -->
      <p class="text-zinc-500 text-sm text-center mt-4">
        <template v-if="audios.length > 0">
          圖片將根據音樂時長自動分配顯示時間
        </template>
        <template v-else-if="images.length > 0">
          每張圖片預設顯示 5 秒
        </template>
        <template v-else>
          上傳圖片開始建立您的 Ken-Burns 影片
        </template>
      </p>
    </div>

    <!-- 支援格式說明 -->
    <div class="mt-6 text-center text-zinc-500 text-sm">
      <p>支援格式：JPG, PNG, WebP（圖片）| MP3, WAV, OGG（音樂）</p>
    </div>
  </div>
</template>
