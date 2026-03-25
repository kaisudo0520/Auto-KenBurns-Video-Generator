<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  id: string
  filename: string
  duration?: number
  bpm?: number
  loudness?: number
  selected?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  duration: 0,
  bpm: 0,
  loudness: 0,
  selected: false,
})

const emit = defineEmits<{
  (e: 'select', id: string): void
  (e: 'remove', id: string): void
}>()

const waveformHeights = Array.from({ length: 40 }, () => Math.random() * 60 + 20)

const displayDuration = computed(() => {
  if (props.duration) {
    const minutes = Math.floor(props.duration / 60)
    const seconds = Math.floor(props.duration % 60)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }
  return '--:--'
})

const displayBPM = computed(() => {
  return props.bpm ? Math.round(props.bpm) : '--'
})

const displayLoudness = computed(() => {
  return props.loudness ? `${props.loudness.toFixed(1)} LUFS` : '--'
})
</script>
<template>
  <div
    class="audio-card group relative overflow-hidden rounded-xl bg-bg-tertiary border-2 transition-all duration-300 cursor-pointer"
    :class="selected ? 'border-accent-cyan shadow-lg shadow-accent-cyan/20' : 'border-transparent hover:border-white/10'"
    @click="emit('select', id)"
  >
    <!-- Visual Waveform Background -->
    <div class="absolute inset-0 overflow-hidden">
      <div class="absolute inset-0 bg-gradient-to-r from-accent-violet/10 via-accent-cyan/10 to-accent-fuchsia/10" />
      <!-- Animated bars -->
      <div class="absolute inset-0 flex items-center justify-center gap-0.5 opacity-30">
        <div
          v-for="i in 40"
          :key="i"
          class="w-1 bg-accent-violet rounded-full animate-pulse"
          :style="{
            height: `${waveformHeights[i - 1]}%`,
            animationDelay: `${i * 50}ms`
          }"
        />
      </div>
    </div>

    <!-- Content -->
    <div class="relative p-4">
      <div class="flex items-start gap-4">
        <!-- Icon -->
        <div class="relative flex-shrink-0">
          <div class="w-14 h-14 rounded-xl bg-gradient-to-br from-accent-violet/20 to-accent-cyan/20 flex items-center justify-center backdrop-blur-sm">
            <svg class="w-7 h-7 text-accent-violet" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
          </div>
          <!-- Play indicator -->
          <div class="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-accent-cyan flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
        </div>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <p class="text-white font-medium truncate" :title="filename">
            {{ filename }}
          </p>

          <div class="flex items-center gap-3 mt-2 text-xs text-zinc-500">
            <span class="flex items-center gap-1">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {{ displayDuration }}
            </span>
            <span class="flex items-center gap-1">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              {{ displayBPM }} BPM
            </span>
            <span class="flex items-center gap-1">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              </svg>
              {{ displayLoudness }}
            </span>
          </div>
        </div>

        <!-- Remove Button -->
        <button
          @click.stop="emit('remove', id)"
          class="flex-shrink-0 w-8 h-8 rounded-lg bg-red-500/0 hover:bg-red-500 text-zinc-500 hover:text-white flex items-center justify-center transition-all opacity-0 group-hover:opacity-100"
          title="刪除"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Selection Indicator -->
    <div
      v-if="selected"
      class="absolute inset-0 border-2 border-accent-cyan rounded-xl pointer-events-none"
    >
      <div class="absolute top-2 right-2 w-6 h-6 rounded-full bg-accent-cyan flex items-center justify-center">
        <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
      </div>
    </div>
  </div>
</template>

<style scoped>
.audio-card {
  min-height: 88px;
}
</style>
