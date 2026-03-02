<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { path: '/', label: '首頁', icon: 'home' },
  { path: '/settings', label: '系統', icon: 'settings' },
]
</script>

<template>
  <header class="fixed top-0 left-0 right-0 z-50 backdrop-blur-xl bg-bg-primary/80 border-b border-white/5">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <!-- Logo -->
        <div class="flex items-center gap-3">
          <RouterLink to="/" class="flex items-center gap-3 group">
            <div class="relative w-10 h-10 rounded-xl overflow-hidden">
              <div class="absolute inset-0 bg-gradient-to-br from-accent-cyan via-accent-violet to-accent-fuchsia"></div>
              <div class="absolute inset-0 flex items-center justify-center">
                <svg class="w-5 h-5 text-white drop-shadow-lg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
            </div>
            <span class="text-xl font-bold font-display tracking-tight">
              <span class="text-white">Ken</span><span class="text-accent-cyan">Burns</span>
            </span>
          </RouterLink>
        </div>

        <!-- Navigation -->
        <nav class="flex items-center gap-1">
          <RouterLink
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="relative px-4 py-2 text-sm font-medium transition-all duration-200 rounded-lg"
            :class="[
              route.path === item.path
                ? 'text-white'
                : 'text-zinc-400 hover:text-white'
            ]"
          >
            <span class="relative z-10">{{ item.label }}</span>
            <div
              v-if="route.path === item.path"
              class="absolute inset-0 bg-white/5 rounded-lg"
            ></div>
          </RouterLink>
        </nav>

        <!-- Right side actions -->
        <div class="flex items-center gap-2">
          <button class="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 transition-colors" title="說明">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </header>
  <!-- Spacer for fixed header -->
  <div class="h-16"></div>
</template>
