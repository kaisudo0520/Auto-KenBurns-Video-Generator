# Auto-KenBurns 影片生成系統

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green?logo=fastapi)
![Vue 3](https://img.shields.io/badge/Vue-3+-42b883?logo=vue.js)
![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178c6?logo=typescript)
![Tests](https://img.shields.io/badge/Tests-205%20passed-green)
![Coverage](https://img.shields.io/badge/Coverage-80%25-yellow)

## 專案概述

自動生成 Ken-Burns 特效影片的 Web 應用程式。將圖片與音樂自動串接，生成帶有流暢平移與縮放效果的影片。專為動漫人物圖片與 YouTube 音樂頻道影片設計。

## 功能特色

- 圖片拖曳上傳與拖曳排序（支援 JPG, PNG, WebP）
- 音樂拖曳上傳與拖曳排序（支援 MP3, WAV, OGG）
- **BPM 驅動 XYZR 四軸統一特效**：使用 Librosa 分析音樂 BPM，以 4 層黃金比例正弦疊加驅動 XYZ 三軸 + 旋轉搖擺同步運作，形成 4D 運動軌跡
- **隨機化強弱動態**：各軸振幅在範圍內隨機生成，確保每次渲染效果具備獨特性
- **動漫臉部保護**：自動偵測動漫角色臉部（含側臉），限制平移振幅並調整中心偏移
- **段間/段內 BPM 同步停頓**：每段運鏡跑完後 tpad 硬複製最後一幀定格 5–10 秒讓眼睛休息，1 圖 + 1 音樂長曲自動拆段啟用「連續運動模式」（seed + 相位接續）確保 hold 後重啟無視覺斷點
- **位元率上限**：8 Mbps 目標 / 10 Mbps 峰值 / 16 Mbps buffer，NVENC 與 libx264 一致
- 畫面淡入淡出效果（段間 xfade + 音訊整體首尾 fade）
- **FFmpeg 實際渲染**：使用 zoompan 濾鏡產生真實 Ken-Burns 影片
- 即時渲染進度（WebSocket + `-progress pipe:1` 解析）
- NVENC GPU 硬體加速（自動偵測，fallback 至 libx264）
- 多音訊自動串接（xfade/acrossfade 交叉淡入淡出）
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

#### Windows 一鍵啟動（推薦）

雙擊專案根目錄的 **`start.bat`** 即可：

- 自動建立 `backend\venv`（需 Python 3.10 以上）並安裝依賴（首次執行）
- 自動執行 `npm install`（首次執行）
- 啟動任何服務之前先檢查兩個連接埠：被本專案的服務占用就沿用，被其他程式占用則報錯，不會啟動到一半留下孤兒程序
- 以 **venv 內的 Python** 啟動後端（預設 port 8000）、以 Vite 啟動前端（預設 port 5173），各開一個命令視窗
- 等待兩個服務就緒，並比對「直連後端」與「經前端 proxy」取得的 `/health` `instance_id` 確認前後端配對正確後，才自動開啟瀏覽器；任一失敗會清理本次啟動的程序並以錯誤結束

要關閉服務請雙擊 **`stop.bat`**，它只會結束能從命令列辨識為本專案服務的程序，不會依連接埠盲殺。

連接埠設定的優先順序：`start.bat` 為 命令列參數（例如 `start.bat -BackendPort 8010 -FrontendPort 5180`）、環境變數 `BACKEND_PORT` / `FRONTEND_PORT`、預設值；
`stop.bat` 為 命令列參數、`scripts\.running-ports.json` 啟動記錄、環境變數、預設值（記錄是實際執行中服務的事實來源，與環境變數不同時會提示）。
`start.bat` 成功後會把實際使用的埠寫到該記錄，`stop.bat` 不帶參數時會讀取它；只有成功停止該組服務時才會刪除記錄。
若記錄中的服務仍在執行，改用不同的埠再次 `start.bat` 會被拒絕，請先 `stop.bat`。

實際邏輯在 `scripts\start.ps1` / `scripts\stop.ps1`（共用 `scripts\_common.ps1`），BAT 只是薄殼。

> 手動啟動時請注意：PowerShell 啟用 venv 要用 `.\backend\venv\Scripts\Activate.ps1`，
> `source venv/Scripts/activate` 只適用於 Git Bash。若未正確啟用，`uvicorn` 可能解析到系統其他 Python
> （例如 Anaconda）而缺少 `imgutils`，臉部偵測會靜默退回只認正面臉的 cascade。

> 前端的 `/api`、`/ws`、`/uploads`、`/output` 在 `npm run dev` 與 `vite preview` 都經由 Vite proxy 轉發到後端；
> 若將建置後的前端獨立部署（沒有 Vite proxy），需在執行 `vite build` **之前**設定 `VITE_API_URL` 與 `VITE_WS_URL`
> 指向後端（Vite 會在建置時將其寫入產物，部署後再設定環境變數無效）。

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
source venv/bin/activate          # Linux/Mac
source venv/Scripts/activate      # Windows Git Bash
.\venv\Scripts\Activate.ps1       # Windows PowerShell

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

> `npm run preview`（預覽 `dist/` 建置結果）使用獨立的 port 4173（可用環境變數 `PREVIEW_PORT` 覆寫），
> 與開發伺服器的 5173 分開，避免殘留的 preview 被一鍵啟動器當成可沿用的前端；preview 同樣經 proxy 連到後端。

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

系統使用 Librosa 分析音樂 BPM，以多頻正弦疊加驅動 FFmpeg zoompan 濾鏡的縮放與平移。

**運動設計**（Overscan 雙向縮放 + 統一 3D 攝影機模型 + 旋轉搖擺）：
- **Overscan 緩衝區**：`base_zoom=1.15`，圖片初始只顯示 ~85%，多出 15% 為移動緩衝區
- **雙向縮放**：`z = base_zoom ± amp/2`，可 zoom in 也可 zoom out，全程都有平移空間
- **XYZR 四軸同步**：4 層黃金比例頻率正弦疊加，XYZ + 旋轉同時運作，形成 4D 運動軌跡
- **旋轉搖擺**：BPM 同步正弦擺動（8–15°），模擬攝影機搖擺動感
- **隨機振幅組合**：各軸振幅在範圍內隨機生成，確保每次渲染具備獨特性
- **微動呼吸感**：低振幅高頻正弦（畫面 0.2%），模擬攝影機手持質感

| 參數 | 週期 / 數值 | 說明 |
|------|-------------|------|
| 縮放週期 (Z) | 10 小節 | BPM 160: 15s, BPM 120: 20s, BPM 80: 30s |
| 平移基頻 (X) | 2.5 小節 | 50% 權重 |
| 平移二次頻 | 基頻 × φ | 25% 權重，黃金比例 |
| 平移三次頻 | 基頻 × φ² | 15% 權重 |
| 平移四次頻 | 基頻 × φ³ | 10% 權重（高頻微擾） |
| 旋轉週期 (R) | 10/φ ≈ 6.18 小節 | 與縮放黃金比例偏移，永不同步 |

**BPM 動態調整**（以 BPM 160 為基準）：
- `clamped_ratio = clamp(bpm/160, 0.5, 1.5)`
- **隨機振幅範圍** (均需 × ratio)：
  - 縮放幅度 (Z)：`random(0.10, 0.28)`（雙向，實際半振幅）
  - 水平振幅 (X)：`random(0.02, 0.10)`
  - 垂直振幅 (Y)：`random(0.015, 0.07)`
  - 旋轉振幅 (R)：`random(8, 15)°`

### 段間 BPM 同步停頓（所有多段模式自動套用）

每段運鏡跑完後以 `trim=end_frame + tpad=stop=N:stop_mode=clone` 硬複製最後一幀凍結 5–10 秒讓觀眾消化畫面：

- hold 時長 = `16 拍 × 60 / BPM`，clamp 在 `[5, 10]` 秒
  - BPM 120 → 8s、BPM 160 → 6s、BPM 60 → 10s、BPM 200 → 5s
- 至少保留 `max(1s, seg/3)` 運鏡時長，避免極短段完全被 hold 吃掉
- 使用**整數 `stop=N` 幀**，無浮點捨入漂移
- `tpad=stop_mode=clone` 為 bit-identical 硬複製，編碼器看到相同幀高效壓縮

### 段內週期性停頓（1 圖 + 1 音樂長曲）

`build_command` 接收單圖單音樂且 `total_duration >= 20s` 時自動拆成 pseudo-segments：

- `n_pseudo = max(2, round(total / 20))`，目標每段 ~20s（約 12s 運鏡 + 8s 停頓）
- `crossfade_duration = 0` 走 concat 串接，**保留完整音訊不截斷**
- **連續運動模式**確保 hold 後重啟無視覺斷點：
  1. 所有 pseudo-segments 共用 seed → 同一條動畫軌跡
  2. 相位累積 `on → (on + i × motion_frames)` → 接續前段結束處
  3. 略過 EMA 平滑 → 避免 `px/py` 重置為 0 的啟動瞬態
- 可用 `intra_hold=False` 參數關閉

### 多段渲染

多圖 + 多音訊的渲染策略：
- 每首音訊配一張圖片（圖片循環分配），每段獨立 zoompan + 獨立 BPM
- 影片段間：xfade 交叉淡入淡出（首末段外加 fade=in / fade=out）
- 音訊段間：acrossfade 交叉淡入淡出，整體首尾 1.5 秒 afade
- xfade/acrossfade offset 以**整數幀換算**的影片時長計算，避免浮點累積
- `cycle_offset × 黃金角(2.4 rad)` 確保跨段相位連續不重複
- 有效時長 = Σ(音訊時長) − (段數−1) × crossfade_duration
- **同圖多段優化**：以 `split=N` 分流單一圖片輸入，避免黑畫面問題

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
| 後端測試 | 187 |
| 前端測試 | 18 |
| **總計** | **205** |

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

## TODO — 架構級待辦

以下項目需要獨立開發週期處理，不適合在 code review 中快速修復：

- [ ] **認證/授權系統** — 實作 JWT 或 API Key 認證，所有 API 端點目前無任何認證保護。需設計：Token 機制、角色權限、中介層整合、環境區分（dev/prod）
- [ ] **DB 連線池改造** — 目前使用 SQLite StaticPool 單一連線，渲染期間長期持有 session。需評估：NullPool + scoped_session、或遷移至 PostgreSQL + 連線池
- [ ] **前端 `as any` 型別標註清理** — `ResultView.vue` 和 `renderStore.ts` 中有多處 `as any` 強制轉型，需釐清後端 API 回應結構後統一修正 TypeScript 型別定義

## 授權

MIT License
