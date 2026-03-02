# 自動化 Ken-Burns 影片生成系統 - 技術規格書 (SPEC.md)

**文件版本**: 1.0
**更新日期**: 2026-03-01
**作者**: Coder-Plan (技術架構師)
**專案名稱**: Auto-KenBurns Video Generator

---

## 1. 專案概述 (Project Overview)

本專案旨在開發一款應用程式，能夠將使用者輸入的圖片與音樂，自動串接並生成帶有流暢 Ken-Burns 特效（平移與縮放）的影片。系統將利用電腦視覺技術確保圖片主體（如人物頭部）不被裁切，並透過硬體加速（CUDA/GPU）結合 FFmpeg 提供高效的影片輸出。

為追求極致的用戶體驗與介面現代化，本專案採用 Web 技術建構前端 UI，並與 Python 後端引擎深度整合。

---

## 2. 系統架構圖 (System Architecture)

```
+--------------------------------------------------------------------------------------+
|                                SYSTEM ARCHITECTURE                                   |
+--------------------------------------------------------------------------------------+

    +------------------+                         +------------------+
    |   Client Layer   |                         |   Client Layer   |
    |                  |                         |                  |
    |  +------------+  |      WebSocket         |  +------------+  |
    |  |  Vue 3 UI  |◄─┼──────────────►─────────┤►│  Progress  |  |
    |  +------------+  │      HTTP/REST         |  +------------+  |
    |  |  Tailwind  |  |                         |  +------------+  |
    |  +------------+  |                         |                  |
    +--------+---------+                         +--------^---------+
             |                                           |
             | REST API                                  | WebSocket
             v                                           |
    +--------+---------+                         +--------+---------+
    |                 |                         |                 |
    |  +-----------+  |                         |  +-----------+  |
    |  | FastAPI   |  |                         |  |  Task     |  |
    |  |  Server   |  |                         |  |  Manager  |  |
    |  +-----------+  |                         |  +-----------+  |
    |        |        |                         |        |        |
    +--------+---------+                         +--------+---------+
             |                                           |
             v                                           v
    +------------------------------------------------------------------+
    |                        BACKEND SERVICES                          |
    +------------------------------------------------------------------+
    |                                                                   |
    |  +---------------+  +---------------+  +-------------------+     |
    |  |   API Layer   |  |  WebSocket    |  |   Task Queue     |     |
    |  |  (REST API)   |  |  Handler      |  |   (Background)   |     |
    |  +---------------+  +---------------+  +-------------------+     |
    |                                                                   |
    |  +---------------+  +---------------+  +-------------------+     |
    |  |  File Upload  |  |   Session     |  |   Job Status     |     |
    |  |   Service     |  |   Manager     |  |   Tracker        |     |
    |  +---------------+  +---------------+  +-------------------+     |
    |                                                                   |
    +------------------------------------------------------------------+
                                    |
                                    v
    +------------------------------------------------------------------+
    |                      CORE ENGINE LAYER                           |
    +------------------------------------------------------------------+
    |                                                                   |
    |  +---------------+  +---------------+  +-------------------+     |
    |  |   Image       |  |   Audio       |  |   Video          |     |
    |  |   Analyzer    |  |   Processor   |  |   Renderer       |     |
    |  |  (OpenCV/     |  |  (FFmpeg/     |  |  (FFmpeg +       |     |
    |  |   YOLO)       |  |   Librosa)    |  |   NVENC)         |     |
    |  +---------------+  +---------------+  +-------------------+     |
    |                                                                   |
    |  +---------------+  +---------------+  +-------------------+     |
    |  |   Ken-Burns  |  |   Subject    |  |   Hardware       |     |
    |  |   Generator  |  |   Detector    |  |   Accelerator    |     |
    |  +---------------+  +---------------+  +-------------------+     |
    |                                                                   |
    +------------------------------------------------------------------+
                                    |
                                    v
    +------------------------------------------------------------------+
    |                        DATA LAYER                                |
    +------------------------------------------------------------------+
    |                                                                   |
    |  +---------------+  +---------------+  +-------------------+     |
    |  |    Input      |  |   Working     |  |   Output         |     |
    |  |    Storage    |  |   Directory   |  |   Storage        |     |
    |  +---------------+  +---------------+  +-------------------+     |
    |                                                                   |
    +------------------------------------------------------------------+

    +------------------------------------------------------------------+
    |                     INFRASTRUCTURE LAYER                         |
    +------------------------------------------------------------------+
    |                                                                   |
    |  [ GPU / CUDA ]  [  SQLite/Redis  ]  [  File System  ]           |
    |                                                                   |
    +------------------------------------------------------------------+
```

