<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { ProjectListItem } from '@/types'
import { useProjectStore } from '@/stores/projectStore'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const router = useRouter()
const projectStore = useProjectStore()

const props = defineProps<{
  projects: ProjectListItem[]
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'create'): void
  (e: 'delete', id: string): void
}>()

function formatDate(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function getStatusColor(status: string) {
  switch (status) {
    case 'completed':
      return 'bg-green-500/20 text-green-400'
    case 'processing':
      return 'bg-blue-500/20 text-blue-400'
    case 'failed':
      return 'bg-red-500/20 text-red-400'
    default:
      return 'bg-slate-500/20 text-slate-400'
  }
}

function getStatusLabel(status: string) {
  switch (status) {
    case 'completed':
      return '已完成'
    case 'processing':
      return '處理中'
    case 'failed':
      return '失敗'
    default:
      return '草稿'
  }
}

function openProject(project: ProjectListItem) {
  router.push(`/project/${project.id}`)
}
</script>

<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-2xl font-bold text-white">我的專案</h2>
      <button @click="emit('create')" class="btn-primary flex items-center gap-2">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        新建專案
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="py-12">
      <LoadingSpinner size="lg" text="載入專案中..." />
    </div>

    <!-- Empty State -->
    <div v-else-if="projects.length === 0" class="py-12 text-center">
      <div class="w-20 h-20 mx-auto mb-4 rounded-full bg-slate-800 flex items-center justify-center">
        <svg class="w-10 h-10 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      </div>
      <p class="text-slate-400 text-lg mb-2">尚無專案</p>
      <p class="text-slate-500 text-sm mb-6">建立您的第一個 Ken-Burns 影片專案</p>
      <button @click="emit('create')" class="btn-primary">
        建立專案
      </button>
    </div>

    <!-- Project Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="project in projects"
        :key="project.id"
        class="bg-slate-800 rounded-xl overflow-hidden card-hover cursor-pointer group"
        @click="openProject(project)"
      >
        <!-- Thumbnail -->
        <div class="aspect-video relative bg-slate-700">
          <img
            v-if="project.thumbnail"
            :src="project.thumbnail"
            :alt="project.name"
            class="w-full h-full object-cover"
          />
          <div v-else class="w-full h-full flex items-center justify-center">
            <svg class="w-16 h-16 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>

          <!-- Status Badge -->
          <div class="absolute top-3 right-3">
            <span
              class="px-2 py-1 rounded-full text-xs font-medium"
              :class="getStatusColor(project.status)"
            >
              {{ getStatusLabel(project.status) }}
            </span>
          </div>
        </div>

        <!-- Info -->
        <div class="p-4">
          <h3 class="text-white font-semibold truncate mb-1">{{ project.name }}</h3>
          <p class="text-slate-400 text-sm truncate mb-3">
            {{ project.description || '無描述' }}
          </p>

          <div class="flex items-center justify-between text-xs text-slate-500">
            <span>{{ formatDate(project.created_at) }}</span>
            <div class="flex items-center gap-3">
              <span class="flex items-center gap-1">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                {{ project.images_count }}
              </span>
              <span class="flex items-center gap-1">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                </svg>
                {{ project.audio_count }}
              </span>
            </div>
          </div>
        </div>

        <!-- Hover Actions -->
        <div class="absolute top-3 left-3 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            @click.stop="emit('delete', project.id)"
            class="p-2 rounded-lg bg-slate-900/80 text-white hover:bg-red-600 transition-colors"
            title="刪除"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
