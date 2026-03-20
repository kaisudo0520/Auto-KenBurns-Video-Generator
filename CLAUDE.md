# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ Important Language Requirement

**All responses and communication must be in Traditional Chinese (繁體中文).**

This includes:
- All code comments and documentation
- User-facing messages and prompts
- Agent communications
- Any textual output

---

## Project Overview

Auto-KenBurns Video Generator - A web application that automatically generates Ken-Burns effect videos from images and music. Designed for anime character images with YouTube music channel videos in mind.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Vue 3 Frontend │────▶│  FastAPI Backend │
│   (Vite + TS)   │◀────│   (Python 3.x)   │
└─────────────────┘     └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  KenBurns Engine │
                    │  (FFmpeg/OpenCV) │
                    └─────────────────┘
```

## Running the Application

### Backend

```bash
cd backend

# 建立虛擬環境（推薦）
python -m venv venv
source venv/Scripts/activate  # Windows

# 安裝依賴
pip install -r requirements.txt

# 執行測試
python -m pytest tests/ -v

# 啟動伺服器（注意：需要從專案根目錄執行）
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 如果 port 8000 被佔用，可使用 8001
uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

API docs available at http://localhost:8000/docs (或 http://localhost:8001/docs)

### Frontend

```bash
cd frontend
npm install

# 執行測試
npm run test

# 啟動開發伺服器
npm run dev
```

Frontend runs at http://localhost:5173 with API proxy to backend.

### Production Build

