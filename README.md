# Auto-KenBurns 影片生成系統

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green?logo=fastapi)
![Vue 3](https://img.shields.io/badge/Vue-3+-42b883?logo=vue.js)
![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178c6?logo=typescript)
![Tests](https://img.shields.io/badge/Tests-52%20passed-green)
![Coverage](https://img.shields.io/badge/Coverage-70%25-yellow)

## 專案概述

自動生成 Ken-Burns 特效影片的 Web 應用程式。將圖片與音樂自動串接，生成帶有流暢平移與縮放效果的影片。專為動漫人物圖片與 YouTube 音樂頻道影片設計。

## 功能特色

- 圖片拖曳上傳（支援 JPG, PNG, WebP, BMP）
- 音樂拖曳上傳（支援 MP3, WAV, AAC, FLAC, OGG）
- **BPM 驅動 Ken-Burns 特效**：根據音樂節奏自動調整動作切換頻率
- 持續動態動作：放大/縮小/平移/對角線/旋轉自動切換
- 畫面淡入淡出效果
- 動漫人物主體保護（防止裁切頭部）
- 即時渲染進度（WebSocket）
- CUDA/GPU 硬體加速輸出
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
cd click-merge-ken-burn
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
2. 建立新專案
3. 上傳圖片（動漫人物圖片）
4. 上傳音樂（YouTube 影片的音訊）
5. 設定輸出格式（解析度、幀率）
6. 點擊「開始生成影片」
7. 等待渲染完成並下載

### BPM 驅動效果說明

系統會自動分析音樂的 BPM，並據此調整 Ken-Burns 動作：

| BPM 範圍 | 動作風格 | 切換間隔 |
|----------|----------|----------|
| < 80     | 緩慢悠長 | 1.5-3 秒 |
| 80-140   | 標準     | 1-2 秒   |
| > 140    | 快速動態 | 0.5-1 秒 |

## API 端點

所有 API 路由使用 `/api/v1/` 前綴：

| 模組 | 端點 | 說明 |
|------|------|------|
| 上傳 | `/api/v1/upload/image` | 圖片上傳 |
| 上傳 | `/api/v1/upload/audio` | 音訊上傳 |
| 專案 | `/api/v1/projects` | 專案 CRUD |
| 渲染 | `/api/v1/render/start` | 開始渲染 |
| 設定 | `/api/v1/settings/*` | 系統設定 |
| WebSocket | `/ws/render/{job_id}` | 即時進度 |

## 測試

本專案使用 TDD（測試驅動開發）：

```bash
# 後端測試
cd backend
source venv/Scripts/activate
python -m pytest tests/ -v

# 前端測試
cd frontend
npm run test
```

### 測試覆蓋

| 類別 | 數量 |
|------|------|
| 後端單元測試 | 26 |
| 後端整合測試 | 8 |
| 前端單元測試 | 18 |
| **總計** | **52** |

## 專案結構

```
.
├── backend/                 # FastAPI 後端
│   ├── routers/           # API 路由
│   ├── services/          # 業務邏輯
│   ├── models/            # SQLAlchemy 模型
│   ├── schemas/           # Pydantic 模式
│   ├── database/          # 資料庫連線
│   └── migrations/        # Alembic 遷移
├── frontend/              # Vue 3 前端
│   ├── src/
│   │   ├── components/   # Vue 元件
│   │   ├── views/        # 頁面視圖
│   │   ├── stores/       # Pinia 狀態
│   │   ├── services/     # API 服務
│   │   └── types/        # TypeScript 類型
│   └── ...
├── SPEC.md               # 技術規格書
├── API.md                # API 文件
└── CLAUDE.md             # Claude Code 指引
```

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

使用方式：
```
Use the coder-pm agent to build [功能描述]
```

## 授權

MIT License
