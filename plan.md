自動化 Ken-Burns 影片生成系統 (Auto-KenBurns Video Generator) 專案規格書

1. 專案概述 (Project Overview)

本專案旨在開發一款應用程式，能夠將使用者輸入的圖片與音樂，自動串接並生成帶有流暢 Ken-Burns 特效（平移與縮放）的影片。系統將利用電腦視覺技術確保圖片主體（如人物頭部）不被裁切，並透過硬體加速（CUDA/GPU）結合 FFmpeg 提供高效的影片輸出。
為追求極致的用戶體驗與介面現代化，本專案將採用 Web 技術建構前端 UI，並與 Python 後端引擎深度整合。

2. 技術架構 (Technology Stack)

本專案採用 前後端分離 (Decoupled Architecture)，可作為本地桌面端應用或雲端服務部署：

後端 / API 層：Python 3.x + FastAPI

提供 RESTful API 處理任務設定與排程。

提供 WebSocket 實現雙向通訊（用於即時回傳渲染進度）。

前端框架：Vite + Vue 3 (或 React)

提供流暢、現代化且響應式的圖形使用者介面 (GUI)。

前端樣式與 UI 設計：Tailwind CSS

作為核心 CSS 框架，負責全站的響應式佈局 (Grid/Flexbox)、深色主題 (Dark Mode) 以及高質感互動特效 (Transitions/Animations)。

核心影音引擎：FFmpeg (搭配 NVENC/CUDA 硬體加速模組)

影像分析與運算：OpenCV / MediaPipe / YOLO (用於主體偵測與安全區域計算)

音訊分析 (進階計畫使用)：Librosa 或 Aubio (用於波形與節拍偵測)

3. 輸入與輸出規格 (Input & Output Specifications)

3.1 系統輸入 (Inputs)

圖片 (Images)：支援常見格式 (JPG, PNG 等)。數量支援 1 張或多張 (N 張)。

音訊 (Audio)：支援常見格式 (MP3, WAV, AAC 等)。數量為 N 首。

配對邏輯：

1 對 N：1 張圖片搭配 N 首音樂（該圖片的特效持續時間等於 N 首音樂的總長度）。

N 對 N (嚴格對應)：圖片數量必須等於音樂數量。第 1 張圖片的展示時間完全對齊第 1 首音樂的長度，第 2 張圖片完整串接第 2 首音樂，依此類推，直到第 N 張圖片與第 N 首音樂。

3.2 系統輸出 (Outputs)

影片格式：MP4 (H.264/H.265 編碼)

影片長度：精準對齊輸入音樂的總長度。

解析度與幀率：預設為 1080p (1920x1080) 或 4K，60fps / 30fps。

4. 核心功能需求 (Core Functional Requirements)

4.1 影像處理與 Ken-Burns 特效 (Video & Ken-Burns Effects)

特效演算法必須滿足以下自然與流暢的標準：

XYZ 三軸統一運動模型：
動作軌跡不再是單一且機械式的切換，而是透過 XYZ 三軸（縮放、水平平移、垂直平移）同步受 BPM 驅動。每一幀都依據多頻正弦疊加計算出流暢的 3D Lissajous 軌跡，確保動態連貫且永不重複。

邊界碰撞檢測：在任何縮放比例下，計算出的運鏡視窗（Camera Viewport）絕對不可超出原始圖片邊界，避免出現黑邊。

智慧主體偵測 (Subject-Aware Framing)：

導入 AI 偵測模型（如 MediaPipe 或 Haar Cascades）鎖定畫面中的人物/主體。

安全區機制 (Safe Zone)：將人物頭部及軀幹核心設定為高權重保留區，運鏡時允許手腳邊緣被裁切，但嚴禁人物頭部貼齊邊緣或被切出畫面。

自然流暢的運動控制 (Cinematic Movement)：

緩動函數 (Easing Functions)：套用 Ease-In-Out 曲線，避免起步與停止時的機械式突兀感。

時長與速度限制：單一方向的移動持續時間需具備最小閾值（例如：不得小於 2 秒），避免頻繁且短暫的隨機切換（如 0.5 秒換方向）。移動速率（Pixels per second）需限制在合理範圍，避免產生視覺暈眩（過快）或靜止感（過慢）。

4.2 音訊處理 (Audio Processing)

響度正規化 (Audio Normalization)：

