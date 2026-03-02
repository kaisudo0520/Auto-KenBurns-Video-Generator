# Ken-Burns Video Generator - Frontend

## 專案概述

這是 Ken-Burns 影片生成器的前端應用程式，使用 Vue 3 + TypeScript + Tailwind CSS 構建。

## 技術堆疊

- **框架**: Vue 3 (Composition API)
- **建置工具**: Vite 5
- **語言**: TypeScript
- **樣式**: Tailwind CSS 3
- **狀態管理**: Pinia
- **HTTP 客戶端**: Axios
- **WebSocket**: 原生 WebSocket API

## 功能特性

- 專案管理（建立、編輯、刪除）
- 圖片拖曳上傳（支援 JPG, PNG, WebP, BMP）
- 音樂拖曳上傳（支援 MP3, WAV, AAC, FLAC, OGG）
- Ken-Burns 效果設定（縮放範圍、速度、緩動函數）
- 輸出設定（解析度、幀率、編碼器）
- 即時渲染進度（WebSocket）
- 系統狀態監控

## 開始使用

### 安裝依賴

```bash
cd frontend
npm install
```

### 開發模式

```bash
npm run dev
```

前端將在 http://localhost:5173 啟動，並自動代理 API 請求到後端 http://localhost:8000 (預設)

如需修改後端端口，請編輯 vite.config.ts 中的 proxy 設定

### 生產構建

```bash
npm run build
```

### 預覽生產構建

```bash
npm run preview
```

## 專案結構

```
frontend/
├── src/
│   ├── components/          # Vue 元件
│   │   ├── common/          # 共用元件
│   │   ├── project/         # 專案相關元件
│   │   ├── render/          # 渲染相關元件
│   │   └── upload/          # 上傳相關元件
│   ├── composables/         # Vue Composables
│   ├── router/              # Vue Router 配置
│   ├── services/            # API 和 WebSocket 服務
│   ├── stores/              # Pinia 狀態管理
│   ├── types/               # TypeScript 類型定義
│   ├── views/               # 頁面視圖
│   ├── App.vue              # 根元件
│   ├── main.ts              # 入口檔案
│   └── style.css            # 全域樣式
├── public/                  # 靜態資源
├── index.html               # HTML 入口
├── package.json
├── tailwind.config.js
├── vite.config.ts
└── tsconfig.json
```

## API 整合

前端通過代理連接到後端 API：

- `/api/*` → `http://localhost:8000/api/v1/*` (可透過 vite.config.ts 修改)
- `/ws/*` → `ws://localhost:8000/ws/*`
- `/uploads/*` → `http://localhost:8000/uploads/*`
- `/output/*` → `http://localhost:8000/output/*`

## 設計系統

### 色彩

- 主背景: `#0a0a0f` (深黑色)
- 次背景: `#12121a` (深灰)
- 強調色: Cyan `#06b6d4`, Violet `#8b5cf6`, Fuchsia `#d946ef`

### 字體

- 顯示字體: Outfit
- 等寬字體: Space Mono

### 元件樣式

- 玻璃效果卡片 (glass-card)
- 漸層按鈕 (btn-primary)
- 拖曳上傳區 (drop-zone)
- 進度條漸層 (progress-gradient)

## 授權

MIT License
