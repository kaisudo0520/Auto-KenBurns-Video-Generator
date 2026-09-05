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

### 一鍵啟動（Windows，推薦）

專案根目錄 `start.bat` / `stop.bat`（純 ASCII 薄殼，邏輯在 `scripts/start.ps1`、`scripts/stop.ps1`，共用 `scripts/_common.ps1`）：

- 流程：venv（必檢 Python >= 3.10、缺套件則裝 requirements）→ `npm install`（缺 node_modules 時）→ **啟動前檢查** → 啟動 → 等待就緒 + proxy 探測 → 寫記錄 → 開瀏覽器
- 一律以 `backend\venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0` 啟動後端，不依賴 shell 是否已啟用 venv
- 連接埠優先順序：start 為 參數 `-BackendPort/-FrontendPort`（0 或負數直接報錯，不退回）> 環境變數 `BACKEND_PORT/FRONTEND_PORT`（只接受 ASCII 十進位，否則退回預設並警告）> 預設 8000/5173；stop 為 參數 > `scripts/.running-ports.json`（實際執行中服務的事實來源，與環境變數不同時會警告）> 環境變數 > 預設；超出 1~65535 或同埠報錯
- 啟動前檢查在啟動任何**服務**之前完成（venv / npm install 仍可能先執行）：埠被本專案服務占用則沿用（後端：命令列以 token 邊界含 `backend.main:app`，刻意不比對路徑以涵蓋跑錯環境的 uvicorn；前端：命令列含 `vite` 且在專案路徑下），被其他程式占用則報錯；「前端沿用但後端是新啟動」視為配對不明而報錯；記錄中的另一組服務仍在執行且埠不同也報錯
- 就緒等待為單一總時限（`-WaitLimitSeconds`，預設 90），同時輪詢 `/health` 與前端 `/`（各試 127.0.0.1 與 [::1]）；本次啟動的服務視窗底下已無子程序（排除 conhost.exe）即立即失敗，沿用的服務若不再監聽也立即失敗；就緒後進入**配對階段**（獨立時限：剩餘時限與 10 秒取大者），重試比對「直連後端」與「經前端 proxy」的 `/health` `instance_id`；不一致時隔 1 秒再取樣一次，連續兩次不同才判 mismatch（避免 `--reload` 重啟瞬間誤判）；取不到則 unreachable；兩者皆失敗並清理
- `instance_id` 由 `main.py` 的 `resolve_instance_id()` 決定：環境變數 `KENBURNS_INSTANCE_ID` 優先（`start.ps1` 啟動後端前會設定，讓 `--workers N` 的所有 worker 共用），否則每個 worker 各自產生；手動以 `--workers 4` 啟動且未設該變數的後端被沿用時，配對可能因落到不同 worker 而失敗，錯誤訊息會提示
- 失敗清理只針對本次以 `-PassThru` 記錄、且命令列仍符合錨定樣式 `<cmd.exe> /k title Auto-KenBurns Backend/Frontend :<port> && ` 的 cmd 視窗；不動記錄檔；失敗訊息會帶出可直接執行的 `stop.bat -BackendPort X -FrontendPort Y`
- 記錄檔寫入：同目錄唯一暫存檔 → 既有檔以 `[IO.File]::Replace`（Win32 ReplaceFile，原子）取代，失敗（唯讀、被其他 handle 開著）退回 `Move-Item -Force` 並重試 3 次、首次建立以 rename 搬入；寫入失敗時**不拆掉**已驗證健康的服務，只印停止指令並以非零碼結束
- `stop.bat` 只結束通過同一身分驗證的程序，跳過 PID <= 4，檢查 taskkill 退出碼與停止後埠狀態；關窗改以 cmd 命令列比對而非視窗標題；有任何失敗則保留記錄並以非零碼結束，只在停的就是記錄那組時刪除記錄
- 前端的 `/health`、`/api`、`/ws`、`/uploads`、`/output` 在 dev 與 preview 都走 Vite proxy（preview 用獨立的 `PREVIEW_PORT`，預設 4173，避免殘留的 preview 被當成可沿用的前端）（目標 `127.0.0.1:${BACKEND_PORT}`，`vite.config.ts` 會驗證埠範圍）；WebSocket 預設同源 `ws://${location.host}`，只有設定 `VITE_WS_URL` / `VITE_API_URL` 才直連
- `npm run type-check` 同時檢查 `tsconfig.node.json`（`@types/node` 已為 devDependency）