```bash
# Frontend
cd frontend && npm run build

# Backend (with production server)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Key Technologies

- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic v2, FFmpeg
- **Frontend**: Vue 3 (Composition API), Vite, TypeScript, Tailwind CSS, Pinia
- **Media Processing**: OpenCV, Pillow, FFmpeg (NVENC for GPU acceleration)
- **Audio Analysis**: Librosa (for BPM detection)
- **Testing**: pytest (backend), vitest (frontend)

## Testing

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
| 後端測試 | 141 |
| 前端測試 | 18 |
| **總計** | **159** |

## Important Design Notes

### FFmpeg 渲染管線

渲染流程由三個服務協作：

1. **`kenburns_service.py`** — BPM 分析（Librosa）
2. **`ffmpeg_renderer.py`** — FFmpeg 命令構建、zoompan 表達式生成、非同步執行與進度追蹤
3. **`render_service.py`** — 渲染任務協調（階段管理、WebSocket 進度廣播、取消處理）

渲染階段：`LOADING_IMAGES → PROCESSING_AUDIO → GENERATING_PATHS → ENCODING_VIDEO → FINALIZING`

FFmpeg 使用 `zoompan` 濾鏡搭配 BPM 驅動的 **XYZ 三軸統一表達式** 產生 Ken-Burns 效果：

**運動設計**（Overscan 雙向縮放 + 統一 3D 攝影機模型 + 旋轉搖擺）：
- **Overscan 緩衝區**：`base_zoom=1.15`，圖片初始只顯示 ~85%，多出 15% 為移動緩衝區
- **雙向縮放**：z = base_zoom ± amp/2，可 zoom in 也可 zoom out，全程都有平移空間
- **XYZ 三軸同步**：4 層黃金比例頻率正弦疊加，XYZ 三軸同時連貫運動，形成 3D Lissajous 軌跡
- **旋轉搖擺**：BPM 同步正弦擺動（`random(8, 15)°`），模擬攝影機搖擺動感
- **隨機振幅組合**：各軸振幅在範圍內隨機生成，確保每次渲染具備獨特性
- **微動呼吸感**：低振幅高頻正弦（畫面 0.2%），模擬攝影機手持質感

**縮放（z 軸）**：
- 週期 = 10 小節（BPM 160: 15s, BPM 120: 20s, BPM 80: 30s）
- `base_zoom + amp × (smootherstep((1-cos)/2) - 0.5)` → 雙向縮放
- 安全約束：z_min >= 1.0（不會 zoom out 到露出黑邊）

**平移（x/y 軸）**：
- X 基頻 = 2.5 小節（加快平移節奏），權重 50%
- 二次頻 = 基頻 × φ（黃金比例），權重 25%
- 三次頻 = 基頻 × φ²，權重 15%
- 四次頻 = 基頻 × φ³（高頻微擾），權重 10%
- X 用 sin、Y 用 cos → 橢圓軌跡（非直線往復）

**旋轉（rotation 軸）**：
- 振幅：`random(8, 15)°` × BPM ratio，正弦擺動（sin 自然在兩端減速、中間加速）
- 週期 = `10/φ ≈ 6.18 小節`（與縮放 10 小節黃金比例偏移，永不同步）
- 濾鏡鏈：`zoompan(1920x1080) → scale(放大至旋轉緩衝區) → rotate(BPM 正弦擺動) → crop(1920x1080 中心)`
- 放大倍率：自動計算 16:9 旋轉緩衝區尺寸，含 2% 安全邊距，確保旋轉後裁切無黑角
- 多段模式：各段旋轉相位用 `cycle_offset × 2.4 rad` 偏移，與 XYZ 一致

**XYZR 4-Axis 協同運作**：
- 全時連貫運動，某軸振幅接近 0 時自動退化為低維運動
- 四軸頻率採用不可公約組合（zoom=10 bar, pan=2.5 bar, rotation=6.18 bar），確保軌跡永不完全重複

**BPM 動態調整**（以 BPM 160 為基準）：
- `clamped_ratio = clamp(bpm/160, 0.5, 1.5)`
- **隨機振幅範圍** (均需 × ratio)：
  - 縮放幅度 (Z)：`random(0.10, 0.28)`（雙向，實際半振幅）
  - 水平振幅 (X)：`random(0.02, 0.10)`
  - 垂直振幅 (Y)：`random(0.015, 0.07)`
  - 旋轉振幅 (R)：`random(8, 15)°`（正弦擺動）

**抖動消除**：
1. `trunc()` 包裹 x/y 座標（一致的整數截斷方向）
2. 4x 超取樣 + Lanczos 縮放（捨入誤差降至 0.25px，參考 FFmpeg Trac #4298）
3. EMA 時間平滑（α=0.18）：一階 IIR 低通濾波

**多段渲染**（多圖 + 多音訊）：
- 每首音訊配一張圖片（圖片循環分配），每段獨立 zoompan + 獨立 BPM
- **多段模式觸發條件**：圖片數 > 1 **或** 音訊數 > 1（兩者任一滿足即進入多段）
- 影片段間：每段獨立 `fade=in` / `fade=out`（1 秒），再用 `concat` 串接
- 音訊段間：直接 `concat` 串接（段間無淡入淡出），僅整體首尾 1.5 秒 `afade`
- `cycle_offset × 黃金角(2.4 rad)` 確保跨段相位連續不重複
- 有效時長 = Σ(音訊時長)
- **同圖多段優化**：所有段使用同一張圖片時，以 `split=N` 濾鏡分流單一輸入，
  避免重複開啟同一檔案導致後續段落黑畫面的 FFmpeg 問題

編碼器自動偵測：優先使用 `h264_nvenc` (NVENC GPU)，fallback 至 `libx264`。
進度追蹤：FFmpeg `-progress pipe:1` 解析 `out_time_us`。
取消支援：`_active_renderers` 全域字典追蹤 FFmpeg 進程，取消時呼叫 `terminate()`。

### Anime Character Protection

The Ken-Burns service (`backend/services/kenburns_service.py`) includes subject detection to protect anime character heads/faces from being cropped. The safe zone calculation prioritizes face and body core regions.

### API Endpoints

All API routes are prefixed with `/api/v1/`:
- `POST /api/v1/quick-render` - 快速渲染（上傳圖片+音樂直接渲染）
- `GET /api/v1/render/status/{job_id}` - 渲染狀態查詢
- `POST /api/v1/render/cancel/{job_id}` - 取消渲染
- `POST /api/v1/render/open-folder/{job_id}` - 開啟輸出資料夾
- `/api/v1/upload/*` - File upload (images/audio)
- `/api/v1/projects/*` - Project CRUD
- `/api/v1/settings/*` - System settings
- `/ws/render/{job_id}` - WebSocket for real-time progress

## Multi-Agent Framework

本專案使用 Claude Code 的多 Agent 協作框架：

| Agent | 角色 | 職責 | 搭配 ECC 技能 |
|-------|------|------|---------------|
| **Coder-PM** | 專案經理 | 需求分析、任務分派、協調各 Agent 協作 | `plan`, `blueprint`, `search-first`, `verification-loop` |
| **Coder-Plan** | 技術架構師 | 撰寫規格書、技術方案設計 | `planner`, `blueprint`, `backend-patterns`, `api-design` |
| **Coder-Backend** | 後端開發者 | FastAPI 路由、服務層、FFmpeg 整合 | `python-patterns`, `backend-patterns`, `security-review`, `video-editing` |
| **Coder-Bridge** | API 設計師 | 前後端介面規格、型別同步 | `api-design`, `coding-standards` |
| **Coder-Database** | 資料庫專家 | 資料模型設計、Alembic 遷移、查詢優化 | `postgres-patterns`, `database-migrations` |
| **Coder-Frontend** | 前端開發者 | Vue 3 元件、頁面、狀態管理 | `frontend-patterns`, `frontend-design`, `e2e-testing` |
| **Coder-Test** | 測試工程師 | pytest / vitest 測試撰寫與執行 | `tdd`, `python-testing`, `tdd-workflow`, `e2e` |
| **Coder-Review** | 程式碼審查 | 品質檢查、安全審查、效能建議 | `python-review`, `security-review`, `code-review` |
| **Coder-Debug** | 除錯專家 | 錯誤排查、日誌分析、效能瓶頸定位 | `verification-loop`, `python-review` |

> ECC 技能前綴：`/everything-claude-code:`，例如 `/everything-claude-code:plan`

使用方式：`Use the coder-pm agent to build [feature description]`
