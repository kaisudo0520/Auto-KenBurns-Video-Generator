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
| 後端單元測試 | 26 |
| 後端整合測試 | 8 |
| 前端單元測試 | 18 |
| **總計** | **52** |

## Important Design Notes

### Ken-Burns Effect (BPM-Driven)

The system automatically generates continuous Ken-Burns effects based on music BPM analysis:
- Low BPM (<80): Slow, elongated movements (1.5-3 seconds per action)
- Medium BPM (80-140): Standard movements (1-2 seconds)
- High BPM (>140): Fast dynamic movements (0.5-1 second)

Effects automatically switch between: zoom in/out, pan left/right/up/down, diagonal movements, rotation. Each image has fade-in/fade-out transitions.

### Anime Character Protection

The Ken-Burns service (`backend/services/kenburns_service.py`) includes subject detection to protect anime character heads/faces from being cropped. The safe zone calculation prioritizes face and body core regions.

### API Endpoints

All API routes are prefixed with `/api/v1/`:
- `/api/v1/upload/*` - File upload (images/audio)
- `/api/v1/projects/*` - Project CRUD
- `/api/v1/render/*` - Rendering control
- `/api/v1/settings/*` - System settings
- `/ws/render/{job_id}` - WebSocket for real-time progress

## Multi-Agent Framework

This project uses Claude Code's multi-agent collaboration:
- **Coder-PM** - Project manager, coordinates tasks
- **Coder-Plan** - Technical architect, writes specifications
- **Coder-Backend** - Backend developer (business logic)
- **Coder-Bridge** - API designer (front-end/back-end communication)
- **Coder-Database** - Database expert
- **Coder-Frontend** - Frontend developer (uses frontend-design skill)
- **Coder-Test** - Test engineer
- **Coder-Review** - Code review

Usage: `Use the coder-pm agent to build [feature description]`