---

## 3. 模組劃分 (Module Breakdown)

### 3.1 前端模組 (Frontend Modules)

```
frontend/
├── src/
│   ├── components/
│   │   ├── upload/
│   │   │   ├── ImageUploader.vue      # 圖片上傳元件
│   │   │   ├── AudioUploader.vue      # 音訊上傳元件
│   │   │   └── DragDropZone.vue       # 拖曳上傳區域
│   │   ├── preview/
│   │   │   ├── MediaPreview.vue       # 媒體預覽元件
│   │   │   ├── ImageCard.vue          # 圖片卡片
│   │   │   └── AudioCard.vue          # 音訊卡片
│   │   ├── player/
│   │   │   └── VideoPlayer.vue        # 影片播放器
│   │   ├── progress/
│   │   │   ├── ProgressBar.vue        # 進度條
│   │   │   └── StatusIndicator.vue    # 狀態指示器
│   │   └── settings/
│   │       ├── OutputSettings.vue     # 輸出設定
│   │       └── EffectSettings.vue     # 特效設定
│   │
│   ├── pages/
│   │   ├── HomePage.vue               # 首頁/主頁面
│   │   ├── EditorPage.vue             # 編輯器頁面
│   │   └── ResultPage.vue             # 結果頁面
│   │
│   ├── composables/
│   │   ├── useWebSocket.js            # WebSocket 鉤子
│   │   ├── useUpload.js               # 上傳邏輯
│   │   ├── useVideoGeneration.js      # 影片生成邏輯
│   │   └── useProgress.js             # 進度追蹤
│   │
│   ├── stores/
│   │   ├── projectStore.js            # 專案狀態管理
│   │   ├── settingsStore.js           # 設定狀態管理
│   │   └── progressStore.js           # 進度狀態管理
│   │
│   ├── services/
│   │   ├── api.js                     # API 客戶端
│   │   └── websocket.js               # WebSocket 客戶端
│   │
│   └── styles/
│       ├── main.css                   # 主樣式
│       └── variables.css              # CSS 變數
```

### 3.2 後端模組 (Backend Modules)

```
backend/
├── app/
│   ├── main.py                        # FastAPI 應用入口
│   ├── config.py                      # 配置文件
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── upload.py              # 上傳路由
│   │   │   ├── project.py             # 專案路由
│   │   │   ├── render.py              # 渲染路由
│   │   │   └── settings.py            # 設定路由
│   │   └── websocket/
│   │       └── progress.py            # WebSocket 進度處理
│   │
│   ├── core/
│   │   ├── engine/
│   │   │   ├── kenburns.py            # Ken-Burns 特效生成器
│   │   │   ├── subject_detector.py    # 主體偵測
│   │   │   ├── path_calculator.py     # 路徑計算
│   │   │   └── renderer.py            # 影片渲染器
│   │   │
│   │   ├── audio/
│   │   │   ├── normalizer.py          # 音訊正規化
│   │   │   ├── crossfade.py           # 交叉淡化
│   │   │   └── beat_detector.py       # 節拍偵測
│   │   │
│   │   ├── video/
│   │   │   ├── ffmpeg_wrapper.py      # FFmpeg 包裝器
│   │   │   ├── hardware_accel.py      # 硬體加速
│   │   │   └── output_builder.py      # 輸出建構器
│   │   │
│   │   └── utils/
│   │       ├── file_manager.py        # 檔案管理
│   │       └── validators.py          # 驗證工具
│   │
│   ├── models/
│   │   ├── schemas/
│   │   │   ├── project.py             # 專案資料模型
│   │   │   ├── settings.py            # 設定資料模型
│   │   │   └── response.py            # 回應資料模型
│   │   └── database.py                # 資料庫連接
│   │
│   ├── services/
│   │   ├── task_manager.py            # 任務管理
│   │   ├── session_manager.py         # 會話管理
│   │   └── progress_tracker.py        # 進度追蹤
│   │
│   └── utils/
│       ├── logger.py                  # 日誌工具
│       └── exceptions.py              # 自訂異常
│
└── tests/
```

---

## 4. 技術選型細節 (Technical Selection Details)

### 4.1 前端技術堆疊

| 技術 | 版本 | 用途 | 選擇理由 |
|------|------|------|----------|
| **Vite** | ^5.0 | 建置工具 | 快速的開發伺服器與優化的生產構建 |
| **Vue 3** | ^3.4 | 響應式框架 | Composition API 提供更好的邏輯複用 |
| **Tailwind CSS** | ^3.4 | CSS 框架 |  Utility-first，支援深色主題，易於自定義 |
| **Pinia** | ^2.1 | 狀態管理 | 官方推薦的 Vue 3 狀態管理庫 |
| **Vue Router** | ^4.2 | 路由管理 | SPA 導航 |
| **Socket.io Client** | ^4.7 | WebSocket 客戶端 | 穩定的雙向通訊 |

