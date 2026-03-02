<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  value: number
  max?: number
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
  variant?: 'default' | 'gradient' | 'success' | 'warning' | 'error'
}

const props = withDefaults(defineProps<Props>(), {
  max: 100,
  showLabel: false,
  size: 'md',
  variant: 'gradient',
})

const percent = computed(() => {
  return Math.min(100, Math.max(0, (props.value / props.max) * 100))
})

const heightClass = computed(() => {
  switch (props.size) {
    case 'sm': return 'h-1'
    case 'lg': return 'h-4'
    default: return 'h-2'
  }
})

const variantClass = computed(() => {
  switch (props.variant) {
    case 'success': return 'bg-emerald-500'
    case 'warning': return 'bg-amber-500'
    case 'error': return 'bg-red-500'
    case 'gradient':
    default:
      return 'progress-gradient'
  }
})
</script>

<template>
  <div class="progress-bar">
    <!-- Track -->
    <div
      class="w-full bg-white/10 rounded-full overflow-hidden"
      :class="heightClass"
    >
      <!-- Fill -->
      <div
        class="h-full rounded-full transition-all duration-500 ease-out"
        :class="variantClass"
        :style="{ width: `${percent}%` }"
      >
        <!-- Shine effect -->
        <div
          v-if="variant === 'gradient'"
          class="h-full w-full relative overflow-hidden"
        >
          <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full animate-shimmer" />
        </div>
      </div>
    </div>

    <!-- Label -->
    <div v-if="showLabel" class="flex justify-between mt-2 text-sm">
      <span class="text-zinc-400">{{ value }}%</span>
      <span class="text-zinc-500">{{ max }}%</span>
    </div>
  </div>
</template>

<style scoped>
.animate-shimmer {
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}
</style>
