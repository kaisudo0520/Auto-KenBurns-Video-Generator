<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  status: 'idle' | 'processing' | 'completed' | 'error' | 'pending'
  size?: 'sm' | 'md' | 'lg'
  label?: string
  showLabel?: boolean
  animate?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  showLabel: true,
  animate: true,
})

const sizeClass = computed(() => {
  switch (props.size) {
    case 'sm': return 'w-2 h-2'
    case 'lg': return 'w-4 h-4'
    default: return 'w-3 h-3'
  }
})

const statusConfig = computed(() => {
  switch (props.status) {
    case 'processing':
      return {
        class: 'bg-accent-cyan',
        label: props.label || '處理中',
        pulse: props.animate,
      }
    case 'completed':
      return {
        class: 'bg-emerald-500',
        label: props.label || '已完成',
        pulse: false,
      }
    case 'error':
      return {
        class: 'bg-red-500',
        label: props.label || '錯誤',
        pulse: false,
      }
    case 'pending':
      return {
        class: 'bg-amber-500',
        label: props.label || '等待中',
        pulse: true,
      }
    case 'idle':
    default:
      return {
        class: 'bg-zinc-500',
        label: props.label || '閒置',
        pulse: false,
      }
  }
})
</script>

<template>
  <div class="status-indicator inline-flex items-center gap-2">
    <!-- Dot -->
    <div class="relative flex items-center justify-center">
      <div
        class="rounded-full"
        :class="[sizeClass, statusConfig.class]"
      />
      <!-- Pulse ring -->
      <div
        v-if="statusConfig.pulse"
        class="absolute inset-0 rounded-full"
        :class="[statusConfig.class, 'animate-ping opacity-75']"
      />
    </div>

    <!-- Label -->
    <span
      v-if="showLabel"
      class="text-sm"
      :class="{
        'text-accent-cyan': status === 'processing',
        'text-emerald-400': status === 'completed',
        'text-red-400': status === 'error',
        'text-amber-400': status === 'pending',
        'text-zinc-500': status === 'idle'
      }"
    >
      {{ statusConfig.label }}
    </span>
  </div>
</template>