**啟用 venv 的 shell 差異**：`source venv/Scripts/activate` 只在 Git Bash 有效；PowerShell 必須用
`.\backend\venv\Scripts\Activate.ps1`。venv 未生效時 `uvicorn` 會解析到 Anaconda 的版本，
該環境沒有 `imgutils`，臉部偵測會靜默退回只認正面臉的 `lbpcascade_animeface`。

### Backend

```bash
cd backend

# 建立虛擬環境（推薦）
python -m venv venv
source venv/Scripts/activate      # Windows Git Bash
.\venv\Scripts\Activate.ps1       # Windows PowerShell

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

# Backend (with production server, run from project root)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
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
source venv/Scripts/activate      # Git Bash；PowerShell 改用 .\venv\Scripts\Activate.ps1
python -m pytest tests/ -v

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

## Important Design Notes

### FFmpeg 渲染管線

渲染流程由三個服務協作：

1. **`kenburns_service.py`** — BPM 分析（Librosa）
2. **`ffmpeg_renderer.py`** — FFmpeg 命令構建、zoompan 表達式生成、非同步執行與進度追蹤
3. **`render_service.py`** — 渲染任務協調（階段管理、WebSocket 進度廣播、取消處理）

渲染階段：`LOADING_IMAGES → PROCESSING_AUDIO → GENERATING_PATHS → ENCODING_VIDEO → FINALIZING`

FFmpeg 使用 `zoompan` 濾鏡搭配 BPM 驅動的 **XYZ 三軸統一表達式** 產生 Ken-Burns 效果：

**運動設計**（Overscan 雙向縮放 + 統一 3D 攝影機模型 + 旋轉搖擺）：
- **Overscan 緩衝區**：`base_zoom=1.10`，圖片初始只顯示 ~91%，多出 10% 為移動緩衝區（較小 overscan 讓畫面更完整）
- **雙向縮放**：z = base_zoom ± amp/2，可 zoom in 也可 zoom out，全程都有平移空間
- **XYZ 三軸同步**：4 層黃金比例頻率正弦疊加，XYZ 三軸同時連貫運動，形成 3D Lissajous 軌跡
- **旋轉搖擺**：BPM 同步正弦擺動（`random(4, 9)°`），模擬攝影機搖擺動感
- **隨機振幅組合**：各軸振幅在範圍內隨機生成，確保每次渲染具備獨特性
- **微動呼吸感**：低振幅高頻正弦（畫面 0.2%），模擬攝影機手持質感

**縮放（z 軸）**：
- 週期 = 13 小節（BPM 160: 19.5s, BPM 120: 26s, BPM 80: 39s）
- `base_zoom + amp × (smootherstep((1-cos)/2) - 0.5)` → 雙向縮放
- 安全約束：z_min >= 1.0（不會 zoom out 到露出黑邊）

**平移（x/y 軸）**：
- X 基頻 = 3.25 小節（放慢平移節奏），權重 50%
- 二次頻 = 基頻 × φ（黃金比例），權重 25%
- 三次頻 = 基頻 × φ²，權重 15%
- 四次頻 = 基頻 × φ³（高頻微擾），權重 10%
- X 用 sin、Y 用 cos → 橢圓軌跡（非直線往復）

**旋轉（rotation 軸）**：
- 振幅：`random(4, 9)°` × BPM ratio，正弦擺動（sin 自然在兩端減速、中間加速）
- 週期 = `13/φ ≈ 8.03 小節`（與縮放 13 小節黃金比例偏移，永不同步）
- 濾鏡鏈：`zoompan(1920x1080) → scale(放大至旋轉緩衝區) → rotate(BPM 正弦擺動) → crop(1920x1080 中心)`
- 放大倍率：自動計算 16:9 旋轉緩衝區尺寸，含 2% 安全邊距，確保旋轉後裁切無黑角
- 多段模式：各段旋轉相位用 `cycle_offset × 2.4 rad` 偏移，與 XYZ 一致

**XYZR 4-Axis 協同運作**：
- 全時連貫運動，某軸振幅接近 0 時自動退化為低維運動
- 四軸頻率採用不可公約組合（zoom=13 bar, pan=3.25 bar, rotation=8.03 bar），確保軌跡永不完全重複

**BPM 動態調整**（以 BPM 160 為基準）：
- `clamped_ratio = clamp(bpm/160, 0.5, 1.5)`
- **隨機振幅範圍** (均需 × ratio)：
  - 縮放幅度 (Z)：`random(0.06, 0.18)`（雙向，實際半振幅）
  - 水平振幅 (X)：`random(0.015, 0.065)`
  - 垂直振幅 (Y)：`random(0.010, 0.045)`
  - 旋轉振幅 (R)：`random(4, 9)°`（正弦擺動）

**抖動消除**：
1. `trunc()` 包裹 x/y 座標（一致的整數截斷方向）
2. 4x 超取樣 + Lanczos 縮放（捨入誤差降至 0.25px，參考 FFmpeg Trac #4298）
3. EMA 時間平滑（α=0.18）：一階 IIR 低通濾波

**多段渲染**（多圖 + 多音訊）：
- 每首音訊配一張圖片（圖片循環分配），每段獨立 zoompan + 獨立 BPM
- **多段模式觸發條件**：圖片數 > 1 **或** 音訊數 > 1（兩者任一滿足即進入多段）
- 影片段間：xfade 交叉淡入淡出（首末段外加 `fade=in` / `fade=out`）
- 音訊段間：`acrossfade` 交叉淡入淡出，整體首尾 1.5 秒 `afade`
- `cycle_offset × 黃金角(2.4 rad)` 確保跨段相位連續不重複
- xfade/acrossfade offset 以**整數幀換算**的影片時長計算（`seg_video_durations`），避免浮點誤差累積
- 有效時長 = Σ(音訊時長) - (段數-1) × crossfade_duration
- **同圖多段優化**：所有段使用同一張圖片時，以 `split=N` 濾鏡分流單一輸入，
  避免重複開啟同一檔案導致後續段落黑畫面的 FFmpeg 問題

**段間 BPM 同步停頓**（所有多段模式自動套用）：
- 每段尾部以 `trim=end_frame=motion_frames, setpts=PTS-STARTPTS` 切掉 zoompan 無限輸出後，
  在 rotate+crop 之後插入 `tpad=stop=hold_frames:stop_mode=clone` 硬複製最後一幀
- hold 時長公式：`16 拍 × 60/BPM`，clamp 在 `[5, 10]` 秒
  - BPM 120 → 8s、BPM 160 → 6s、BPM 60 → clamp 10s、BPM 200 → clamp 5s
- 至少保留 `max(1s, seg/3)` 運鏡時長，避免極短段完全被 hold 吃掉
- 使用**整數 `stop=N` 幀**而非浮點 `stop_duration=秒`，避免捨入漂移
- 為何不用表達式層 `if(gt(on,M),M,on)` clamp：
  1. `px + α×(target - px)` EMA 平滑在凍結後有 0.8s 拖尾（視覺上像運鏡變慢而非停格）
  2. FFmpeg `pow(if(...),N)` 巢狀逗號解析有風險
  - `tpad=stop_mode=clone` 為硬複製，逐 bit 一致凍結，編碼器看到相同幀高效壓縮

**段內週期性停頓（intra_hold）**（1 圖 + 1 音樂長曲）：
- `build_command` 接收單圖單音樂且 `total_duration >= 20s` 時，自動拆成
  `n_pseudo = max(2, round(total / 20))` 個 pseudo-segments，觸發多段邏輯
- `crossfade_duration = 0` 強制走 concat 串接，**保留完整音訊不截斷**
- `continuous_motion=True` 啟用**連續運動模式**，確保 hold 定格後下一段運鏡無視覺斷點：
  1. **共用 seed**：所有 pseudo-segments 共享一組隨機振幅（軌跡完全相同）
  2. **相位累積**：第 i 段傳入 `frame_phase_offset = i × motion_frames`，
     表達式內 `on → (on+offset)` 純常數位移，讓本段從前一段結束處接續
  3. **略過 EMA**：連續運動模式下 `x_expr = x_target` 直接取目標位置，
     避免 zoompan 每段 `px/py` 重置為 0 的啟動瞬態破壞連續性
- 可透過 `intra_hold=False` 參數關閉
- Lossless 驗證：邊界跳躍量 ≈ 正常運鏡量（~1.7 vs ~1.8），hold 內部 delta = 0

**位元率控制**（`FFmpegRenderer.VIDEO_BITRATE/MAXRATE/BUFSIZE`）：
- NVENC（h264/h265）：`-rc vbr -b:v 8M -maxrate 10M -bufsize 16M`
- libx264/libx265：`-crf 20 -maxrate 10M -bufsize 16M`（capped CRF）
- 由 `_apply_encoder_settings()` classmethod 統一處理單段與多段路徑

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