### 4.2 後端技術堆疊

| 技術 | 版本 | 用途 | 選擇理由 |
|------|------|------|----------|
| **Python** | 3.10+ | 執行環境 | 強大的影像處理生態系 |
| **FastAPI** | ^0.109 | Web 框架 | 高效能，自動 API 文件生成 |
| **Uvicorn** | ^0.27 | ASGI 伺服器 | 高效能非同步伺服器 |
| **Pydantic** | ^2.5 | 資料驗證 | 強型別驗證，自動生成文件 |
| **python-multipart** | ^0.0.6 | 檔案上傳 | FastAPI 檔案上傳依賴 |
| **aiofiles** | ^23.2 | 非同步檔案 IO | 异步檔案處理 |
| **joblib** | ^1.3 | 背景任務 | 輕量級背景任務管理 |

### 4.3 影像處理技術

| 技術 | 版本 | 用途 | 選擇理由 |
|------|------|------|----------|
| **OpenCV** | ^4.9 | 影像處理 | 完整的電腦視覺庫 |
| **NumPy** | ^1.26 | 數值計算 | 高效矩陣運算 |
| **Pillow** | ^10.2 | 圖片處理 | Python Imaging Library |
| **mediapipe** | ^0.10 | 人體偵測 | Google 的高效能人體姿態偵測 |
| **ultralytics** | ^8.1 | YOLO 偵測 | 先進的物體偵測模型 |

### 4.4 影音處理技術

| 技術 | 版本 | 用途 | 選擇理由 |
|------|------|------|----------|
| **FFmpeg** | 6.0+ | 影片處理 | 業界標準影音處理工具 |
| **pydub** | ^0.25 | 音訊處理 | 簡化的音訊操作介面 |
| **librosa** | ^0.10 | 音訊分析 | 強大的音訊分析庫 |

### 4.5 硬體加速技術

| 技術 | 版本 | 用途 | 選擇理由 |
|------|------|------|----------|
| **CUDA** | 12.x | GPU 運算 | NVIDIA GPU 加速 |
| **FFmpeg NVENC** | - | 硬體編碼 | NVIDIA 硬體編碼加速 |

---

## 5. 資料流程 (Data Flow)

### 5.1 完整資料流程圖

```
+---------------------------------------------------------------------------------------+
|                              COMPLETE DATA FLOW                                       |
+---------------------------------------------------------------------------------------+

    [1. UPLOAD]                    [2. PROCESS]                   [3. RENDER]
    +-----------+                 +------------+                 +-----------+
    |  Client   |                 |   Backend  |                 |   GPU/    |
    |           |                 |            |                 |  FFmpeg   |
    +---+---+---+                 +-----+------+                 +-----+-----+
        | | |                         | | |                           |
        | | |  HTTP POST              | | |                           |
        | | └────────────────────────►| | |                           |
        | |                           | | |  Validate Files           |
        | |                           | ▼ |                           |
        | |                    +------+------+                       |
        | |                    |   Upload   |                       |
        │ │                    |   Service  |                       |
        │ │                    +------+------+                       │
        │ |                           |                              |
        │ │  File ID                  | Save to temp                 |
        │ │◄──────────────────────────┘                              |
        │ |                                                            |
        │ │  HTTP POST /api/render                                   │
        │ │  +------------------+                                     |
        │ └─►|  Render Request  |                                     |
        │ │  +--------+---------+                                     |
        │ │           |                                                │
        │ │           | Create Job                                    |
        │ │           ▼                                                |
        │ │  +------------------+                                     │
        │ │  |  Task Manager    |──── Background Task                |
        │ │  +--------+---------+         Starts                     |
        │ │           |                                                │
        │ │           │ Job ID                                        │
        │ │           ▼                                                |
        │ │  +------------------+    WebSocket    +-----------------+ |
        │ │  │  WebSocket       │◄──────────────►|  Progress       | │
        │ │  │  Connection      │    Real-time    |  Updates        | │
        │ │  +------------------+                 +-----------------+ │
        │ │                                                            │
        │ │                           [INTERNAL PROCESSING]            │
        │ │                                                            │
        │ │  +------------+  +------------+  +-------------------+     │
        │ │  │   Image    │  │   Audio    │  │   Ken-Burns      │     │
        │ │  │   Loader   │─►│  Normalizer│─►│   Generator      │     │
        │ │  +------------+  +------------+  +--------+----------+     │
        │ │                                              |              │
        │ │                                              ▼              │
        │ │                    +----------------+  +--------+----------+ │
        │ │                    │ Subject        │  │   Path         │ │
        │ │                    │ Detector       │─►│   Calculator   │ │
        │ │                    │ (YOLO)         │  +-----------------+ │
        │ │                    +----------------+                        │
        │ │                                                            │
        │ │                                              ▼              │
        │ │                                    +-------------------+     │
        │ │                                    │  Video Renderer  │     │
        │ │                                    │  (FFmpeg + CUDA) │     │
        │ │                                    +--------+----------+     │
        │ │                                             │                  │
        │ │                                             │ Progress         │
        │ │                                             │ (0-100%)        │
        │ │                                             │                  │
        │ │◄────────────────────────────────────────────┘                  │
        │ |                                                            │
        │ │  HTTP GET /api/download/{job_id}                           │
        │ │  +------------------+                                       │
        │ └─►|  Download        │◄──── Output Video File                │
        │     |  Service         |                                       |
        │     +------------------+                                       |
        |                                                              |
        └──────────────────────────────────────────────────────────────┘
```

