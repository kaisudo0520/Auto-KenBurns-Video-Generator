<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useRenderStore } from '@/stores/renderStore'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ImageUploader from '@/components/upload/ImageUploader.vue'
import AudioUploader from '@/components/upload/AudioUploader.vue'

const router = useRouter()
const renderStore = useRenderStore()

// === 資料模型（帶唯一 ID，支援拖曳 key 追蹤）===
interface ImageItem {
  id: string
  file: File
  preview: string
}

interface AudioItem {
  id: string
  file: File
}

let nextId = 0
function genId(): string {
  return `item_${++nextId}`
}

const imageItems = ref<ImageItem[]>([])
const audioItems = ref<AudioItem[]>([])
const isRendering = ref(false)
const renderError = ref<string | null>(null)

// 提取 File 陣列供渲染使用
const imageFiles = computed(() => imageItems.value.map(i => i.file))
const audioFiles = computed(() => audioItems.value.map(i => i.file))

// 格式化檔案大小
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// === 檔案操作 ===
function handleImagesSelected(files: File[]) {
  files.forEach(file => {
    const id = genId()
    const preview = URL.createObjectURL(file)
    imageItems.value.push({ id, file, preview })
  })
}

function handleImageRemove(index: number) {
  const item = imageItems.value[index]
  if (item?.preview) URL.revokeObjectURL(item.preview)
  imageItems.value.splice(index, 1)
}

function handleAudiosSelected(files: File[]) {
  files.forEach(file => {
    audioItems.value.push({ id: genId(), file })
  })
}

function handleAudioRemove(index: number) {
  audioItems.value.splice(index, 1)
}

// === 拖曳重排序 ===
const dragState = ref<{
  type: 'image' | 'audio'
  fromIndex: number
} | null>(null)
const dropTargetIndex = ref(-1)

function onDragStart(type: 'image' | 'audio', index: number, event: DragEvent) {
  dragState.value = { type, fromIndex: index }
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', '') // Firefox 需要
  }
}

function onDragOver(type: 'image' | 'audio', index: number, event: DragEvent) {
  if (!dragState.value || dragState.value.type !== type) return
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
  dropTargetIndex.value = index
}

function onDrop(type: 'image' | 'audio', toIndex: number, event: DragEvent) {
  event.preventDefault()
  if (!dragState.value || dragState.value.type !== type) return

  const fromIndex = dragState.value.fromIndex
  if (fromIndex !== toIndex) {
    const arr = type === 'image' ? imageItems.value : audioItems.value
    const [item] = arr.splice(fromIndex, 1)
    arr.splice(toIndex, 0, item)
  }

  dragState.value = null
  dropTargetIndex.value = -1
}

function onDragEnd() {
  dragState.value = null
  dropTargetIndex.value = -1
}

// 是否正在拖曳重排序（用於禁用上傳區域的拖曳反應）
const isDragging = computed(() => dragState.value !== null)

// === 渲染 ===
async function startRender() {
  if (imageItems.value.length === 0) {
    renderError.value = '請上傳至少一張圖片'
    return
  }

  isRendering.value = true
  renderError.value = null
  renderStore.clearRender()

  try {
    const result = await renderStore.quickRender(imageFiles.value, audioFiles.value)
    renderStore.connectProgressWS(result.job_id)
    router.push(`/result/${result.job_id}`)
  } catch (error: any) {
    console.error('Render error:', error)
    const errMsg = error?.response?.data?.detail || error?.message || '渲染失敗，請稍後再試'
    renderError.value = Array.isArray(errMsg) ? errMsg[0]?.msg || JSON.stringify(errMsg) : errMsg
  } finally {
    isRendering.value = false
  }
}

