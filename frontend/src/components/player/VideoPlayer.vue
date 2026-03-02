<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

interface Props {
  src: string
  poster?: string
  title?: string
  autoplay?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  poster: '',
  title: '影片預覽',
  autoplay: false,
})

const emit = defineEmits<{
  (e: 'play'): void
  (e: 'pause'): void
  (e: 'ended'): void
  (e: 'timeupdate', currentTime: number): void
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
const isPlaying = ref(false)
const isMuted = ref(true)
const isFullscreen = ref(false)
const showControls = ref(true)
const currentTime = ref(0)
const duration = ref(0)
const buffered = ref(0)
const volume = ref(1)

let controlsTimeout: ReturnType<typeof setTimeout> | null = null

const formattedCurrentTime = computed(() => formatTime(currentTime.value))
const formattedDuration = computed(() => formatTime(duration.value))

const progressPercent = computed(() => {
  if (duration.value === 0) return 0
  return (currentTime.value / duration.value) * 100
})

const bufferedPercent = computed(() => {
  if (duration.value === 0) return 0
  return (buffered.value / duration.value) * 100
})

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function togglePlay() {
  if (!videoRef.value) return

  if (isPlaying.value) {
    videoRef.value.pause()
  } else {
    videoRef.value.play()
  }
}

function toggleMute() {
  if (!videoRef.value) return
  videoRef.value.muted = !videoRef.value.muted
  isMuted.value = videoRef.value.muted
}

function toggleFullscreen() {
  if (!containerRef.value) return

  if (document.fullscreenElement) {
    document.exitFullscreen()
    isFullscreen.value = false
  } else {
    containerRef.value.requestFullscreen()
    isFullscreen.value = true
  }
}

function seek(e: MouseEvent) {
  if (!videoRef.value) return
  const target = e.currentTarget as HTMLDivElement
  const rect = target.getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  videoRef.value.currentTime = percent * duration.value
}

function setVolume(e: Event) {
  if (!videoRef.value) return
  const target = e.target as HTMLInputElement
  const newVolume = parseFloat(target.value)
  videoRef.value.volume = newVolume
  volume.value = newVolume
  isMuted.value = newVolume === 0
}

function handleTimeUpdate() {
  if (!videoRef.value) return
  currentTime.value = videoRef.value.currentTime
  emit('timeupdate', currentTime.value)
}

function handleLoadedMetadata() {
  if (!videoRef.value) return
  duration.value = videoRef.value.duration
}

function handleProgress() {
  if (!videoRef.value || !videoRef.value.buffered.length) return
  buffered.value = videoRef.value.buffered.end(videoRef.value.buffered.length - 1)
}

function handlePlay() {
  isPlaying.value = true
  emit('play')
}

function handlePause() {
  isPlaying.value = false
  emit('pause')
}

function handleEnded() {
  isPlaying.value = false
  emit('ended')
}

function showControlsTemporarily() {
  showControls.value = true
  if (controlsTimeout) {
    clearTimeout(controlsTimeout)
  }
  controlsTimeout = setTimeout(() => {
    if (isPlaying.value) {
      showControls.value = false
    }
  }, 3000)
}

onMounted(() => {
  if (props.autoplay && videoRef.value) {
    videoRef.value.play().catch(() => {
      // Autoplay blocked
    })
  }
})

onUnmounted(() => {
  if (controlsTimeout) {
    clearTimeout(controlsTimeout)
  }
})
</script>

<template>
  <div
    ref="containerRef"
    class="video-player relative overflow-hidden rounded-xl bg-black group"
    @mousemove="showControlsTemporarily"
    @mouseleave="isPlaying && (showControls = false)"
  >
    <!-- Video Element -->
    <video
      ref="videoRef"
      :src="src"
      :poster="poster"
      class="w-full h-full object-contain"
      @timeupdate="handleTimeUpdate"
      @loadedmetadata="handleLoadedMetadata"
      @progress="handleProgress"
      @play="handlePlay"
      @pause="handlePause"
      @ended="handleEnded"
      @click="togglePlay"
      playsinline
    />

    <!-- Center Play Button (when paused) -->
    <div
      v-if="!isPlaying"
      class="absolute inset-0 flex items-center justify-center cursor-pointer"
      @click="togglePlay"
    >
      <div class="w-20 h-20 rounded-full bg-white/10 backdrop-blur-sm flex items-center justify-center transition-all duration-300 hover:scale-110 hover:bg-white/20">
        <div class="w-16 h-16 rounded-full bg-gradient-to-br from-accent-violet to-accent-cyan flex items-center justify-center pl-1">
          <svg class="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
      </div>
    </div>

    <!-- Controls Overlay -->
    <div
      class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent pt-20 pb-4 px-4 transition-opacity duration-300"
      :class="showControls ? 'opacity-100' : 'opacity-0 pointer-events-none'"
    >
      <!-- Title -->
      <p v-if="title" class="text-white text-sm font-medium mb-3 truncate">{{ title }}</p>

      <!-- Progress Bar -->
      <div class="relative mb-3 group/progress">
        <!-- Buffered -->
        <div class="absolute inset-0 h-1 bg-white/20 rounded-full overflow-hidden">
          <div class="h-full bg-white/30 rounded-full" :style="{ width: `${bufferedPercent}%` }" />
        </div>
        <!-- Progress -->
        <div
          class="absolute inset-y-0 left-0 bg-gradient-to-r from-accent-cyan via-accent-violet to-accent-fuchsia rounded-full cursor-pointer"
          :style="{ width: `${progressPercent}%` }"
          @click="seek"
        >
          <div class="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-white shadow-lg opacity-0 group-hover/progress:opacity-100 transition-opacity" />
        </div>
      </div>

      <!-- Controls -->
      <div class="flex items-center gap-4">
        <!-- Play/Pause -->
        <button @click="togglePlay" class="text-white hover:text-accent-cyan transition-colors">
          <svg v-if="isPlaying" class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
          </svg>
          <svg v-else class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        </button>

        <!-- Volume -->
        <div class="flex items-center gap-2 group/volume">
          <button @click="toggleMute" class="text-white hover:text-accent-cyan transition-colors">
            <svg v-if="isMuted || volume === 0" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
            </svg>
            <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
            </svg>
          </button>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            :value="volume"
            @input="setVolume"
            class="w-0 group-hover/volume:w-20 transition-all duration-200 accent-accent-cyan"
          />
        </div>

        <!-- Time -->
        <span class="text-white text-sm font-mono ml-auto">
          {{ formattedCurrentTime }} / {{ formattedDuration }}
        </span>

        <!-- Fullscreen -->
        <button @click="toggleFullscreen" class="text-white hover:text-accent-cyan transition-colors">
          <svg v-if="!isFullscreen" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
video::-webkit-media-controls {
  display: none !important;
}

video::-webkit-media-controls-enclosure {
  display: none !important;
}
</style>
