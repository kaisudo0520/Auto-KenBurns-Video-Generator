<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  type: 'image' | 'audio'
  filename: string
  previewUrl?: string
  duration?: number
  size?: number
  width?: number
  height?: number
  order?: number
  selected?: boolean
}>()

const emit = defineEmits<{
  (e: 'remove'): void
  (e: 'select'): void
  (e: 'reorder', direction: 'up' | 'down'): void
}>()

const waveformHeights = Array.from({ length: 24 }, () => Math.random() * 70 + 30)

const formattedSize = computed(() => {
  if (!props.size) return ''
  const kb = props.size / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
})

const formattedDuration = computed(() => {
  if (!props.duration) return ''
  const mins = Math.floor(props.duration / 60)
  const secs = Math.floor(props.duration % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
})

const dimensions = computed(() => {
  if (!props.width || !props.height) return ''
  return `${props.width} x ${props.height}`
})
</script>

<template>
  <div
    class="relative group glass-card overflow-hidden card-hover"
    :class="selected ? 'ring-2 ring-accent-cyan' : ''"
    @click="emit('select')"
  >
    <!-- Image Preview -->
    <div v-if="type === 'image'" class="aspect-[4/3] relative">
      <img
        v-if="previewUrl"
        :src="previewUrl"
        :alt="filename"
        class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
      />
      <div v-else class="w-full h-full bg-gradient-to-br from-bg-tertiary to-bg-secondary flex items-center justify-center">
        <svg class="w-12 h-12 text-zinc-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      </div>

      <!-- Gradient overlay -->
      <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent"></div>

      <!-- Info -->
      <div class="absolute bottom-0 left-0 right-0 p-3">
        <p class="text-white text-sm font-medium truncate">{{ filename }}</p>
        <p class="text-zinc-400 text-xs">{{ dimensions }}</p>
      </div>
    </div>

    <!-- Audio Preview -->
    <div v-else class="p-5">
      <div class="flex items-center gap-4">
        <div class="w-14 h-14 rounded-xl bg-gradient-to-br from-accent-fuchsia/30 to-accent-violet/30 flex items-center justify-center flex-shrink-0">
          <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-white font-medium truncate">{{ filename }}</p>
          <div class="flex items-center gap-2 text-zinc-500 text-xs mt-1">
            <span v-if="formattedDuration">{{ formattedDuration }}</span>
            <span v-if="formattedSize" class="text-zinc-600">- {{ formattedSize }}</span>
          </div>
        </div>
      </div>

      <!-- Audio Waveform -->
      <div class="mt-4 flex items-center gap-0.5 h-10">
        <div
          v-for="i in 24"
          :key="i"
          class="flex-1 rounded-full transition-all duration-300"
          :class="i % 3 === 0 ? 'bg-accent-violet/60' : 'bg-accent-cyan/30'"
          :style="{ height: `${waveformHeights[i - 1]}%` }"
        ></div>
      </div>
    </div>

    <!-- Order Badge -->
    <div
      v-if="order !== undefined"
      class="absolute top-3 left-3 w-7 h-7 rounded-lg bg-gradient-to-br from-accent-cyan to-accent-violet text-white text-sm font-bold flex items-center justify-center shadow-lg"
    >
      {{ order + 1 }}
    </div>

    <!-- Hover Actions -->
    <div class="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-all duration-200 flex gap-1.5">
      <button
        v-if="order !== undefined && order > 0"
        @click.stop="emit('reorder', 'up')"
        class="p-2 rounded-lg bg-black/60 backdrop-blur-sm text-white hover:bg-accent-cyan/80 transition-colors"
        title="上移"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
        </svg>
      </button>
      <button
        @click.stop="emit('remove')"
        class="p-2 rounded-lg bg-black/60 backdrop-blur-sm text-white hover:bg-red-500/80 transition-colors"
        title="移除"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  </div>
</template>
