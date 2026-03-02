<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projectStore'
import { useRenderStore } from '@/stores/renderStore'
import ProjectDetail from '@/components/project/ProjectDetail.vue'
import ProjectSettings from '@/components/project/ProjectSettings.vue'
import RenderProgress from '@/components/render/RenderProgress.vue'
import RenderButton from '@/components/render/RenderButton.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import api from '@/services/api'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const renderStore = useRenderStore()

const activeTab = ref<'detail' | 'settings'>('detail')
const uploadingImages = ref(false)
const uploadingAudios = ref(false)

const projectId = computed(() => route.params.id as string)

const canRender = computed(() => {
  if (!projectStore.currentProject) return false
  return projectStore.currentProject.images.length > 0
})

onMounted(async () => {
  await loadProject()
})

watch(projectId, async () => {
  await loadProject()
})

async function loadProject() {
  if (projectId.value) {
    await projectStore.fetchProject(projectId.value)
  }
}

async function handleUploadImages(files: File[]) {
  if (!projectStore.currentProject) return

  uploadingImages.value = true
  try {
    const uploadedFiles = await api.uploadImages(files)
    if (uploadedFiles.data.uploaded.length > 0) {
      const fileIds = uploadedFiles.data.uploaded.map(f => f.file_id)
      await api.addImagesToProject(projectId.value, { file_ids: fileIds })
      await loadProject()
    }
  } catch (error) {
    console.error('Failed to upload images:', error)
  } finally {
    uploadingImages.value = false
  }
}

async function handleUploadAudios(files: File[]) {
  if (!projectStore.currentProject) return

  uploadingAudios.value = true
  try {
    const uploadedFiles = await api.uploadAudios(files)
    if (uploadedFiles.data.uploaded.length > 0) {
      const fileIds = uploadedFiles.data.uploaded.map(f => f.file_id)
      await api.addAudioToProject(projectId.value, { file_ids: fileIds })
      await loadProject()
    }
  } catch (error) {
    console.error('Failed to upload audios:', error)
  } finally {
    uploadingAudios.value = false
  }
}

async function handleRemoveImage(imageId: string) {
  try {
    await api.removeImageFromProject(projectId.value, imageId)
    await loadProject()
  } catch (error) {
    console.error('Failed to remove image:', error)
  }
}

async function handleRemoveAudio(audioId: string) {
  try {
    await api.removeAudioFromProject(projectId.value, audioId)
    await loadProject()
  } catch (error) {
    console.error('Failed to remove audio:', error)
  }
}

async function handleReorderImage(imageId: string, direction: 'up' | 'down') {
  if (!projectStore.currentProject) return

  const images = [...projectStore.currentProject.images]
  const index = images.findIndex(img => img.id === imageId)

  if (direction === 'up' && index > 0) {
    const temp = images[index].order
    images[index].order = images[index - 1].order
    images[index - 1].order = temp
  } else if (direction === 'down' && index < images.length - 1) {
    const temp = images[index].order
    images[index].order = images[index + 1].order
    images[index + 1].order = temp
  }

  try {
    await projectStore.updateImageOrder(images.map(img => ({ id: img.id, order: img.order })))
    await loadProject()
  } catch (error) {
    console.error('Failed to reorder image:', error)
  }
}

async function handleUpdateSettings(settings: any) {
  try {
    await projectStore.updateSettings(settings)
  } catch (error) {
    console.error('Failed to update settings:', error)
  }
}

async function handleStartRender() {
  if (!canRender.value) return

  try {
    const job = await renderStore.startRender(projectId.value)
    if (job) {
      renderStore.connectProgressWS(job.job_id)
      // 導航到結果頁面
      router.push(`/result/${job.job_id}`)
    }
  } catch (error) {
    console.error('Failed to start render:', error)
  }
}

async function handleCancelRender() {
  if (!renderStore.currentJob) return

  try {
    await renderStore.cancelRender(renderStore.currentJob.job_id)
  } catch (error) {
    console.error('Failed to cancel render:', error)
  }
}

