import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Project, ProjectListItem, CreateProjectRequest, UpdateProjectRequest, RenderSettings } from '@/types'
import { DEFAULT_RENDER_SETTINGS } from '@/types'
import api from '@/services/api'

export const useProjectStore = defineStore('project', () => {
  // 內部 ref
  const _projects = ref<ProjectListItem[]>([])
  // 對外暴露的 computed，確保永遠有值
  const projects = computed(() => _projects.value ?? [])

  const currentProject = ref<Project | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({
    page: 1,
    page_size: 20,
    total_items: 0,
    total_pages: 0,
  })

  const hasProject = computed(() => currentProject.value !== null)
  const projectImages = computed(() => currentProject.value?.images || [])
  const projectAudio = computed(() => currentProject.value?.audio || [])
  const projectSettings = computed(() => currentProject.value?.settings || DEFAULT_RENDER_SETTINGS)

  async function fetchProjects(params?: {
    page?: number
    page_size?: number
    status?: string
    sort_by?: string
    sort_order?: string
  }) {
    loading.value = true
    error.value = null
    try {
      const response = await api.getProjects(params)
      // response is { success: true, data: [...], pagination: {...} }
      _projects.value = response.data ?? []
      pagination.value = response.pagination ?? { page: 1, page_size: 20, total_items: 0, total_pages: 0 }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch projects'
      // 確保即使失敗也有空陣列
      _projects.value = []
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(projectId: string) {
    loading.value = true
    error.value = null
    try {
      const response = await api.getProject(projectId)
      currentProject.value = response.data
      return response.data
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch project'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createProject(data: CreateProjectRequest) {
    loading.value = true
    error.value = null
    try {
      const response = await api.createProject(data)
      // response is { success: true, data: {...project} }
      const newProject = response.data
      // Convert to ProjectListItem format for the list
      const listItem: ProjectListItem = {
        id: newProject.id,
        name: newProject.name,
        description: newProject.description,
        status: newProject.status,
        created_at: newProject.created_at,
        updated_at: newProject.updated_at,
        images_count: 0,
        audio_count: 0,
      }
      // 確保陣列存在
      if (!_projects.value) {
        _projects.value = []
      }
      _projects.value.unshift(listItem)
      return newProject
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create project'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateProject(projectId: string, data: UpdateProjectRequest) {
    loading.value = true
    error.value = null
    try {
      const response = await api.updateProject(projectId, data)
      currentProject.value = response.data
      const index = _projects.value.findIndex((p) => p.id === projectId)
      if (index !== -1) {
        _projects.value[index] = {
          ...response.data,
          images_count: response.data.images?.length ?? 0,
          audio_count: response.data.audio?.length ?? 0,
        } as ProjectListItem
      }
      return response.data
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update project'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteProject(projectId: string) {
    loading.value = true
    error.value = null
    try {
      await api.deleteProject(projectId)
      _projects.value = (_projects.value ?? []).filter((p) => p.id !== projectId)
      if (currentProject.value?.id === projectId) {
        currentProject.value = null
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete project'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateSettings(settings: Partial<RenderSettings>) {
    if (!currentProject.value) return
    return updateProject(currentProject.value.id, { settings })
  }

  async function updateImageOrder(images: Array<{ id: string; duration?: number; order?: number }>) {
    if (!currentProject.value) return
    return updateProject(currentProject.value.id, { images })
  }

  function clearCurrentProject() {
    currentProject.value = null
  }

  return {
    projects,
    currentProject,
    loading,
    error,
    pagination,
    hasProject,
    projectImages,
    projectAudio,
    projectSettings,
    fetchProjects,
    fetchProject,
    createProject,
    updateProject,
    deleteProject,
    updateSettings,
    updateImageOrder,
    clearCurrentProject,
  }
})