### 5.2 API 端點設計

#### 5.2.1 上傳 API

| 方法 | 路徑 | 描述 | 請求格式 |
|------|------|------|----------|
| POST | `/api/upload/image` | 上傳圖片 | `multipart/form-data` |
| POST | `/api/upload/audio` | 上傳音訊 | `multipart/form-data` |
| GET | `/api/upload/{file_id}` | 取得上傳的檔案 | - |

#### 5.2.2 專案 API

| 方法 | 路徑 | 描述 |
|------|------|------|
| POST | `/api/project/create` | 建立新專案 |
| GET | `/api/project/{project_id}` | 取得專案詳情 |
| PUT | `/api/project/{project_id}` | 更新專案 |
| DELETE | `/api/project/{project_id}` | 刪除專案 |
| GET | `/api/project/list` | 列出所有專案 |

#### 5.2.3 渲染 API

| 方法 | 路徑 | 描述 |
|------|------|------|
| POST | `/api/render/start` | 開始渲染 |
| GET | `/api/render/status/{job_id}` | 取得渲染狀態 |
| DELETE | `/api/render/cancel/{job_id}` | 取消渲染 |
| GET | `/api/render/download/{job_id}` | 下載完成的影片 |

#### 5.2.4 WebSocket 端點

| 方法 | 路徑 | 描述 |
|------|------|------|
| WS | `/ws/progress/{job_id}` | 即時渲染進度 |

### 5.3 資料模型

#### 5.3.1 專案 (Project)

```python
class Project(BaseModel):
    id: str                           # UUID
    name: str                         # 專案名稱
    created_at: datetime              # 建立時間
    updated_at: datetime              # 更新時間
    images: List[ImageAsset]          # 圖片列表
    audio: List[AudioAsset]           # 音訊列表
    settings: RenderSettings          # 渲染設定
    status: ProjectStatus             # 專案狀態
```

#### 5.3.2 圖片資產 (ImageAsset)

```python
class ImageAsset(BaseModel):
    id: str                           # UUID
    file_id: str                      # 檔案 ID
    filename: str                     # 檔案名稱
    width: int                        # 寬度
    height: int                        # 高度
    duration: float                   # 顯示時長(秒)
    subject_regions: List[Region]     # 主體區域
```

#### 5.3.3 音訊資產 (AudioAsset)

```python
class AudioAsset(BaseModel):
    id: str                           # UUID
    file_id: str                      # 檔案 ID
    filename: str                     # 檔案名稱
    duration: float                   # 時長(秒)
    sample_rate: int                  # 取樣率
    loudness: float                   # 響度(LUFS)
```

#### 5.3.4 渲染設定 (RenderSettings)

```python
class RenderSettings(BaseModel):
    output_format: OutputFormat       # 輸出格式 (mp4_h264, mp4_h265)
    resolution: Resolution            # 解析度 (1080p, 4k)
    fps: int                          # 幀率 (30, 60)
    video_bitrate: int                # 影片位元率
    audio_bitrate: int                # 音訊位元率
    kenburns: KenBurnsSettings        # Ken-Burns 特效設定
    audio_fade: AudioFadeSettings     # 音訊淡入淡出設定
```

---

## 6. 核心功能模組詳細設計

### 6.1 Ken-Burns 特效生成器 (BPM驅動版)

> **重要更新**：本系統支援自動根據音樂BPM持續調整Ken-Burns動作，無需手動選擇效果。

#### 6.1.1 核心概念

