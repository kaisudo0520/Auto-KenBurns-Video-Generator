<script setup lang="ts">
import { ref } from 'vue'
import { AUDIO_EXTENSIONS } from '@/types'

const props = defineProps<{
  projectId?: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'upload', files: File[]): void
  (e: 'error', error: string): void
}>()

const isDragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  isDragging.value = true
}

function handleDragLeave(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false

  const files = Array.from(e.dataTransfer?.files || [])
  processFiles(files)
}

function handleFileSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const files = Array.from(target.files || [])
  processFiles(files)
  target.value = ''
}

function processFiles(files: File[]) {
  const validFiles = files.filter((file) => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!AUDIO_EXTENSIONS.includes(ext)) {
      emit('error', `不支援的檔案類型: ${file.name}`)
      return false
    }
    return true
  })

  if (validFiles.length > 0) {
    emit('upload', validFiles)
  }
}

function triggerFileInput() {
  if (!props.disabled) {
    fileInput.value?.click()
  }
}
</script>

<template>
  <div
    class="drop-zone relative group"
    :class="[
      isDragging ? 'drag-over' : '',
      disabled ? 'opacity-50 cursor-not-allowed' : '',
    ]"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
    @click="triggerFileInput"
  >
    <input
      ref="fileInput"
      type="file"
      multiple
      accept="audio/mpeg,audio/wav,audio/aac,audio/flac,audio/ogg"
      class="hidden"
      @change="handleFileSelect"
      :disabled="disabled"
    />

    <div class="flex flex-col items-center justify-center py-10">
      <!-- Icon -->
      <div class="relative mb-5">
        <div class="w-20 h-20 rounded-2xl bg-gradient-to-br from-accent-fuchsia/20 to-accent-violet/20 flex items-center justify-center transition-transform duration-300 group-hover:scale-110">
          <svg class="w-10 h-10 text-zinc-400 group-hover:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
        </div>
        <!-- Badge -->
        <div class="absolute -bottom-2 -right-2 w-8 h-8 rounded-lg bg-gradient-to-br from-accent-fuchsia to-accent-violet flex items-center justify-center">
          <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
        </div>
      </div>

      <p class="text-white text-lg font-medium mb-2">
        拖曳音樂至此處
      </p>
      <p class="text-zinc-500 text-sm mb-1">
        或點擊選擇檔案
      </p>
      <p class="text-zinc-600 text-xs">
        支援 MP3, WAV, AAC, FLAC, OGG
      </p>
    </div>

    <!-- Decorative corner -->
    <div class="absolute top-3 right-3 w-12 h-12 border-t-2 border-r-2 border-accent-fuchsia/30 rounded-tr-xl"></div>
    <div class="absolute bottom-3 left-3 w-12 h-12 border-b-2 border-l-2 border-accent-violet/30 rounded-bl-xl"></div>
  </div>
</template>
