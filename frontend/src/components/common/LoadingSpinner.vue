<script setup lang="ts">
defineProps<{
  size?: 'sm' | 'md' | 'lg'
  text?: string
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-4">
    <div
      class="relative"
      :class="{
        'w-6 h-6': size === 'sm',
        'w-10 h-10': size === 'md',
        'w-14 h-14': size === 'lg' || !size,
      }"
    >
      <!-- Outer ring -->
      <div class="absolute inset-0 rounded-full border-2 border-transparent border-t-accent-violet animate-spin" style="animation-duration: 1.5s;"></div>
      <!-- Inner ring -->
      <div class="absolute inset-1 rounded-full border-2 border-transparent border-t-accent-cyan animate-spin" style="animation-duration: 1s; animation-direction: reverse;"></div>
      <!-- Center dot -->
      <div class="absolute inset-0 m-auto w-1.5 h-1.5 rounded-full bg-accent-fuchsia animate-pulse"></div>
    </div>
    <p v-if="text" class="text-zinc-400 text-sm animate-pulse">{{ text }}</p>
  </div>
</template>
