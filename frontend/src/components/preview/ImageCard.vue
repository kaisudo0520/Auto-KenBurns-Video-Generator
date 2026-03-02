<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  id: string
  src: string
  filename: string
  width?: number
  height?: number
  order?: number
  duration?: number
  selected?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  width: 0,
  height: 0,
  order: 0,
  duration: 0,
  selected: false,
})

const emit = defineEmits<{
  (e: 'select', id: string): void
  (e: 'remove', id: string): void
  (e: 'reorder', id: string, direction: 'up' | 'down'): void
}>()

const dimensions = computed(() => {
  if (props.width && props.height) {
    return `${props.width} × ${props.height}`
  }
  return '未知尺寸'
})

const displayDuration = computed(() => {
  if (props.duration) {
    return `${props.duration.toFixed(1)}秒`
  }
  return '自動'
})
</script>

<template>
  <div
    class="image-card group relative overflow-hidden rounded-xl bg-bg-tertiary border-2 transition-all duration-300 cursor-pointer"
    :class="selected ? 'border-accent-violet shadow-lg shadow-accent-violet/20' : 'border-transparent hover:border-white/10'"
    @click="emit('select', id)"
  >
    <!-- Image -->
    <div class="aspect-video relative overflow-hidden">
      <img
        :src="src"
        :alt="filename"
        class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
      />

      <!-- Overlay -->
      <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

      <!-- Hover Actions -->
      <div class="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <button
          @click.stop="emit('remove', id)"
          class="w-8 h-8 rounded-lg bg-red-500/80 hover:bg-red-500 text-white flex items-center justify-center transition-colors"
          title="刪除"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Order Badge -->
      <div v-if="order !== undefined" class="absolute top-2 left-2 w-7 h-7 rounded-lg bg-black/50 backdrop-blur-sm flex items-center justify-center text-white text-sm font-medium">
        {{ order + 1 }}
      </div>

      <!-- Duration Badge -->
      <div v-if="duration" class="absolute bottom-2 right-2 px-2 py-1 rounded-md bg-black/60 backdrop-blur-sm text-white text-xs font-medium">
        {{ displayDuration }}
      </div>

      <!-- Selection Indicator -->
      <div v-if="selected" class="absolute inset-0 bg-accent-violet/20 border-2 border-accent-violet rounded-xl">
        <div class="absolute top-2 right-2 w-6 h-6 rounded-full bg-accent-violet flex items-center justify-center">
          <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
      </div>
    </div>

    <!-- Info -->
    <div class="p-3">
      <p class="text-white text-sm font-medium truncate" :title="filename">
        {{ filename }}
      </p>
      <p class="text-zinc-500 text-xs mt-1">
        {{ dimensions }}
      </p>
    </div>

    <!-- Reorder Buttons -->
    <div class="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-full pr-2 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col gap-1">
      <button
        @click.stop="emit('reorder', id, 'up')"
        class="w-6 h-6 rounded bg-bg-elevated hover:bg-accent-violet text-white flex items-center justify-center transition-colors"
        title="上移"
      >
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
        </svg>
      </button>
    </div>
    <div class="absolute right-0 top-1/2 -translate-y-1/2 translate-x-full pl-2 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col gap-1">
      <button
        @click.stop="emit('reorder', id, 'down')"
        class="w-6 h-6 rounded bg-bg-elevated hover:bg-accent-violet text-white flex items-center justify-center transition-colors"
        title="下移"
      >
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.image-card:hover .image-card-actions {
  opacity: 1;
}
</style>