function clearAll() {
  imageItems.value.forEach(item => {
    if (item.preview) URL.revokeObjectURL(item.preview)
  })
  imageItems.value = []
  audioItems.value = []
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
          <span class="text-zinc-500 text-sm">({{ imageItems.length }} 張)</span>
        </div>

        <!-- 已選擇的圖片（可拖曳重排序）-->
        <div v-if="imageItems.length > 0" class="mb-4">
          <div class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
            <div
              v-for="(item, index) in imageItems"
              :key="item.id"
              draggable="true"
              @dragstart="onDragStart('image', index, $event)"
              @dragover="onDragOver('image', index, $event)"
              @drop="onDrop('image', index, $event)"
              @dragend="onDragEnd"
              class="relative aspect-square rounded-lg overflow-hidden group cursor-grab active:cursor-grabbing select-none transition-all duration-150"
              :class="{
                'opacity-40 scale-95': dragState?.type === 'image' && dragState.fromIndex === index,
                'ring-2 ring-accent-cyan': dragState?.type === 'image' && dropTargetIndex === index && dragState.fromIndex !== index,
              }"
            >
              <!-- 序號標記 -->
              <div class="absolute top-1 left-1 z-10 w-5 h-5 rounded-full bg-black/70 text-white text-[10px] flex items-center justify-center font-mono leading-none">
                {{ index + 1 }}
              </div>

              <!-- 圖片預覽 -->
              <img
                v-if="item.preview"
                :src="item.preview"
                :alt="`圖片 ${index + 1}`"
                class="w-full h-full object-cover"
              />
              <div v-else class="w-full h-full bg-zinc-800 animate-pulse"></div>

              <!-- 移除按鈕 -->
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
          <p v-if="imageItems.length > 1" class="text-zinc-600 text-xs mt-2">拖曳圖片可調整順序</p>
        </div>

        <!-- 上傳按鈕（拖曳重排序時禁用以避免誤觸發）-->
        <ImageUploader
          @upload="handleImagesSelected"
          :class="{ 'pointer-events-none': isDragging }"
        />
      </div>

      <!-- 分割線 -->
      <div class="border-t border-zinc-700/50 my-8"></div>

      <!-- 音樂上傳 -->
      <div class="mb-8">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-1 h-6 rounded-full bg-gradient-to-b from-accent-fuchsia to-accent-cyan"></div>
          <h2 class="text-xl font-bold font-display text-white">音樂（可選）</h2>
          <span v-if="audioItems.length > 0" class="text-zinc-500 text-sm">({{ audioItems.length }} 首)</span>
        </div>

        <!-- 已選擇的音樂列表（可拖曳重排序）-->
        <div v-if="audioItems.length > 0" class="space-y-2 mb-4">
          <div
            v-for="(item, index) in audioItems"
            :key="item.id"
            draggable="true"
            @dragstart="onDragStart('audio', index, $event)"
            @dragover="onDragOver('audio', index, $event)"
            @drop="onDrop('audio', index, $event)"
            @dragend="onDragEnd"
            class="flex items-center justify-between p-4 rounded-lg bg-bg-secondary border border-zinc-700/50 cursor-grab active:cursor-grabbing select-none transition-all duration-150"
            :class="{
              'opacity-40': dragState?.type === 'audio' && dragState.fromIndex === index,
              'border-accent-fuchsia ring-1 ring-accent-fuchsia': dragState?.type === 'audio' && dropTargetIndex === index && dragState.fromIndex !== index,
            }"
          >
            <div class="flex items-center gap-3 min-w-0">
              <!-- 拖曳手柄 -->
              <div class="shrink-0 text-zinc-600">
                <svg class="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
                  <circle cx="5" cy="3" r="1.5"/><circle cx="11" cy="3" r="1.5"/>
                  <circle cx="5" cy="8" r="1.5"/><circle cx="11" cy="8" r="1.5"/>
                  <circle cx="5" cy="13" r="1.5"/><circle cx="11" cy="13" r="1.5"/>
                </svg>
              </div>
              <!-- 序號 -->
              <span class="shrink-0 w-5 h-5 rounded-full bg-accent-fuchsia/20 text-accent-fuchsia text-[10px] flex items-center justify-center font-mono leading-none">
                {{ index + 1 }}
              </span>
              <!-- 音樂圖示 -->
              <div class="w-10 h-10 shrink-0 rounded-lg bg-accent-fuchsia/20 flex items-center justify-center">
                <svg class="w-5 h-5 text-accent-fuchsia" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                </svg>
              </div>
              <div class="min-w-0">
                <p class="text-white truncate">{{ item.file.name }}</p>
                <p class="text-zinc-500 text-xs">{{ formatFileSize(item.file.size) }}</p>
              </div>
            </div>
            <button @click="handleAudioRemove(index)" class="shrink-0 ml-3 text-zinc-400 hover:text-white transition-colors">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <p v-if="audioItems.length > 1" class="text-zinc-600 text-xs">拖曳音樂可調整播放順序</p>
        </div>

        <!-- 上傳按鈕（拖曳重排序時禁用）-->
        <AudioUploader
          @upload="handleAudiosSelected"
          :class="{ 'pointer-events-none': isDragging }"
        />
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
          :disabled="isRendering || (imageItems.length === 0 && audioItems.length === 0)"
        >
          清除全部
        </button>
        <button
          @click="startRender"
          class="btn-primary flex-1 flex items-center justify-center gap-2"
          :disabled="isRendering || imageItems.length === 0"
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
        <template v-if="audioItems.length > 0">
          圖片將根據音樂時長自動分配顯示時間
        </template>
        <template v-else-if="imageItems.length > 0">
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
