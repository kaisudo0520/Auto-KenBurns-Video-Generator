<script setup lang="ts">
import { ref } from 'vue'
import { IMAGE_EXTENSIONS } from '@/types'

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
    if (!IMAGE_EXTENSIONS.includes(ext)) {
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
      accept="image/jpeg,image/png,image/webp,image/bmp"
      class="hidden"
      @change="handleFileSelect"
      :disabled="disabled"
    />

    <div class="flex flex-col items-center justify-center py-10">
      <!-- Icon -->
      <div class="relative mb-5">
        <div class="w-20 h-20 rounded-2xl bg-gradient-to-br from-accent-violet/20 to-accent-cyan/20 flex items-center justify-center transition-transform duration-300 group-hover:scale-110">
          <svg class="w-10 h-10 text-zinc-400 group-hover:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </div>
        <!-- Badge -->
        <div class="absolute -bottom-2 -right-2 w-8 h-8 rounded-lg bg-gradient-to-br from-accent-cyan to-accent-violet flex items-center justify-center">
          <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
        </div>
      </div>

      <p class="text-white text-lg font-medium mb-2">
        拖曳圖片至此處
      </p>
      <p class="text-zinc-500 text-sm mb-1">
        或點擊選擇檔案
      </p>
      <p class="text-zinc-600 text-xs">
        支援 JPG, PNG, WebP, BMP
      </p>
    </div>

    <!-- Decorative corner -->
    <div class="absolute top-3 right-3 w-12 h-12 border-t-2 border-r-2 border-accent-violet/30 rounded-tr-xl"></div>
    <div class="absolute bottom-3 left-3 w-12 h-12 border-b-2 border-l-2 border-accent-cyan/30 rounded-bl-xl"></div>
  </div>
</template>
