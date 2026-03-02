<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  src: string
  type: 'image' | 'video' | 'audio'
  alt?: string
  autoplay?: boolean
  loop?: boolean
  muted?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  alt: '媒體預覽',
  autoplay: false,
  loop: false,
  muted: true,
})

const isImage = computed(() => props.type === 'image')
const isVideo = computed(() => props.type === 'video')
const isAudio = computed(() => props.type === 'audio')
</script>

<template>
  <div class="media-preview relative overflow-hidden rounded-xl bg-bg-tertiary">
    <!-- Image Preview -->
    <img
      v-if="isImage"
      :src="src"
      :alt="alt"
      class="w-full h-full object-cover transition-transform duration-500 hover:scale-105"
    />

    <!-- Video Preview -->
    <video
      v-else-if="isVideo"
      :src="src"
      :autoplay="autoplay"
      :loop="loop"
      :muted="muted"
      controls
      class="w-full h-full object-contain"
    />

    <!-- Audio Preview -->
    <div v-else-if="isAudio" class="audio-preview p-6">
      <div class="flex items-center gap-4 mb-4">
        <div class="w-14 h-14 rounded-xl bg-gradient-to-br from-accent-violet/20 to-accent-cyan/20 flex items-center justify-center">
          <svg class="w-7 h-7 text-accent-violet" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-white font-medium truncate">{{ alt }}</p>
          <p class="text-zinc-500 text-sm">音訊檔案</p>
        </div>
      </div>
      <audio :src="src" controls class="w-full" />
    </div>

    <!-- Loading State -->
    <div v-if="!src" class="absolute inset-0 flex items-center justify-center">
      <div class="w-10 h-10 rounded-full border-2 border-accent-violet/30 border-t-accent-violet animate-spin"></div>
    </div>
  </div>
</template>

<style scoped>
.media-preview {
  aspect-ratio: 16 / 9;
}

.audio-preview {
  aspect-ratio: auto;
  min-height: 120px;
}

audio {
  height: 40px;
  border-radius: 20px;
}

audio::-webkit-media-controls-panel {
  background: linear-gradient(180deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.1));
}
</style>