```
圖片時長內持續動作切換：
┌─────────────────────────────────────────────────────────────┐
│  [圖片] ─────────────────────────────────────────────────►   │
│         │          │          │          │          │      │
│      動作1      動作2      動作3      動作4      動作5     │
│    (放大)     (左移)    (縮小)     (右上)     (右下)       │
│      │          │          │          │          │      │
│   ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐       │
│   │淡入   │  │      │  │      │  │      │  │淡出   │       │
│   └──────┘  └──────┘  └──────┘  └──────┘  └──────┘       │
│                                                             │
│  根據BPM自動計算動作切換間隔                                  │
│  - 低BPM (<80): 2-4拍 = 1.5-3秒                             │
│  - 中BPM (80-140): 2-3拍 = 1-2秒                           │
│  - 高BPM (>140): 1-2拍 = 0.5-1秒                           │
└─────────────────────────────────────────────────────────────┘
```

#### 6.1.2 支援的動作類型

| 類型 | 描述 | 範例 |
|------|------|------|
| ZOOM_IN | 放大 | 聚焦主體 |
| ZOOM_OUT | 縮小 | 展示環境 |
| PAN_LEFT | 向左平移 | 視線引導 |
| PAN_RIGHT | 向右平移 | 視線引導 |
| PAN_UP | 向上平移 | 建築攝影 |
| PAN_DOWN | 向下平移 | 建築攝影 |
| DIAGONAL_* | 對角線移動 | 動態感 |
| ROTATE_CW/CCW | 旋轉 | 特殊效果 |
| COMPOSE | 組合動作 | 預設 |

#### 6.1.3 BPM分析與動作同步

```python
class BPMAnalysis:
    """音樂BPM分析結果"""
    bpm: float                    # BPM值
    beat_duration: float          # 每拍持續時間(秒)
    onset_times: List[float]     # 節拍時間點

class EffectSegment:
    """單一動作片段"""
    effect_type: EffectType
    start_time: float
    end_time: float
    start_zoom: float
    end_zoom: float
    start_x, end_x: float        # 平移座標
    start_y, end_y: float

class ImageSegment:
    """圖片片段（包含持續的Ken-Burns動作）"""
    image_path: str
    start_time: float
    end_time: float
    fade_in_duration: float = 0.5   # 淡入時間
    fade_out_duration: float = 0.5  # 淡出時間
    effects: List[EffectSegment]
```

#### 6.1.4 動作切換邏輯

1. **BPM分析**：使用Librosa分析音樂，取得BPM和節拍點
2. **持續生成**：根據BPM計算動作切換間隔
3. **隨機多樣**：每次選擇不同效果類型，避免重複
4. **淡入淡出**：每張圖片開始淡入、結束淡出

#### 6.1.5 緩動函數

```python
class EasingFunctions:
    LINEAR = "linear"              # 線性
    EASE_IN = "easeIn"             # 緩入
    EASE_OUT = "easeOut"           # 緩出
    EASE_IN_OUT = "easeInOut"      # 緩入緩出 (預設)
```

#### 6.1.6 動漫人物專屬優化

- **主體偵測**：使用YOLO/MediaPipe偵測動漫人物
- **頭部保護**：頭部區域額外保留25%邊界
- **安全區計算**：優先保護臉部和身體核心區域

### 6.2 主體偵測模組

#### 6.2.1 架構

```
SubjectDetector
├── YOLODetector          # YOLO 物體偵測
├── MediaPipePose         # MediaPipe 姿態偵測
├── FaceDetector          # 人臉偵測
└── SafeZoneCalculator    # 安全區計算
```

#### 6.2.2 安全區計算

```python
class SafeZone:
    """
    安全區域 - 主體必須在此區域內
    """
    margin_x: float      # 水平邊距 (比例)
    margin_y: float      # 垂直邊距 (比例)
    min_head_space: float  # 頭部上方最小空間

class Region:
    """
    偵測到的區域
    """
    type: RegionType     # REGION_PERSON, REGION_FACE, REGION_OBJECT
    bounds: BoundingBox   # 邊界框
    confidence: float    # 置信度
    priority: int        # 優先級
```

#### 6.2.3 偵測流程

1. **載入圖片** - 讀取輸入圖片
2. **YOLO 偵測** - 偵測人物和重要物體
3. **姿態偵測** (可選) - 使用 MediaPipe 取得詳細人體姿態
4. **安全區計算** - 根據偵測結果計算安全區域
5. **Viewport 調整** - 確保 Ken-Burns 路徑在安全區內

### 6.3 音訊處理模組

#### 6.3.1 架構

```
AudioProcessor
├── Normalizer            # 音量正規化
├── CrossfadeManager      # 交叉淡化
├── BeatDetector          # 節拍偵測 (進階)
└── AudioMixer            # 音訊混音
```

