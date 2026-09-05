import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// 連接埠可由環境變數覆寫（scripts/start.ps1 會依此設定），預設後端 8000、前端 5173。
// 埠解析與 scripts/_common.ps1 的 Resolve-Port 相近但不完全相同：
//   兩者都只接受 ASCII 十進位整數；非整數時都退回預設並警告；
//   超出 1~65535 時這裡退回預設並警告，PowerShell 端則由 Assert-PortConfig 直接報錯中止
function parsePort(envName: string, fallback: number): number {
  const raw = process.env[envName]
  if (raw === undefined || raw.trim() === '') return fallback
  // 只接受十進位整數（與 PowerShell 端 [int]::TryParse 一致，不接受 0x1f40 / 8e3 之類寫法）
  const port = /^\d+$/.test(raw.trim()) ? Number(raw) : NaN
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    console.warn(`[vite.config] 環境變數 ${envName}='${raw}' 不是有效的 port，改用預設值 ${fallback}`)
    return fallback
  }
  return port
}

const backendPort = parsePort('BACKEND_PORT', 8000)
const frontendPort = parsePort('FRONTEND_PORT', 5173)
// proxy 目標用 127.0.0.1 而非 localhost：uvicorn 只綁 IPv4，避免 localhost 被解析成 ::1 時連線被拒
const backendHttp = `http://127.0.0.1:${backendPort}`
const backendWs = `ws://127.0.0.1:${backendPort}`

// dev 與 preview 共用同一份 proxy，讓 `vite preview` 也能在本機直接連到後端。
// /health 也轉發：一鍵啟動器用它比對「直連後端」與「經前端 proxy」拿到的 instance_id 是否相同
const backendProxy = {
  '/health': {
    target: backendHttp,
    changeOrigin: true,
  },
  '/api': {
    target: backendHttp,
    changeOrigin: true,
  },
  '/ws': {
    target: backendWs,
    ws: true,
  },
  '/uploads': {
    target: backendHttp,
    changeOrigin: true,
  },
  '/output': {
    target: backendHttp,
    changeOrigin: true,
  },
}

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: frontendPort,
    proxy: backendProxy,
  },
  preview: {
    // 刻意不沿用 FRONTEND_PORT：preview 提供的是 dist/ 舊建置，若與 dev 同埠，
    // 一鍵啟動器可能把殘留的 preview 當成可沿用的前端
    port: parsePort('PREVIEW_PORT', 4173),
    proxy: backendProxy,
  },
})
