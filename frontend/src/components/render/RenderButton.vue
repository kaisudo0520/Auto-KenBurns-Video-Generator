<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  disabled?: boolean
  loading?: boolean
  canRender: boolean
  imagesCount: number
}>()

const emit = defineEmits<{
  (e: 'click'): void
}>()

const buttonText = computed(() => {
  if (props.loading) return '正在啟動...'
  if (!props.canRender) return '請先上傳圖片'
  return '開始渲染'
})

const buttonClass = computed(() => {
  if (props.disabled || !props.canRender) {
    return 'bg-zinc-700/50 cursor-not-allowed opacity-50'
  }
  return 'btn-primary animate-glow-pulse'
})
</script>

<template>
  <div class="space-y-3">
    <button
      @click="emit('click')"
      :disabled="disabled || !canRender || loading"
      :class="buttonClass"
      class="w-full py-5 text-lg font-bold flex items-center justify-center gap-3"
    >
      <svg v-if="loading" class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
      <svg v-else class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      {{ buttonText }}
    </button>

    <p v-if="!canRender && imagesCount > 0" class="text-center text-zinc-500 text-sm">
      請先上傳圖片素材才能開始渲染
    </p>
  </div>
</template>