#### 6.3.2 音量正規化

```python
class AudioNormalizer:
    """
    音訊正規化 - 符合 EBU R128 標準
    """
    def normalize(self, audio_path: str, target_lufs: float = -14.0) -> str:
        """
        正規化音訊

        Args:
            audio_path: 輸入音訊路徑
            target_lufs: 目標響度 (LUFS)

        Returns:
            正規化後的音訊路徑
        """
```

#### 6.3.3 交叉淡化

```python
class CrossfadeManager:
    """
    交叉淡化管理
    """
    def add_crossfade(
        self,
        audio_files: List[str],
        fade_duration: float = 2.0,
        crossfade_type: CrossfadeType = CrossfadeType.EQUAL_POWER
    ) -> str:
        """
        添加交叉淡化

        Args:
            audio_files: 音訊檔案列表
            fade_duration: 淡入淡出時長
            crossfade_type: 交叉淡化類型

        Returns:
            合併後的音訊路徑
        """
```

### 6.4 影片渲染模組

#### 6.4.1 架構

```
VideoRenderer
├── FFmpegWrapper         # FFmpeg 包裝
├── HardwareAccelerator   # 硬體加速
├── FrameGenerator        # 幀生成器
├── ProgressReporter      # 進度回報
└── OutputBuilder         # 輸出建構
```

#### 6.4.2 硬體加速檢測

```python
class HardwareAccelerator:
    """
    硬體加速管理器
    """
    def detect_gpu(self) -> GPUInfo:
        """偵測 GPU"""
        # 檢查 CUDA
        # 檢查 NVENC 支援
        # 回傳 GPU 資訊

    def get_encoder(self) -> str:
        """取得最佳編碼器"""
        if self.cuda_available:
            return "hevc_nvenc"  # H.265 NVENC
        else:
            return "libx265"     # Software encoding
```

#### 6.4.3 FFmpeg 指令範例

```bash
# 使用 NVENC 硬體加速
ffmpeg -y \
  -hwaccel cuda \
  -i input.mp4 \
  -c:v h264_nvenc \
  -preset p7 \
  -cq 23 \
  -c:a aac \
  -b:a 192k \
  output.mp4

# Ken-Burns 濾鏡
ffmpeg -y \
  -loop 1 -i input.jpg \
  -vf "zoompan=z='min(zoom+0.001,1.5)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080" \
  -t 5 \
  -c:v libx264 \
  output.mp4
```

---

## 7. WebSocket 即時進度回報

### 7.1 WebSocket 訊息格式

#### 7.1.1 伺服器 -> 客戶端

```typescript
// 進度更新
interface ProgressMessage {
  type: 'progress';
  data: {
    job_id: string;
    progress: number;        // 0-100
    current_frame: number;
    total_frames: number;
    fps: number;
    eta_seconds: number;
    stage: RenderStage;
  };
}

// 狀態更新
interface StatusMessage {
  type: 'status';
  data: {
    job_id: string;
    status: JobStatus;
    message: string;
    error?: string;
  };
}

// 完成訊息
interface CompleteMessage {
  type: 'complete';
  data: {
    job_id: string;
    output_path: string;
    file_size: number;
    duration: number;
  };
}
```

#### 7.1.2 客戶端 -> 伺服器

```typescript
// 訂閱進度
interface SubscribeMessage {
  type: 'subscribe';
  job_id: string;
}

// 取消訂閱
interface UnsubscribeMessage {
  type: 'unsubscribe';
  job_id: string;
}
```

### 7.2 渲染階段 (RenderStage)

| 階段 | 描述 | 預估時間比重 |
|------|------|--------------|
| PREPARING | 準備階段 | 5% |
| LOADING_IMAGES | 載入圖片 | 10% |
| DETECTING_SUBJECTS | 偵測主體 | 20% |
| GENERATING_PATHS | 生成路徑 | 10% |
| PROCESSING_AUDIO | 處理音訊 | 15% |
| RENDERING_FRAMES | 渲染幀 | 30% |
| ENCODING_VIDEO | 編碼影片 | 8% |
| FINALIZING | 完成階段 | 2% |

---

## 8. 錯誤處理策略 (Error Handling Strategy)

### 8.1 錯誤分類

#### 8.1.1 客戶端錯誤 (4xx)