整合 FFmpeg 的 loudnorm 濾鏡（符合 EBU R128 標準），確保整個影片專案的輸出音量一致，消除不同歌曲間「忽大忽小」的問題。

無縫轉場 (Audio Transitions)：

音樂首尾必須套用自然的淡入 (Fade-in) 與淡出 (Fade-out)。

多首音樂之間支援 交叉淡化 (Crossfade)，確保音樂切換時的聽覺連貫性。

4.3 輸出與硬體加速 (Hardware Acceleration & API Integration)

硬體加速：自動偵測系統 GPU 環境，若支援 CUDA，則呼叫 FFmpeg 的硬體編碼器（如 h264_nvenc 或 hevc_nvenc）大幅縮短渲染時間。

非同步渲染與進度回報：

後端 (FastAPI) 接收到前端的生成請求後，應將渲染任務放入背景執行 (Background Tasks 或 Celery)。

後端解析 FFmpeg 輸出的日誌，透過 WebSocket 即時將當前幀數、渲染進度 (0% - 100%) 與預估剩餘時間 (ETA) 推送給 Web 前端。

前端接收 WebSocket 數據並流暢渲染進度條。

4.4 前端介面與 UI/UX 設計規範 (UI/UX Design Specifications using Tailwind CSS)

為打造媲美專業影音編輯軟體（如 Premiere, DaVinci）的沉浸式體驗，全站 UI 將以 Tailwind CSS 為核心進行設計：

全域深色主題 (Dark Mode First)：

背景色預設採用深灰/黑階（例如：bg-slate-900 或 bg-gray-950），以突顯圖片與影音內容。

文字顏色使用高對比度的白灰色系（例如：text-slate-100 或 text-gray-300）。

拖曳上傳互動區 (Drag & Drop Zone)：

設計明顯的虛線框上傳區域，使用 utility classes 如 border-2 border-dashed border-slate-600 rounded-2xl p-10。

互動回饋：當檔案拖曳至上方時，觸發背景色改變與邊框高亮（如 hover:bg-slate-800 hover:border-blue-500 transition-all duration-300）。

媒體素材列表 (Media Dashboard)：

卡片式排版：使用 Grid 或 Flexbox 排列上傳的圖片與音樂卡片（grid grid-cols-2 md:grid-cols-4 gap-4）。

每張素材卡片具備圓角與陰影（rounded-lg shadow-md bg-slate-800 overflow-hidden）。

渲染進度與狀態視覺化 (Progress Visualization)：

漸層進度條：利用 Tailwind 的漸層色階呈現渲染進度，營造現代感（例如：bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500）。

脈衝動畫：在等待處理或渲染中，針對特定狀態燈號加入脈衝動畫（animate-pulse）。

按鈕與控制元件 (Buttons & Controls)：

主要行動按鈕 (Primary CTA) 如「開始生成影片」，需具備流暢的縮放與顏色過渡效果（bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 px-6 rounded-xl transform hover:scale-105 active:scale-95 transition-all）。

5. 進階計畫 (Advanced Features - Phase 2)

音波驅動運鏡 (Audio-Reactive Movement)：

節拍偵測 (Beat Detection)：分析音樂檔案的波形與 BPM（每分鐘節拍數）。

動態切點與速率：

在音樂重音或鼓點 (Onset/Drops) 發生時，自動作為圖片切換的觸發點。

音樂節奏快時，自動提高 Ken-Burns 運鏡速度與縮放幅度；節奏慢/舒緩時，運鏡轉為平緩。讓視覺與聽覺達到高度同步。

6. 未來計畫 (Future Roadmap - Phase 3)

字幕合併與內嵌功能 (SRT Subtitle Hardcoding)：

支援讀取單個或多個 .srt 字幕檔。

時間軸自動重構：當存在多個 SRT 檔案對應多首音樂時，系統能依據音樂的先後順序，自動將後續 SRT 檔案的時間軸加上前置音樂的總長度（Time-shifting），合併為單一的主時間軸。

透過 FFmpeg 的 subtitles 濾鏡將字幕直接壓製（Hardcode）進入 MP4 影像軌中，並支援自訂字體、大小與邊框樣式。

桌面端封裝 (Desktop Packaging)：

使用 Tauri 或 PyWebView 將 Vite 前端與 FastAPI 後端封裝為獨立的單一執行檔 (Windows .exe / macOS .dmg)，提供開箱即用的原生桌面體驗。