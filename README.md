# Auto-KenBurns 影片生成系統

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green?logo=fastapi)
![Vue 3](https://img.shields.io/badge/Vue-3+-42b883?logo=vue.js)
![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178c6?logo=typescript)
![Tests](https://img.shields.io/badge/Tests-108%20passed-green)
![Coverage](https://img.shields.io/badge/Coverage-70%25-yellow)

## 專案概述

自動生成 Ken-Burns 特效影片的 Web 應用程式。將圖片與音樂自動串接，生成帶有流暢平移與縮放效果的影片。專為動漫人物圖片與 YouTube 音樂頻道影片設計。

## 功能特色

- 圖片拖曳上傳（支援 JPG, PNG, WebP）
- 音樂拖曳上傳（支援 MP3, WAV, OGG）
- **BPM 驅動 Ken-Burns 特效**：使用 Librosa 分析音樂 BPM，以多頻黃金比例正弦疊加驅動 zoompan 縮放/平移動態
- **動漫臉部保護**：自動偵測動漫角色臉部（含側臉），動態調整平移振幅與中心偏移，避免 Ken-Burns 效果裁切臉部
- 畫面淡入淡出效果
- **FFmpeg 實際渲染**：使用 zoompan 濾鏡產生真實 Ken-Burns 影片
- 即時渲染進度（WebSocket + `-progress pipe:1` 解析）
- NVENC GPU 硬體加速（自動偵測，fallback 至 libx264）
- 多音訊自動串接（FFmpeg concat 濾鏡）
- 渲染取消支援（即時終止 FFmpeg 進程）
- 輸出後一鍵開啟資料夾
- 深色主題現代化 UI

## 技術架構

```
前後端分離架構
┌─────────────────┐     ┌─────────────────┐
│   Vue 3 前端     │────▶│  FastAPI 後端    │
│   Vite + TS     │◀────│   Python 3.x    │
└─────────────────┘     └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  KenBurns 引擎  │
                    │  FFmpeg + OpenCV │
                    └─────────────────┘
```

### 技術堆疊

- **後端**：FastAPI、SQLAlchemy 2.0、Pydantic v2、FFmpeg
- **前端**：Vue 3 (Composition API)、Vite、TypeScript、Tailwind CSS、Pinia
- **影像處理**：OpenCV、Pillow、FFmpeg (NVENC GPU 加速)
- **動漫臉部偵測**：dghs-imgutils (ONNX YOLO)、lbpcascade_animeface (fallback)
- **音訊分析**：Librosa (BPM 偵測)

## 快速開始

### 前置需求

- Python 3.10+
- Node.js 18+
- FFmpeg（需加入 PATH）

### 安裝與啟動

#### 1. 複製專案

```bash
git clone <repository-url>
cd Auto-KenBurns-Video-Generator
```

#### 2. 啟動後端

```bash
cd backend

# 建立虛擬環境（推薦）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安裝依賴
pip install -r requirements.txt

# 執行測試（可選）
python -m pytest tests/ -v

# 回到專案根目錄
cd ..
```

**重要：從專案根目錄啟動伺服器**

```bash
# 啟動開發伺服器（使用 --reload 自動重載）
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 或不使用 --reload（更穩定）
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

API 文件：http://localhost:8000/docs

#### 3. 啟動前端

```bash
cd frontend

# 安裝依賴
npm install

# 執行測試（可選）
npm run test

# 啟動開發伺服器
npm run dev
```

前端網站：http://localhost:5173

### 生產環境部署

```bash
# 前端建置
cd frontend
npm run build

# 後端啟動（從專案根目錄）
cd ..
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 使用方式

1. 開啟瀏覽器訪問 http://localhost:5173
2. 上傳圖片（動漫人物圖片等）
3. 上傳音樂（可多首，系統自動串接）
4. 點擊「開始渲染」
5. 即時觀看渲染進度（WebSocket 推送）
6. 渲染完成後點擊「開啟輸出資料夾」檢視影片

### BPM 驅動效果說明

系統使用 Librosa 分析音樂 BPM，以正弦函數驅動 FFmpeg zoompan 濾鏡的縮放與平移：

| BPM 範圍 | 縮放幅度 | 效果風格 |
|----------|----------|----------|
| < 80     | 0.25     | 緩慢悠長 |
| 80-140   | 0.35     | 標準動態 |
| > 140    | 0.45     | 快速強烈 |

縮放循環次數與平移頻率皆由 BPM 動態計算，平移使用正弦/餘弦相位差產生橢圓軌跡。

### 動漫臉部保護

渲染前自動偵測圖片中的動漫角色臉部（支援正面與側臉），並動態調整 Ken-Burns 效果參數：

- **偵測引擎**：優先使用 dghs-imgutils（ONNX YOLO 模型），fallback 至 lbpcascade_animeface
- **中心偏移**：將平移基準從影像中心偏移到臉部中心
- **安全振幅鉗制**：確保最大縮放+最大平移時，臉部仍完全在 viewport 內
- **降級策略**：偵測失敗時自動使用預設行為，不影響渲染流程

## API 端點

所有 API 路由使用 `/api/v1/` 前綴：

| 模組 | 端點 | 說明 |
|------|------|------|
| 快速渲染 | `POST /api/v1/quick-render` | 上傳圖片+音樂直接渲染 |
| 渲染狀態 | `GET /api/v1/render/status/{job_id}` | 查詢渲染進度 |
| 取消渲染 | `POST /api/v1/render/cancel/{job_id}` | 取消渲染任務 |
| 開啟資料夾 | `POST /api/v1/render/open-folder/{job_id}` | 開啟輸出資料夾 |
| 上傳 | `POST /api/v1/upload/image` | 圖片上傳 |
| 上傳 | `POST /api/v1/upload/audio` | 音訊上傳 |
| 專案 | `/api/v1/projects` | 專案 CRUD |
| 設定 | `/api/v1/settings/*` | 系統設定 |
| WebSocket | `/ws/render/{job_id}` | 即時渲染進度 |

## 測試

本專案使用 TDD（測試驅動開發）：

```bash
# 後端測試（從專案根目錄執行）
python -m pytest backend/tests/ -v

# 前端測試
cd frontend
npm run test
```

### 測試覆蓋

| 類別 | 數量 |
|------|------|
| 後端測試 | 90 |
| 前端測試 | 18 |
| **總計** | **108** |

## 專案結構

```
.
├── backend/                 # FastAPI 後端
│   ├── routers/             # API 路由
│   ├── services/            # 業務邏輯
│   │   ├── kenburns_service.py       # Ken-Burns 效果引擎（BPM 分析、安全區計算）
│   │   ├── ffmpeg_renderer.py        # FFmpeg 渲染器（命令構建、進度追蹤）
│   │   ├── render_service.py         # 渲染任務管理與協調
│   │   ├── face_detection_service.py # 動漫臉部偵測（imgutils / cascade）
│   │   └── file_service.py           # 檔案管理
│   ├── resources/           # 靜態資源（分類器 XML 等）
│   ├── models/              # SQLAlchemy 模型
│   ├── schemas/             # Pydantic 模式
│   ├── database/            # 資料庫連線
│   ├── migrations/          # Alembic 遷移
│   └── tests/               # pytest 測試
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── components/      # Vue 元件
│   │   │   ├── common/      # 共用元件
│   │   │   ├── player/      # 影片播放器
│   │   │   ├── progress/    # 進度元件
│   │   │   └── upload/      # 上傳元件
│   │   ├── composables/     # Vue Composables
│   │   ├── router/          # Vue Router 配置
│   │   ├── views/           # 頁面視圖
│   │   ├── stores/          # Pinia 狀態管理
│   │   ├── services/        # API 與 WebSocket 服務
│   │   └── types/           # TypeScript 類型定義
│   ├── tailwind.config.js
│   └── vite.config.ts
├── SPEC.md                  # 技術規格書
├── API.md                   # API 文件
└── CLAUDE.md                # Claude Code 指引
```

## 前端設計系統

### 色彩

- 主背景: `#0a0a0f` (深黑色)
- 次背景: `#12121a` (深灰)
- 強調色: Cyan `#06b6d4`, Violet `#8b5cf6`, Fuchsia `#d946ef`

### 字體

- 顯示字體: Outfit
- 等寬字體: Space Mono

### 元件樣式

- 玻璃效果卡片 (`glass-card`)
- 漸層按鈕 (`btn-primary`)
- 拖曳上傳區 (`drop-zone`)
- 進度條漸層 (`progress-gradient`)

### API 代理

前端通過 Vite proxy 連接後端（設定在 `vite.config.ts`）：

- `/api/*` → `http://localhost:8000`
- `/ws/*` → `ws://localhost:8000`
- `/uploads/*` → `http://localhost:8000`
- `/output/*` → `http://localhost:8000`

## 多 Agent 協作框架

本專案使用 Claude Code 的多 Agent 協作：

| Agent | 職責 |
|-------|------|
| Coder-PM | 專案經理，協調任務 |
| Coder-Plan | 技術架構師 |
| Coder-Backend | 後端開發 |
| Coder-Bridge | API 設計 |
| Coder-Database | 資料庫專家 |
| Coder-Frontend | 前端開發 |
| Coder-Test | 測試工程師 |
| Coder-Review | Code Review |
| Coder-Debug | 問題診斷與除錯 |

使用方式：
```
Use the coder-pm agent to build [功能描述]
```

## 授權

MIT License
