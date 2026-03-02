<script setup lang="ts">
import { computed } from 'vue'
import type { Project, ImageAsset, AudioAsset } from '@/types'
import { ImageCard, AudioCard } from '@/components/preview'
import ImageUploader from '@/components/upload/ImageUploader.vue'
import AudioUploader from '@/components/upload/AudioUploader.vue'

const props = defineProps<{
  project: Project
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'uploadImages', files: File[]): void
  (e: 'uploadAudios', files: File[]): void
  (e: 'removeImage', imageId: string): void
  (e: 'removeAudio', audioId: string): void
  (e: 'reorderImage', imageId: string, direction: 'up' | 'down'): void
  (e: 'updateSettings'): void
}>()

const totalImageDuration = computed(() => {
  const total = props.project.images.reduce((sum, img) => sum + (img.duration || 5), 0)
  return total.toFixed(1)
})

const totalAudioDuration = computed(() => {
  const total = props.project.audio.reduce((sum, audio) => sum + (audio.duration || 0), 0)
  return total.toFixed(1)
})

function formatDuration(seconds: number) {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}
</script>

<template>
  <div class="space-y-6">
    <!-- Project Header -->
    <div class="flex items-start justify-between">
      <div>
        <h1 class="text-2xl font-bold text-white mb-2">{{ project.name }}</h1>
        <p class="text-zinc-400">{{ project.description || '無描述' }}</p>
      </div>
      <div class="text-right">
        <p class="text-sm text-zinc-500">建立於 {{ new Date(project.created_at).toLocaleDateString('zh-TW') }}</p>
      </div>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="glass-card p-4">
        <p class="text-zinc-400 text-sm">圖片數量</p>
        <p class="text-2xl font-bold text-white">{{ project.images.length }}</p>
      </div>
      <div class="glass-card p-4">
        <p class="text-zinc-400 text-sm">影片時長</p>
        <p class="text-2xl font-bold text-white">{{ totalImageDuration }}s</p>
      </div>
      <div class="glass-card p-4">
        <p class="text-zinc-400 text-sm">音軌數量</p>
        <p class="text-2xl font-bold text-white">{{ project.audio.length }}</p>
      </div>
      <div class="glass-card p-4">
        <p class="text-zinc-400 text-sm">音訊時長</p>
        <p class="text-2xl font-bold text-white">{{ totalAudioDuration }}s</p>
      </div>
    </div>

    <!-- Image Section -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-semibold text-white flex items-center gap-2">
          <svg class="w-5 h-5 text-accent-violet" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          圖片素材
        </h2>
        <span class="text-zinc-500 text-sm">{{ project.images.length }} 張</span>
      </div>

      <!-- Upload Zone -->
      <ImageUploader
        :project-id="project.id"
        :disabled="loading"
        @upload="emit('uploadImages', $event)"
        @error="console.error($event)"
      />

      <!-- Image Grid -->
      <div v-if="project.images.length > 0" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <ImageCard
          v-for="image in project.images"
          :key="image.id"
          :id="image.id"
          :src="`/api/v1/upload/${image.file_id}`"
          :filename="image.filename"
          :width="image.width"
          :height="image.height"
          :duration="image.duration"
          :order="image.order"
          @remove="emit('removeImage', image.id)"
          @reorder="emit('reorderImage', image.id, $event)"
        />
      </div>
    </div>

    <!-- Audio Section -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-semibold text-white flex items-center gap-2">
          <svg class="w-5 h-5 text-accent-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
          背景音樂
        </h2>
        <span class="text-zinc-500 text-sm">{{ project.audio.length }} 首</span>
      </div>

      <!-- Upload Zone -->
      <AudioUploader
        :project-id="project.id"
        :disabled="loading"
        @upload="emit('uploadAudios', $event)"
        @error="console.error($event)"
      />

      <!-- Audio List -->
      <div v-if="project.audio.length > 0" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <AudioCard
          v-for="audio in project.audio"
          :key="audio.id"
          :id="audio.id"
          :filename="audio.filename"
          :duration="audio.duration"
          @remove="emit('removeAudio', audio.id)"
        />
      </div>
    </div>
  </div>
</template>
