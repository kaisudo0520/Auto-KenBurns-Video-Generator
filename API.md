# Auto-KenBurns Video Generator - API 規格書

**文件版本**: 1.0
**更新日期**: 2026-03-01
**專案名稱**: Auto-KenBurns Video Generator

---

## 目錄

1. [概述](#1-概述)
2. [基礎資訊](#2-基礎資訊)
3. [錯誤回應格式](#3-錯誤回應格式)
4. [上傳模組 (Upload)](#4-上傳模組-upload)
5. [專案管理 (Projects)](#5-專案管理-projects)
6. [渲染任務 (Render)](#6-渲染任務-render)
7. [設定 (Settings)](#7-設定-settings)
8. [WebSocket 即時通訊](#8-websocket-即時通訊)
9. [附錄](#9-附錄)

---

## 1. 概述

本文件定義自動化 Ken-Burns 影片生成系統的 RESTful API 規格，包含上傳、專案管理、渲染任務和設定功能。

### 1.1 技術堆疊

| 層面 | 技術 |
|------|------|
| 後端框架 | FastAPI (Python 3.10+) |
| 前端框架 | Vite + Vue 3 + TypeScript |
| 即時通訊 | WebSocket |
| 資料驗證 | Pydantic v2 |

### 1.2 API 設計原則

- RESTful 最佳實踐
- HTTP 狀態碼正確使用
- 請求/回應格式標準化
- 錯誤回應結構一致
- OpenAPI/Swagger 自動文件生成

---

## 2. 基礎資訊

### 2.1 基礎 URL

```
Base URL: http://localhost:8000
API Prefix: /api/v1
WebSocket: ws://localhost:8000/ws
```

### 2.2 請求 Header

所有 API 請求必須包含以下 Header：

```http
Content-Type: application/json
Accept: application/json
```

### 2.3 通用回應格式

#### 成功回應 (200-299)

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功訊息"
}
```

#### 分頁回應

```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 100,
    "total_pages": 5
  }
}
```

---

## 3. 錯誤回應格式

### 3.1 錯誤回應結構

所有錯誤回應遵循以下格式：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "錯誤訊息描述",
    "details": { ... },
    "request_id": "req_abc123"
  }
}
```

### 3.2 HTTP 狀態碼

| 狀態碼 | 意義 | 使用場景 |
|--------|------|----------|
| 200 | OK | 請求成功 |
| 201 | Created | 資源建立成功 |
| 204 | No Content | 刪除成功，無回傳內容 |
| 400 | Bad Request | 請求格式錯誤 |
| 401 | Unauthorized | 未授權 |
| 403 | Forbidden | 權限不足 |
| 404 | Not Found | 資源不存在 |
| 413 | Payload Too Large | 檔案過大 |
| 422 | Validation Error | 驗證錯誤 |
| 429 | Too Many Requests | 請求過多 |
| 500 | Internal Error | 伺服器內部錯誤 |
| 503 | Service Unavailable | 服務不可用 |

### 3.3 業務邏輯錯誤碼

| 錯誤碼 | HTTP 狀態 | 描述 |
|--------|-----------|------|
| INVALID_FILE_TYPE | 400 | 不支援的檔案類型 |
| FILE_CORRUPTED | 400 | 檔案損壞 |
| FILE_TOO_LARGE | 413 | 檔案大小超過限制 |
| INSUFFICIENT_STORAGE | 507 | 儲存空間不足 |
| PROJECT_NOT_FOUND | 404 | 專案不存在 |
| RENDER_IN_PROGRESS | 400 | 渲染任務進行中 |
| RENDER_FAILED | 500 | 渲染失敗 |
| JOB_NOT_FOUND | 404 | 任務不存在 |
| JOB_CANCELLED | 410 | 任務已取消 |
| GPU_NOT_AVAILABLE | 503 | GPU 不可用 |
| AUDIO_PROCESSING_FAILED | 500 | 音訊處理失敗 |

---

## 4. 上傳模組 (Upload)

### 4.1 上傳圖片

上傳圖片檔案到伺服器。

**端點**: `POST /api/v1/upload/image`

**請求 Header**:
```http
Content-Type: multipart/form-data
```

**請求參數** (Form Data):

| 參數 | 類型 | 必填 | 描述 |
|------|------|------|------|
| file | File | 是 | 圖片檔案 (JPEG, PNG, WebP, BMP) |
| project_id | string | 否 | 關聯的專案 ID |

**請求範例**:
```bash
curl -X POST http://localhost:8000/api/v1/upload/image \
  -F "file=@image.jpg" \
  -F "project_id=proj_abc123"
```

**成功回應** (200):
```json
{
  "success": true,
  "data": {
    "file_id": "file_img_001",
    "filename": "image.jpg",
    "content_type": "image/jpeg",
    "size": 1024000,
    "width": 1920,
    "height": 1080,
    "uploaded_at": "2026-03-01T10:30:00Z"
  }
}
```

**錯誤回應**:
```json
{
  "success": false,
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "不支援的檔案類型",
    "details": {
      "allowed_types": ["image/jpeg", "image/png", "image/webp", "image/bmp"],
      "received_type": "image/gif"
    }
  }
}
```

---

### 4.2 上傳音樂

上傳音訊檔案到伺服器。

**端點**: `POST /api/v1/upload/audio`

**請求 Header**:
```http
Content-Type: multipart/form-data
```

**請求參數** (Form Data):

| 參數 | 類型 | 必填 | 描述 |
|------|------|------|------|
| file | File | 是 | 音訊檔案 (MP3, WAV, AAC, FLAC, OGG) |
| project_id | string | 否 | 關聯的專案 ID |

**成功回應** (200):
```json
{
  "success": true,
  "data": {
    "file_id": "file_audio_001",
    "filename": "music.mp3",
    "content_type": "audio/mpeg",
    "size": 5120000,
    "duration": 180.5,
    "sample_rate": 44100,
    "loudness": -14.2,
    "uploaded_at": "2026-03-01T10:30:00Z"
  }
}
```

---

### 4.3 批量上傳圖片

一次上傳多張圖片。

**端點**: `POST /api/v1/upload/images`

**請求參數** (Form Data):

| 參數 | 類型 | 必填 | 描述 |
|------|------|------|------|
| files | File[] | 是 | 多個圖片檔案 |
| project_id | string | 否 | 關聯的專案 ID |

**成功回應** (200):
```json
{
  "success": true,
  "data": {
    "uploaded": [
      {
        "file_id": "file_img_001",
        "filename": "image1.jpg",
        "status": "success"
      },
      {
        "file_id": "file_img_002",
        "filename": "image2.png",
        "status": "success"
      }
    ],
    "failed": [
      {
        "filename": "corrupted.jpg",
        "status": "failed",
        "error": "FILE_CORRUPTED"
      }
    ]
  }
}
```

---

### 4.4 批量上傳音樂

一次上傳多首音樂。

**端點**: `POST /api/v1/upload/audios`

**請求參數** (Form Data):

| 參數 | 類型 | 必填 | 描述 |
|------|------|------|------|
| files | File[] | 是 | 多個音訊檔案 |
| project_id | string | 否 | 關聯的專案 ID |

---

### 4.5 取得上傳狀態

取得檔案上傳的詳細資訊。

**端點**: `GET /api/v1/upload/{file_id}`

**路徑參數**:

| 參數 | 類型 | 描述 |
|------|------|------|
| file_id | string | 檔案 ID |

**成功回應** (200):
```json
{
  "success": true,
  "data": {
    "file_id": "file_img_001",
    "filename": "image.jpg",
    "content_type": "image/jpeg",
    "size": 1024000,
    "width": 1920,
    "height": 1080,
    "uploaded_at": "2026-03-01T10:30:00Z",
    "status": "ready"
  }
}
```

---

### 4.6 刪除上傳檔案

刪除已上傳的檔案。

**端點**: `DELETE /api/v1/upload/{file_id}`

**成功回應** (204): No Content

---

## 5. 專案管理 (Projects)

### 5.1 建立專案

建立一個新的 Ken-Burns 專案。

**端點**: `POST /api/v1/projects`

**請求體**:

```json
{
  "name": "我的 Ken-Burns 影片",
  "description": "家族旅行影片",
  "settings": {
    "resolution": "1080p",
    "fps": 30,
    "output_format": "mp4_h264",
    "video_bitrate": 8000000,
    "audio_bitrate": 192000,
    "kenburns": {
      "effect_type": "compose_pan_zoom",
      "duration": 5.0,
      "easing": "ease_in_out",
      "min_zoom": 1.0,
      "max_zoom": 1.5
    },
    "audio_fade": {
      "fade_in": 2.0,
      "fade_out": 2.0,
      "crossfade": true
    }
  }
}
```

**請求欄位說明**:

| 欄位 | 類型 | 必填 | 預設值 | 描述 |
|------|------|------|--------|------|
| name | string | 是 | - | 專案名稱 (最大 100 字元) |
| description | string | 否 | "" | 專案描述 |
| settings | object | 否 | 見下方 | 渲染設定 |

**settings 預設值**:
```json
{
  "resolution": "1080p",
  "fps": 30,
  "output_format": "mp4_h264",
  "video_bitrate": 8000000,
  "audio_bitrate": 192000,
  "kenburns": {
    "effect_type": "compose_pan_zoom",
    "duration": 5.0,
    "easing": "ease_in_out",
    "min_zoom": 1.0,
    "max_zoom": 1.5
  },
  "audio_fade": {
    "fade_in": 2.0,
    "fade_out": 2.0,
    "crossfade": true
  }
}
```

**成功回應** (201):
```json
{
  "success": true,
  "data": {
    "id": "proj_abc123",
    "name": "我的 Ken-Burns 影片",
    "description": "家族旅行影片",
    "created_at": "2026-03-01T10:30:00Z",
    "updated_at": "2026-03-01T10:30:00Z",
    "status": "draft",
    "images": [],
    "audio": [],
    "settings": { ... }
  }
}
```

---

### 5.2 取得專案列表

取得所有專案列表（分頁）。

**端點**: `GET /api/v1/projects`

**查詢參數**:

| 參數 | 類型 | 預設值 | 描述 |
|------|------|--------|------|
| page | integer | 1 | 頁碼 |
| page_size | integer | 20 | 每頁數量 (最大 100) |
| status | string | - | 篩選狀態 (draft, processing, completed, failed) |
| sort_by | string | created_at | 排序欄位 |
| sort_order | string | desc | 排序方向 (asc, desc) |

**成功回應** (200):
```json
{
  "success": true,
  "data": [
    {
      "id": "proj_abc123",
      "name": "我的 Ken-Burns 影片",
      "description": "家族旅行影片",
      "created_at": "2026-03-01T10:30:00Z",
      "updated_at": "2026-03-01T10:30:00Z",
      "status": "draft",
      "images_count": 10,
      "audio_count": 2,
      "thumbnail": "/uploads/thumbnails/proj_abc123.jpg"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 50,
    "total_pages": 3
  }
}
```

---

### 5.3 取得專案詳情

取得特定專案的完整資訊。

**端點**: `GET /api/v1/projects/{project_id}`

**路徑參數**:

| 參數 | 類型 | 描述 |
|------|------|------|
| project_id | string | 專案 ID |

**成功回應** (200):
```json
{
  "success": true,
  "data": {
    "id": "proj_abc123",
    "name": "我的 Ken-Burns 影片",
    "description": "家族旅行影片",
    "created_at": "2026-03-01T10:30:00Z",
    "updated_at": "2026-03-01T12:00:00Z",
    "status": "draft",
    "images": [
      {
        "id": "img_001",
        "file_id": "file_img_001",
        "filename": "photo1.jpg",
        "width": 1920,
        "height": 1080,
        "duration": 5.0,
        "order": 0,
        "subject_regions": [
          {
            "type": "person",
            "bounds": {
              "x": 0.3,
              "y": 0.2,
              "width": 0.4,
              "height": 0.6
            },
            "confidence": 0.95
          }
        ]
      }
    ],
    "audio": [
      {
        "id": "audio_001",
        "file_audio_ "file_id":001",
        "filename": "music.mp3",
        "duration": 180.5,
        "order": 0
      }
    ],
    "settings": { ... },
    "latest_render": {
      "job_id": "job_xyz789",
      "status": "completed",
      "output_path": "/output/proj_abc123/final.mp4",
      "created_at": "2026-03-01T12:00:00Z"
    }
  }
}
```

---

### 5.4 更新專案

更新專案資訊、圖片順序或設定。

**端點**: `PUT /api/v1/projects/{project_id}`

**請求體** (部分欄位更新):

```json
{
  "name": "新的專案名稱",
  "description": "更新的描述",
  "images": [
    {
      "id": "img_001",
      "duration": 6.0,
      "order": 0
    },
    {
      "id": "img_002",
      "duration": 4.0,
      "order": 1
    }
  ],
  "settings": {
    "resolution": "4k",
    "fps": 60
  }
}
```

**成功回應** (200):
```json
{
  "success": true,
  "data": {
    "id": "proj_abc123",
    "name": "新的專案名稱",
    "updated_at": "2026-03-01T12:30:00Z",
    ...
  }
}
```

---

### 5.5 刪除專案

刪除專案及其所有關聯資料。

**端點**: `DELETE /api/v1/projects/{project_id}`

**成功回應** (204): No Content

**錯誤回應** (400):
```json
{
  "success": false,
  "error": {
    "code": "RENDER_IN_PROGRESS",
    "message": "無法刪除正在渲染中的專案"
  }
}
```

---

### 5.6 新增圖片到專案

將已上傳的圖片添加到專案。

**端點**: `POST /api/v1/projects/{project_id}/images`

**請求體**:

```json
{
  "file_ids": ["file_img_001", "file_img_002", "file_img_003"],
  "order": 0,
  "duration": 5.0
}
```

**成功回應** (200):
```json
{
  "success": true,
  "data": {
    "added": ["img_001", "img_002", "img_003"],
    "project_images_count": 5
  }
}
```

---

### 5.7 新增音樂到專案

將已上傳的音樂添加到專案。

**端點**: `POST /api/v1/projects/{project_id}/audio`

**請求體**:

```json
{
  "file_ids": ["file_audio_001"],
  "order": 0
}
```

---

### 5.8 移除專案中的圖片

從專案中移除圖片。

**端點**: `DELETE /api/v1/projects/{project_id}/images/{image_id}`

**成功回應** (204): No Content

---

### 5.9 移除專案中的音樂

從專案中移除音樂。

**端點**: `DELETE /api/v1/projects/{project_id}/audio/{audio_id}`

**成功回應** (204): No Content

---

## 6. 渲染任務 (Render)

### 6.1 開始渲染

開始渲染專案影片。

**端點**: `POST /api/v1/render/start`

**請求體**:

```json
{
  "project_id": "proj_abc123"
}
```

**成功回應** (202):
```json
{
  "success": true,
  "data": {
    "job_id": "job_xyz789",
    "project_id": "proj_abc123",
    "status": "queued",
    "estimated_duration": 300,
    "webSocket_url": "ws://localhost:8000/ws/progress/job_xyz789"
  }
}
```

**錯誤回應** (400):
```json
{
  "success": false,
  "error": {
    "code": "INVALID_PROJECT_STATE",
    "message": "專案沒有足夠的圖片進行渲染",
    "details": {
      "images_count": 0,
      "minimum_required": 1
    }
  }
}
```

---

### 6.2 取得渲染狀態

取得渲染任務的當前狀態。

**端點**: `GET /api/v1/render/status/{job_id}`

**路徑參數**:

| 參數 | 類型 | 描述 |
|------|------|------|
| job_id | string | 任務 ID |

**成功回應** (200):
```json
{
  "success": true,
  "data": {
    "job_id": "job_xyz789",
    "project_id": "proj_abc123",
    "status": "rendering",
    "progress": {
      "percentage": 45,
      "current_frame": 1350,
      "total_frames": 3000,
      "fps": 28.5,
      "eta_seconds": 58,
      "stage": "rendering_frames",
      "stage_progress": {
        "current": "處理第 3 張圖片",
        "percentage": 60
      }
    },
    "started_at": "2026-03-01T12:00:00Z",
    "updated_at": "2026-03-01T12:05:00Z"
  }
}
```

---

### 6.3 取消渲染

取消正在進行或排隊中的渲染任務。

**端點**: `DELETE /api/v1/render/cancel/{job_id}`

**成功回應** (200):
```json
{
  "success": true,
  "data": {
    "job_id": "job_xyz789",
    "status": "cancelled"
  }
}
```

**錯誤回應** (400):
```json
{
  "success": false,
  "error": {
    "code": "INVALID_JOB_STATE",
    "message": "任務已完成，無法取消"
  }
}
```

---

### 6.4 取得渲染歷史

取得專案的渲染歷史。

**端點**: `GET /api/v1/render/history/{project_id}`

**成功回應** (200):
```json
{
  "success": true,
  "data": [
    {
      "job_id": "job_001",
      "status": "completed",
      "progress": 100,
      "output_path": "/output/proj_abc123/render_001.mp4",
      "file_size": 15000000,
      "duration": 120.5,
      "created_at": "2026-03-01T12:00:00Z",
      "completed_at": "2026-03-01T12:10:00Z"
    },
    {
      "job_id": "job_002",
      "status": "failed",
      "progress": 45,
      "error": "FFmpeg encoding error",
      "created_at": "2026-03-01T11:00:00Z",
      "failed_at": "2026-03-01T11:05:00Z"
    }
  ]
}
```

---

### 6.5 下載成品影片

下載渲染完成的影片。

**端點**: `GET /api/v1/render/download/{job_id}`

**查詢參數**:

| 參數 | 類型 | 預設值 | 描述 |
|------|------|--------|------|
| quality | string | original | 品質 (original, high, medium, low) |

**回應**: 檔案下載 (video/mp4)

**錯誤回應** (404):
```json
{
  "success": false,
  "error": {
    "code": "OUTPUT_NOT_FOUND",
    "message": "渲染輸出檔案不存在"
  }
}
```

---

### 6.6 預覽幀

取得特定幀的預覽圖。

**端點**: `GET /api/v1/render/preview/{job_id}`

**查詢參數**:

| 參數 | 類型 | 必填 | 描述 |
|------|------|------|------|
| frame | integer | 是 | 幀編號 |

**回應**: 圖片檔案 (image/jpeg)

---

## 7. 設定 (Settings)

### 7.1 取得可用設定選項

取得系統支援的所有設定選項。

**端點**: `GET /api/v1/settings/options`

**成功回應** (200):
```json
{
  "success": true,
  "data": {
    "resolutions": [
      { "value": "720p", "label": "HD (1280x720)", "width": 1280, "height": 720 },
      { "value": "1080p", "label": "Full HD (1920x1080)", "width": 1920, "height": 1080 },
      { "value": "1440p", "label": "QHD (2560x1440)", "width": 2560, "height": 1440 },
      { "value": "4k", "label": "4K (3840x2160)", "width": 3840, "height": 2160 }
    ],
    "frame_rates": [
      { "value": 24, "label": "24 fps (電影)" },
      { "value": 30, "label": "30 fps (標準)" },
      { "value": 60, "label": "60 fps (流暢)" }
    ],
    "output_formats": [
      { "value": "mp4_h264", "label": "MP4 (H.264)", "description": "相容性最佳" },
      { "value": "mp4_h265", "label": "MP4 (H.265/HEVC)", "description": "壓縮率較高" }
    ],
    "encoders": [
      { "value": "h264_nvenc", "label": "NVIDIA H.264", "hardware": true },
      { "value": "h265_nvenc", "label": "NVIDIA H.265", "hardware": true },
      { "value": "libx264", "label": "Software H.264", "hardware": false },
      { "value": "libx265", "label": "Software H.265", "hardware": false }
    ],
    "kenburns_effects": [
      { "value": "pan_left", "label": "向左平移" },
      { "value": "pan_right", "label": "向右平移" },
      { "value": "pan_up", "label": "向上平移" },
      { "value": "pan_down", "label": "向下平移" },
      { "value": "zoom_in", "label": "放大" },
      { "value": "zoom_out", "label": "縮小" },
      { "value": "compose_pan_zoom", "label": "組合 (平移+縮放)", "default": true },
      { "value": "random", "label": "隨機" }
    ],
    "easing_functions": [
      { "value": "linear", "label": "線性" },
      { "value": "ease_in", "label": "緩入" },
      { "value": "ease_out", "label": "緩出" },
      { "value": "ease_in_out", "label": "緩入緩出", "default": true }
    ]
  }
}
```

---

### 7.2 取得系統狀態

取得系統硬體和服務狀態。

**端點**: `GET /api/v1/settings/system`

**成功回應** (200):
```json
{
  "success": true,
  "data": {
    "gpu": {
      "available": true,
      "name": "NVIDIA GeForce RTX 3080",
      "memory_total": 10240,
      "memory_used": 2048,
      "driver_version": "560.35.03",
      "nvenc_available": true
    },
    "storage": {
      "temp_used": 524288000,
      "temp_total": 107374182400,
      "output_used": 1073741824,
      "output_total": 214748364800
    },
    "render_queue": {
      "running": 1,
      "queued": 2,
      "max_concurrent": 3
    },
    "version": {
      "api": "1.0.0",
      "ffmpeg": "6.0",
      "engine": "1.0.0"
    }
  }
}
```

---

### 7.3 驗證專案設定

驗證專案設定是否有效。

**端點**: `POST /api/v1/settings/validate`

**請求體**:

```json
{
  "project_id": "proj_abc123"
}
```

或直接驗證設定：

```json
{
  "settings": {
    "resolution": "4k",
    "fps": 60,
    "images_total_duration": 50,
    "audio_total_duration": 45
  }
}
```

**成功回應** (200):
```json
{
  "success": true,
  "data": {
    "valid": true,
    "warnings": [
      {
        "field": "audio_total_duration",
        "message": "音訊時長短於圖片，影片結尾將會靜音"
      }
    ]
  }
}
```

**錯誤回應** (422):
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "設定驗證失敗",
    "details": {
      "errors": [
        {
          "field": "resolution",
          "message": "4K 解析度需要 GPU 加速，但目前 GPU 不可用"
        }
      ]
    }
  }
}
```

---

## 8. WebSocket 即時通訊

### 8.1 連接進度更新

建立 WebSocket 連接以接收即時渲染進度。

**端點**: `WS /ws/progress/{job_id}`

**連接 URL**:
```
ws://localhost:8000/ws/progress/job_xyz789
```

**連接參數** (Query String):

| 參數 | 類型 | 必填 | 描述 |
|------|------|------|------|
| token | string | 否 | 認證 token |

### 8.2 客戶端 -> 伺服器 訊息

#### 訂閱訊息

```json
{
  "type": "subscribe",
  "job_id": "job_xyz789"
}
```

#### 取消訂閱訊息

```json
{
  "type": "unsubscribe",
  "job_id": "job_xyz789"
}
```

### 8.3 伺服器 -> 客戶端 訊息

#### 連接確認

```json
{
  "type": "connected",
  "data": {
    "job_id": "job_xyz789",
    "message": "已連接到渲染進度服務"
  }
}
```

#### 進度更新

```json
{
  "type": "progress",
  "data": {
    "job_id": "job_xyz789",
    "progress": 45.5,
    "current_frame": 1365,
    "total_frames": 3000,
    "fps": 28.5,
    "eta_seconds": 58,
    "stage": "rendering_frames",
    "stage_label": "渲染幀",
    "stage_percentage": 60,
    "stage_message": "處理第 3 張圖片 / 共 5 張"
  }
}
```

#### 狀態更新

```json
{
  "type": "status",
  "data": {
    "job_id": "job_xyz789",
    "status": "rendering",
    "message": "正在渲染中",
    "timestamp": "2026-03-01T12:05:00Z"
  }
}
```

#### 錯誤訊息

```json
{
  "type": "error",
  "data": {
    "job_id": "job_xyz789",
    "error": "FFmpeg encoding failed",
    "code": "RENDER_FAILED",
    "timestamp": "2026-03-01T12:10:00Z"
  }
}
```

#### 完成訊息

```json
{
  "type": "complete",
  "data": {
    "job_id": "job_xyz789",
    "status": "completed",
    "output_path": "/output/proj_abc123/final.mp4",
    "file_size": 15000000,
    "duration": 120.5,
    "resolution": "1920x1080",
    "fps": 30,
    "timestamp": "2026-03-01T12:10:00Z"
  }
}
```

### 8.4 渲染階段 (RenderStage)

| 階段 | 鍵值 | 標籤 | 預估比重 |
|------|------|------|----------|
| preparing | preparing | 準備階段 | 5% |
| loading_images | loading_images | 載入圖片 | 10% |
| detecting_subjects | detecting_subjects | 偵測主體 | 20% |
| generating_paths | generating_paths | 生成路徑 | 10% |
| processing_audio | processing_audio | 處理音訊 | 15% |
| rendering_frames | rendering_frames | 渲染幀 | 30% |
| encoding_video | encoding_video | 編碼影片 | 8% |
| finalizing | finalizing | 完成階段 | 2% |

### 8.5 任務狀態 (JobStatus)

| 狀態 | 描述 |
|------|------|
| queued | 已排隊 |
| preparing | 準備中 |
| rendering | 渲染中 |
| encoding | 編碼中 |
| completed | 完成 |
| failed | 失敗 |
| cancelled | 已取消 |
| paused | 已暫停 |

---

## 9. 附錄

### 9.1 支援的檔案格式

#### 輸入圖片

| 格式 | MIME Type | 副檔名 |
|------|-----------|--------|
| JPEG | image/jpeg | .jpg, .jpeg |
| PNG | image/png | .png |
| WebP | image/webp | .webp |
| BMP | image/bmp | .bmp |

#### 輸入音訊

| 格式 | MIME Type | 副檔名 |
|------|-----------|--------|
| MP3 | audio/mpeg | .mp3 |
| WAV | audio/wav | .wav |
| AAC | audio/aac | .aac |
| FLAC | audio/flac | .flac |
| OGG | audio/ogg | .ogg |

#### 輸出影片

| 格式 | 副檔名 | 描述 |
|------|--------|------|
| MP4 (H.264) | .mp4 | 相容性最佳 |
| MP4 (H.265) | .mp4 | 壓縮率較高 |

### 9.2 檔案大小限制

| 類型 | 單檔限制 | 說明 |
|------|----------|------|
| 圖片 | 50 MB | 建議解析度不超過 8K |
| 音訊 | 100 MB | - |
| 輸出影片 | 無限制 | 取決於硬碟空間 |

### 9.3 數量限制

| 類型 | 最大數量 |
|------|----------|
| 每專案圖片 | 50 張 |
| 每專案音訊 | 10 首 |
| 同時渲染任務 | 3 個 |
| 每小時請求數 | 1000 次 |

### 9.4 OpenAPI/Swagger 文件

API 文件可透過以下網址存取：

```
http://localhost:8000/docs
```

或取得 OpenAPI JSON：

```
http://localhost:8000/openapi.json
```

---

**文件結束**

*本 API 規格書定義了自動化 Ken-Burns 影片生成系統的完整 RESTful API 介面。所有實作應遵循此規格書進行開發。*