function handleDownload() {
  if (!renderStore.currentJob) return

  const url = api.getDownloadUrl(renderStore.currentJob.job_id)
  window.open(url, '_blank')
}
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Back Button -->
    <button
      @click="router.push('/')"
      class="flex items-center gap-2 text-zinc-400 hover:text-white mb-6 transition-colors group"
    >
      <svg class="w-5 h-5 group-hover:-translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      返回專案列表
    </button>

    <!-- Loading State -->
    <div v-if="projectStore.loading && !projectStore.currentProject" class="py-20">
      <LoadingSpinner size="lg" text="載入專案中..." />
    </div>

    <!-- Project Not Found -->
    <div v-else-if="!projectStore.currentProject" class="py-20 text-center">
      <div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-zinc-800 flex items-center justify-center">
        <svg class="w-10 h-10 text-zinc-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <p class="text-zinc-400 text-lg mb-4">專案不存在</p>
      <button @click="router.push('/')" class="btn-primary">
        返回首頁
      </button>
    </div>

    <!-- Project Content -->
    <div v-else class="space-y-6">
      <!-- Project Header -->
      <div class="flex items-start justify-between animate-fade-in-up">
        <div>
          <h1 class="text-3xl font-bold font-display text-white mb-2">{{ projectStore.currentProject.name }}</h1>
          <p class="text-zinc-400">{{ projectStore.currentProject.description || '無描述' }}</p>
        </div>
        <div class="text-right">
          <p class="text-sm text-zinc-500">建立於 {{ new Date(projectStore.currentProject.created_at).toLocaleDateString('zh-TW') }}</p>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex gap-2 border-b border-white/5 pb-2 animate-fade-in-up stagger-1">
        <button
          @click="activeTab = 'detail'"
          class="px-5 py-2.5 rounded-lg font-medium transition-all duration-200"
          :class="activeTab === 'detail' ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white hover:bg-white/5'"
        >
          <span class="flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            專案內容
          </span>
        </button>
        <button
          @click="activeTab = 'settings'"
          class="px-5 py-2.5 rounded-lg font-medium transition-all duration-200"
          :class="activeTab === 'settings' ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white hover:bg-white/5'"
        >
          <span class="flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            輸出設定
          </span>
        </button>
      </div>

      <!-- Render Progress -->
      <div v-if="renderStore.isRendering || renderStore.currentJob?.status === 'completed'" class="animate-fade-in-up stagger-2">
        <RenderProgress
          :progress="renderStore.progress"
          :status="renderStore.currentJob?.status || ''"
          :eta="renderStore.etaSeconds"
          @cancel="handleCancelRender"
        />
      </div>

      <!-- Tab Content -->
      <div v-if="activeTab === 'detail'" class="space-y-8 animate-fade-in-up stagger-3">
        <ProjectDetail
          :project="projectStore.currentProject"
          :loading="uploadingImages || uploadingAudios"
          @upload-images="handleUploadImages"
          @upload-audios="handleUploadAudios"
          @remove-image="handleRemoveImage"
          @remove-audio="handleRemoveAudio"
          @reorder-image="handleReorderImage"
        />
      </div>

      <div v-else class="animate-fade-in-up stagger-3">
        <ProjectSettings
          :settings="projectStore.projectSettings"
          @update="handleUpdateSettings"
        />
      </div>

      <!-- Render Button -->
      <div v-if="!renderStore.isRendering && renderStore.currentJob?.status !== 'completed'" class="mt-10 animate-fade-in-up stagger-4">
        <RenderButton
          :can-render="canRender"
          :loading="renderStore.loading"
          :images-count="projectStore.projectImages.length"
          @click="handleStartRender"
        />
      </div>

      <!-- Download Button -->
      <div v-if="renderStore.currentJob?.status === 'completed'" class="mt-10 animate-fade-in-up stagger-4">
        <button @click="handleDownload" class="btn-primary w-full py-4 text-lg font-bold flex items-center justify-center gap-3">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          下載影片
        </button>
      </div>
    </div>
  </div>
</template>
