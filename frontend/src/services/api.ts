import axios, { AxiosInstance, AxiosError } from 'axios'
import type {
  ApiResponse,
  PaginatedResponse,
  Project,
  ProjectListItem,
  ProjectListParams,
  CreateProjectRequest,
  UpdateProjectRequest,
  AddImagesRequest,
  AddAudioRequest,
  ImageFile,
  AudioFile,
  StartRenderRequest,
  StartRenderResponse,
  RenderJobStatus,
  CancelRenderResponse,
  RenderHistoryItem,
  SettingsOptions,
  SystemStatus,
  ValidateSettingsRequest,
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    })

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('API Error:', error.response?.data)
        return Promise.reject(error)
      }
    )
  }

  // Project APIs
  async getProjects(params?: ProjectListParams): Promise<PaginatedResponse<ProjectListItem>> {
    const response = await this.client.get<PaginatedResponse<ProjectListItem>>('/projects', { params })
    return response.data
  }

  async getProject(projectId: string): Promise<ApiResponse<Project>> {
    const response = await this.client.get<ApiResponse<Project>>(`/projects/${projectId}`)
    return response.data
  }

  async createProject(data: CreateProjectRequest): Promise<ApiResponse<Project>> {
    const response = await this.client.post<ApiResponse<Project>>('/projects', data)
    return response.data
  }

  async updateProject(projectId: string, data: UpdateProjectRequest): Promise<ApiResponse<Project>> {
    const response = await this.client.put<ApiResponse<Project>>(`/projects/${projectId}`, data)
    return response.data
  }

  async deleteProject(projectId: string): Promise<void> {
    await this.client.delete(`/projects/${projectId}`)
  }

  async addImagesToProject(projectId: string, data: AddImagesRequest): Promise<ApiResponse<{ added: string[]; project_images_count: number }>> {
    const response = await this.client.post<ApiResponse<{ added: string[]; project_images_count: number }>>(`/projects/${projectId}/images`, data)
    return response.data
  }

  async addAudioToProject(projectId: string, data: AddAudioRequest): Promise<ApiResponse<{ added: string[]; project_audio_count: number }>> {
    const response = await this.client.post<ApiResponse<{ added: string[]; project_audio_count: number }>>(`/projects/${projectId}/audio`, data)
    return response.data
  }

  async removeImageFromProject(projectId: string, imageId: string): Promise<void> {
    await this.client.delete(`/projects/${projectId}/images/${imageId}`)
  }

  async removeAudioFromProject(projectId: string, audioId: string): Promise<void> {
    await this.client.delete(`/projects/${projectId}/audio/${audioId}`)
  }

  // Upload APIs
  async uploadImage(file: File, projectId?: string): Promise<ApiResponse<ImageFile>> {
    const formData = new FormData()
    formData.append('file', file)
    if (projectId) {
      formData.append('project_id', projectId)
    }
    const response = await this.client.post<ApiResponse<ImageFile>>('/upload/image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  async uploadAudio(file: File, projectId?: string): Promise<ApiResponse<AudioFile>> {
    const formData = new FormData()
    formData.append('file', file)
    if (projectId) {
      formData.append('project_id', projectId)
    }
    const response = await this.client.post<ApiResponse<AudioFile>>('/upload/audio', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  async uploadImages(files: File[], projectId?: string): Promise<ApiResponse<{ uploaded: Array<{ file_id: string; filename: string; status: string }>; failed: Array<{ filename: string; status: string; error: string }> }>> {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    if (projectId) {
      formData.append('project_id', projectId)
    }
    const response = await this.client.post<ApiResponse<{ uploaded: Array<{ file_id: string; filename: string; status: string }>; failed: Array<{ filename: string; status: string; error: string }> }>>('/upload/images', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  async uploadAudios(files: File[], projectId?: string): Promise<ApiResponse<{ uploaded: Array<{ file_id: string; filename: string; status: string }>; failed: Array<{ filename: string; status: string; error: string }> }>> {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    if (projectId) {
      formData.append('project_id', projectId)
    }
    const response = await this.client.post<ApiResponse<{ uploaded: Array<{ file_id: string; filename: string; status: string }>; failed: Array<{ filename: string; status: string; error: string }> }>>('/upload/audios', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  async getUploadStatus(fileId: string): Promise<ApiResponse<ImageFile | AudioFile>> {
    const response = await this.client.get<ApiResponse<ImageFile | AudioFile>>(`/upload/${fileId}`)
    return response.data
  }

  async deleteUpload(fileId: string): Promise<void> {
    await this.client.delete(`/upload/${fileId}`)
  }

  // Render APIs
  async startRender(data: StartRenderRequest): Promise<ApiResponse<StartRenderResponse>> {
    const response = await this.client.post<ApiResponse<StartRenderResponse>>('/render/start', data)
    return response.data
  }

  async getRenderStatus(jobId: string): Promise<ApiResponse<RenderJobStatus>> {
    const response = await this.client.get<ApiResponse<RenderJobStatus>>(`/render/status/${jobId}`)
    return response.data
  }

  async cancelRender(jobId: string): Promise<ApiResponse<CancelRenderResponse>> {
    const response = await this.client.post<ApiResponse<CancelRenderResponse>>(`/render/cancel/${jobId}`)
    return response.data
  }

  async getRenderHistory(projectId: string): Promise<ApiResponse<RenderHistoryItem[]>> {
    const response = await this.client.get<ApiResponse<RenderHistoryItem[]>>(`/render/history/${projectId}`)
    return response.data
  }

  // Quick Render API - 直接上傳圖片和音樂進行渲染
  async quickRender(
    images: File[],
    audios: File[] = [],
    imageDurations: number[] = []
  ): Promise<{ job_id: string; status: string; estimated_duration: number; webSocket_url: string }> {
    const formData = new FormData()

    // 添加圖片
    images.forEach((img) => {
      formData.append('images', img)
    })

    // 添加音樂（支援多首）
    audios.forEach((audio) => {
      formData.append('audios', audio)
    })

    // 添加圖片時長
    formData.append('image_durations', JSON.stringify(imageDurations))

    const response = await this.client.post('/quick-render', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  async getQuickRenderStatus(jobId: string): Promise<any> {
    const response = await this.client.get(`/quick-render/status/${jobId}`)
    return response.data
  }

  async openOutputFolder(jobId: string): Promise<{ success: boolean; folder: string; file: string }> {
    const response = await this.client.post<{ success: boolean; folder: string; file: string }>(`/render/open-folder/${jobId}`)
    return response.data
  }

  getDownloadUrl(jobId: string, quality?: string): string {
    const url = new URL(`${API_BASE_URL}/render/download/${jobId}`, window.location.origin)
    if (quality) {
      url.searchParams.set('quality', quality)
    }
    return url.toString()
  }

  getPreviewUrl(jobId: string, frame: number): string {
    const url = new URL(`${API_BASE_URL}/render/preview/${jobId}`, window.location.origin)
    url.searchParams.set('frame', frame.toString())
    return url.toString()
  }

  // Settings APIs
  async getSettingsOptions(): Promise<ApiResponse<SettingsOptions>> {
    const response = await this.client.get<ApiResponse<SettingsOptions>>('/settings/options')
    return response.data
  }

  async getSystemStatus(): Promise<ApiResponse<SystemStatus>> {
    const response = await this.client.get<ApiResponse<SystemStatus>>('/settings/system')
    return response.data
  }

  async validateSettings(data: ValidateSettingsRequest): Promise<ApiResponse<{ valid: boolean; warnings?: Array<{ field: string; message: string }> }>> {
    const response = await this.client.post<ApiResponse<{ valid: boolean; warnings?: Array<{ field: string; message: string }> }>>('/settings/validate', data)
    return response.data
  }
}

export const api = new ApiClient()
export default api
