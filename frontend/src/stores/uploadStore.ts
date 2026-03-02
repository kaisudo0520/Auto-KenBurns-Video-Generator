import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ImageFile, AudioFile, UploadProgress } from '@/types'
import { IMAGE_FILE_TYPES, AUDIO_FILE_TYPES } from '@/types'
import api from '@/services/api'

export const useUploadStore = defineStore('upload', () => {
  const uploadedImages = ref<ImageFile[]>([])
  const uploadedAudios = ref<AudioFile[]>([])
  const uploadProgress = ref<Map<string, UploadProgress>>(new Map())
  const uploading = ref(false)
  const error = ref<string | null>(null)

  const hasImages = computed(() => uploadedImages.value.length > 0)
  const hasAudios = computed(() => uploadedAudios.value.length > 0)
  const totalProgress = computed(() => {
    if (uploadProgress.value.size === 0) return 0
    let total = 0
    uploadProgress.value.forEach((p) => {
      total += p.progress
    })
    return total / uploadProgress.value.size
  })

  function validateImageFile(file: File): { valid: boolean; error?: string } {
    if (!IMAGE_FILE_TYPES.allowed_types.includes(file.type)) {
      return { valid: false, error: `不支援的檔案類型: ${file.type}` }
    }
    if (file.size > IMAGE_FILE_TYPES.max_size) {
      const maxMB = IMAGE_FILE_TYPES.max_size / (1024 * 1024)
      return { valid: false, error: `檔案過大: ${file.name} (最大 ${maxMB}MB)` }
    }
    return { valid: true }
  }

  function validateAudioFile(file: File): { valid: boolean; error?: string } {
    if (!AUDIO_FILE_TYPES.allowed_types.includes(file.type)) {
      return { valid: false, error: `不支援的檔案類型: ${file.type}` }
    }
    if (file.size > AUDIO_FILE_TYPES.max_size) {
      const maxMB = AUDIO_FILE_TYPES.max_size / (1024 * 1024)
      return { valid: false, error: `檔案過大: ${file.name} (最大 ${maxMB}MB)` }
    }
    return { valid: true }
  }

  function validateFiles(files: File[], type: 'image' | 'audio'): { valid: File[]; invalid: Array<{ file: File; error: string }> } {
    const validator = type === 'image' ? validateImageFile : validateAudioFile
    const valid: File[] = []
    const invalid: Array<{ file: File; error: string }> = []

    files.forEach((file) => {
      const result = validator(file)
      if (result.valid) {
        valid.push(file)
      } else {
        invalid.push({ file, error: result.error! })
      }
    })

    return { valid, invalid }
  }

  async function uploadImage(file: File, projectId?: string): Promise<ImageFile | null> {
    const validation = validateImageFile(file)
    if (!validation.valid) {
      error.value = validation.error || 'Invalid file'
      return null
    }

    const fileId = `upload_${Date.now()}_${file.name}`
    uploadProgress.value.set(fileId, {
      file_id: fileId,
      filename: file.name,
      progress: 0,
      bytes_uploaded: 0,
      bytes_total: file.size,
    })

    try {
      uploading.value = true
      // Simulate progress (actual progress would need XMLHttpRequest)
      updateProgress(fileId, 50)

      const response = await api.uploadImage(file, projectId)
      updateProgress(fileId, 100)

      const imageFile = response.data
      uploadedImages.value.push(imageFile)
      return imageFile
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Upload failed'
      return null
    } finally {
      setTimeout(() => {
        uploadProgress.value.delete(fileId)
      }, 1000)
      uploading.value = false
    }
  }

  async function uploadAudio(file: File, projectId?: string): Promise<AudioFile | null> {
    const validation = validateAudioFile(file)
    if (!validation.valid) {
      error.value = validation.error || 'Invalid file'
      return null
    }

    const fileId = `upload_${Date.now()}_${file.name}`
    uploadProgress.value.set(fileId, {
      file_id: fileId,
      filename: file.name,
      progress: 0,
      bytes_uploaded: 0,
      bytes_total: file.size,
    })

    try {
      uploading.value = true
      updateProgress(fileId, 50)

      const response = await api.uploadAudio(file, projectId)
      updateProgress(fileId, 100)

      const audioFile = response.data
      uploadedAudios.value.push(audioFile)
      return audioFile
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Upload failed'
      return null
    } finally {
      setTimeout(() => {
        uploadProgress.value.delete(fileId)
      }, 1000)
      uploading.value = false
    }
  }

  async function uploadImages(files: File[], projectId?: string): Promise<ImageFile[]> {
    const { valid, invalid } = validateFiles(files, 'image')
    if (invalid.length > 0) {
      error.value = invalid.map((i) => i.error).join(', ')
    }

    const uploaded: ImageFile[] = []
    for (const file of valid) {
      const result = await uploadImage(file, projectId)
      if (result) {
        uploaded.push(result)
      }
    }
    return uploaded
  }

  async function uploadAudios(files: File[], projectId?: string): Promise<AudioFile[]> {
    const { valid, invalid } = validateFiles(files, 'audio')
    if (invalid.length > 0) {
      error.value = invalid.map((i) => i.error).join(', ')
    }

    const uploaded: AudioFile[] = []
    for (const file of valid) {
      const result = await uploadAudio(file, projectId)
      if (result) {
        uploaded.push(result)
      }
    }
    return uploaded
  }

  function updateProgress(fileId: string, progress: number) {
    const existing = uploadProgress.value.get(fileId)
    if (existing) {
      uploadProgress.value.set(fileId, {
        ...existing,
        progress,
        bytes_uploaded: Math.round((existing.bytes_total * progress) / 100),
      })
    }
  }

  function removeImage(fileId: string) {
    uploadedImages.value = uploadedImages.value.filter((img) => img.file_id !== fileId)
  }

  function removeAudio(fileId: string) {
    uploadedAudios.value = uploadedAudios.value.filter((audio) => audio.file_id !== fileId)
  }

  function clearUploads() {
    uploadedImages.value = []
    uploadedAudios.value = []
    uploadProgress.value.clear()
    error.value = null
  }

  function clearError() {
    error.value = null
  }

  return {
    uploadedImages,
    uploadedAudios,
    uploadProgress,
    uploading,
    error,
    hasImages,
    hasAudios,
    totalProgress,
    validateImageFile,
    validateAudioFile,
    validateFiles,
    uploadImage,
    uploadAudio,
    uploadImages,
    uploadAudios,
    removeImage,
    removeAudio,
    clearUploads,
    clearError,
  }
})