| 錯誤碼 | 錯誤類型 | 描述 | 處理方式 |
|--------|----------|------|----------|
| 400 | Bad Request | 請求格式錯誤 | 回傳正確格式範例 |
| 401 | Unauthorized | 未授權 | 重新登入 |
| 403 | Forbidden | 權限不足 | 提示權限不足 |
| 404 | Not Found | 資源不存在 | 顯示資源不存在 |
| 413 | Payload Too Large | 檔案過大 | 提示檔案大小限制 |
| 422 | Validation Error | 驗證錯誤 | 回傳驗證錯誤詳細資訊 |
| 429 | Too Many Requests | 請求過多 | 限流提示 |

#### 8.1.2 伺服器端錯誤 (5xx)

| 錯誤碼 | 錯誤類型 | 描述 | 處理方式 |
|--------|----------|------|----------|
| 500 | Internal Error | 內部錯誤 | 記錄日誌，回傳錯誤 ID |
| 502 | Bad Gateway | 閘道錯誤 | 重試機制 |
| 503 | Service Unavailable | 服務不可用 | 排隊/重試 |
| 504 | Gateway Timeout | 閘道超時 | 重試處理 |

#### 8.1.3 業務邏輯錯誤

| 錯誤碼 | 錯誤類型 | 描述 | 處理方式 |
|--------|----------|------|----------|
| 1001 | InvalidFileType | 不支援的檔案類型 | 回傳支援的格式列表 |
| 1002 | FileCorrupted | 檔案損壞 | 提示重新上傳 |
| 1003 | InsufficientStorage | 儲存空間不足 | 提示清理空間 |
| 1004 | GpuNotAvailable | GPU 不可用 | 自動切換軟體編碼 |
| 1005 | RenderFailed | 渲染失敗 | 回傳詳細錯誤日誌 |
| 1006 | AudioProcessingFailed | 音訊處理失敗 | 回傳失敗原因 |

### 8.2 異常處理架構

```python
# backend/app/utils/exceptions.py

class KenBurnsException(Exception):
    """基礎異常類"""
    code: str
    status_code: int = 500

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class FileTypeException(KenBurnsException):
    """檔案類型錯誤"""
    code = "INVALID_FILE_TYPE"
    status_code = 400

class RenderException(KenBurnsException):
    """渲染錯誤"""
    code = "RENDER_FAILED"
    status_code = 500

class GpuException(KenBurnsException):
    """GPU 錯誤"""
    code = "GPU_NOT_AVAILABLE"
    status_code = 503
```

### 8.3 全域異常處理

```python
# backend/app/main.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(KenBurnsException)
async def kenburns_exception_handler(request: Request, exc: KenBurnsException):
    """KenBurns 自訂異常處理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": get_request_id()  # 用於追蹤
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """一般異常處理"""
    # 記錄詳細日誌
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "request_id": get_request_id()  # 用於追蹤
            }
        }
    )
```

### 8.4 重試機制

```python
# 檔案上傳重試
MAX_UPLOAD_RETRIES = 3
UPLOAD_RETRY_DELAY = 1  # 秒

# 渲染任務重試
MAX_RENDER_RETRIES = 2
RENDER_RETRY_DELAY = 5  # 秒

# GPU 回退邏輯
GPU_FALLBACK_CHAIN = [
    "hevc_nvenc",     # H.265 NVENC
    "h264_nvenc",     # H.264 NVENC
    "hevc_qsv",       # Intel Quick Sync
    "libx265",        # Software x265
    "libx264"         # Software x264
]
```

### 8.5 日誌記錄策略

```python
# 日誌級別
LOG_LEVELS = {
    "DEBUG": 10,    # 詳細除錯資訊
    "INFO": 20,     # 一般資訊
    "WARNING": 30,  # 警告
    "ERROR": 40,    # 錯誤
    "CRITICAL": 50  # 嚴重錯誤
}

# 日誌格式
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# 敏感資訊過濾
SENSITIVE_FIELDS = ["password", "token", "api_key", "secret"]
```

---

## 9. 前端 UI 設計規範

### 9.1 深色主題配色

```css
:root {
  /* 背景色 */
  --bg-primary: #0f172a;      /* slate-950 */
  --bg-secondary: #1e293b;    /* slate-800 */
  --bg-tertiary: #334155;     /* slate-700 */

  /* 文字色 */
  --text-primary: #f1f5f9;    /* slate-100 */
  --text-secondary: #cbd5e1;  /* slate-300 */
  --text-muted: #94a3b8;      /* slate-400 */

  /* 強調色 */
  --accent-primary: #3b82f6; /* blue-500 */
  --accent-secondary: #8b5cf6; /* violet-500 */
  --accent-gradient: linear-gradient(135deg, #3b82f6, #8b5cf6);

  /* 狀態色 */
  --success: #22c55e;        /* green-500 */
  --warning: #f59e0b;        /* amber-500 */
  --error: #ef4444;          /* red-500 */
  --info: #06b6d4;           /* cyan-500 */
}
```

### 9.2 元件樣式範例

#### 拖曳上傳區域

```html
<div class="
  border-2 border-dashed border-slate-600
  rounded-2xl p-10
  bg-slate-900/50
  hover:bg-slate-800/50 hover:border-blue-500
  transition-all duration-300
  cursor-pointer
  text-center
">
  <IconUpload class="w-12 h-12 text-slate-400 mx-auto mb-4" />
  <p class="text-slate-300">拖曳檔案至此處 或 點擊上傳</p>
  <p class="text-slate-500 text-sm mt-2">支援 JPG, PNG 圖片 / MP3, WAV, AAC 音訊</p>
</div>
```

#### 進度條

```html
<div class="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
  <div class="
    h-full rounded-full
    bg-gradient-to-r from-blue-500 via-violet-500 to-pink-500
    transition-all duration-500 ease-out
  " :style="{ width: progress + '%' }"></div>
</div>
```

#### 主要按鈕

```html
<button class="
  bg-blue-600 hover:bg-blue-500
  text-white font-semibold
  py-3 px-6 rounded-xl
  transform hover:scale-105 active:scale-95
  transition-all duration-200
  shadow-lg hover:shadow-xl
">
  開始生成影片
</button>
```

---

## 10. 部署架構 (Deployment Architecture)

### 10.1 開發環境

```
[Client] <--HTTP/WS--> [FastAPI (localhost:8000)]
```

### 10.2 生產環境

```
                                    +------------------+
                                    |    Load          |
                                    |    Balancer      |
                                    +--------+---------+
                                             |
          +----------------------------------+----------------------------------+
          |                                  |                                  |
          v                                  v                                  v
   +-------------+                    +-------------+                    +-------------+
   |  Worker 1  |                    |  Worker 2  |                    |  Worker N  |
   |  +---------+                   |  +---------+                   |  +---------+|
   |  |FastAPI |                   |  |FastAPI |                   |  |FastAPI ||
   |  +---------+                   |  +---------+                   |  +---------+|
   |  +---------+                   |  +---------+                   |  +---------+|
   |  |FFmpeg  |                   |  |FFmpeg  |                   |  |FFmpeg  ||
   |  +---------+                   |  +---------+                   |  +---------+|
   +-------------+                   +-------------+                   +-------------+
          |                                  |                                  |
          +----------------------------------+----------------------------------+
                                             |
                                   +---------+---------+
                                   |    GPU Cluster   |
                                   |    (CUDA/NVENC)  |
                                   +---------+---------+
                                             |
                                   +---------+---------+
                                   |    Storage       |
                                   |    (NAS/S3)      |
                                   +------------------+
```

---

## 11. 安全性考量 (Security Considerations)

### 11.1 檔案安全

- 檔案類型驗證 (魔數檢查)
- 檔案大小限制
- 檔案名稱 sanitization
- 惡意指令注入防護

### 11.2 API 安全

- Rate limiting
- Request validation
- CORS 設定
- HTTPS/TLS 加密

### 11.3 資源限制

- 單次最大圖片數量
- 單次最大總時長
- 並發渲染任務限制
- 儲存空間配額

---

## 12. 附錄 (Appendix)

### 12.1 環境變數

```bash
# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
MAX_UPLOAD_SIZE=100MB
MAX_IMAGES=50
MAX_AUDIO_TRACKS=10
CUDA_ENABLED=true

# Storage
TEMP_DIR=/tmp/kenburns
OUTPUT_DIR=/var/kenburns/output

# FFmpeg
FFMPEG_PATH=/usr/bin/ffmpeg
NVENC_PRESET=p7
```

### 12.2 效能基準

| 項目 | 目標值 |
|------|--------|
| 圖片載入 | < 100ms/張 |
| 主體偵測 | < 500ms/張 |
| 路徑計算 | < 50ms/張 |
| 1080p 30fps 渲染 | < 5 分鐘/分鐘影片 |
| 4K 60fps 渲染 | < 15 分鐘/分鐘影片 |

### 12.3 支援的格式

| 類型 | 支援格式 |
|------|----------|
| 輸入圖片 | JPEG, PNG, WebP, BMP |
| 輸入音訊 | MP3, WAV, AAC, FLAC, OGG |
| 輸出影片 | MP4 (H.264), MP4 (H.265) |
| 輸出解析度 | 720p, 1080p, 1440p, 4K |
| 輸出幀率 | 24fps, 30fps, 60fps |

---

**文件結束**

*本技術規格書定義了自動化 Ken-Burns 影片生成系統的完整技術架構與實作細節。所有實作應遵循此規格書進行開發。*
