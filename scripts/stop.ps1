# ============================================================
#  Auto-KenBurns 停止腳本（Windows PowerShell 5.1 相容）
#  只結束本專案的服務程序（依命令列驗證身分），不依 port 盲殺。
#  連接埠優先順序：參數 > start.ps1 寫下的 .running-ports.json（實際執行中服務的事實來源）> 環境變數 > 預設值
# ============================================================
param(
    [int]$BackendPort = 0,
    [int]$FrontendPort = 0
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$Host.UI.RawUI.WindowTitle = 'Auto-KenBurns 停止'

. (Join-Path $PSScriptRoot '_common.ps1')

# 優先序：明確參數 > 啟動記錄（實際執行中服務的事實來源）> 環境變數 > 預設值
$record = Read-PortsFile
$envBackend  = Resolve-Port $false 0 'BACKEND_PORT'  $DefaultBackendPort
$envFrontend = Resolve-Port $false 0 'FRONTEND_PORT' $DefaultFrontendPort
$fallbackBackend  = $envBackend
$fallbackFrontend = $envFrontend
$backendProvided  = $PSBoundParameters.ContainsKey('BackendPort')
$frontendProvided = $PSBoundParameters.ContainsKey('FrontendPort')
if ($record) {
    if ($record.backendPort)  { $fallbackBackend  = [int]$record.backendPort }
    if ($record.frontendPort) { $fallbackFrontend = [int]$record.frontendPort }
    Write-Host "讀取上次啟動記錄：後端 $fallbackBackend、前端 $fallbackFrontend"
    # 只對「未明確指定、實際會採用記錄」的欄位提示環境變數衝突
    $conflicts = @()
    if (-not $backendProvided  -and $env:BACKEND_PORT  -and $fallbackBackend  -ne $envBackend)  { $conflicts += "BACKEND_PORT=$envBackend" }
    if (-not $frontendProvided -and $env:FRONTEND_PORT -and $fallbackFrontend -ne $envFrontend) { $conflicts += "FRONTEND_PORT=$envFrontend" }
    if ($conflicts.Count -gt 0) {
        Write-Warn "環境變數 $($conflicts -join '、') 與啟動記錄不同，以記錄為準；要停環境變數那組請明確傳參數"
    }
}
$BackendPort  = if ($backendProvided)  { $BackendPort }  else { $fallbackBackend }
$FrontendPort = if ($frontendProvided) { $FrontendPort } else { $fallbackFrontend }
Assert-PortConfig $BackendPort $FrontendPort

$script:HadFailure = $false

function Stop-ProjectService([int]$Port, [string]$Kind, [string]$Label) {
    Write-Host "停止$Label（port $Port）..."
    $owners = Get-PortOwners $Port
    if ($owners.Count -eq 0) {
        Write-Host "  port $Port 沒有監聽中的程式"
        return
    }
    $attempted = $false
    $unverifiable = $false
    foreach ($ownerPid in $owners) {
        if ($ownerPid -le 4) {
            # PID 0 / 4 為系統保留（HTTP.sys、WinNAT 等），taskkill 必定失敗
            Write-Warn "  port $Port 由系統程序（PID $ownerPid）持有，無法停止，略過"
            continue
        }
        $info = Get-ProcessInfo $ownerPid
        if (-not $info) {
            # 取不到程序資料（CIM 失敗或權限不足）不等於「確認不是本專案」：視為無法驗證，稍後若埠仍在監聽則計為失敗
            Write-Warn "  無法取得 PID $ownerPid 的程序資料，無法驗證身分，略過"
            $unverifiable = $true
            continue
        }
        if (-not (Test-ProjectProcess $info $Kind)) {
            Write-Warn "  port $Port 的占用者 PID $ownerPid（$($info.Name)）不是本專案的$Label，略過不殺"
            continue
        }
        Write-Host "  結束 PID $ownerPid（$($info.Name)）及其子程序"
        $attempted = $true
        if (-not (Stop-ProcessTree $ownerPid)) { $script:HadFailure = $true }
    }
    if ($attempted -or $unverifiable) {
        Start-Sleep -Milliseconds 500
        if (Test-PortListening $Port) {
            Write-Warn "  port $Port 仍在監聽，${Label}可能未完全停止"
            $script:HadFailure = $true
        } elseif ($attempted) {
            Write-Host "  ${Label}已停止"
        }
    }
}

Stop-ProjectService -Port $BackendPort  -Kind 'backend'  -Label '後端'
Stop-ProjectService -Port $FrontendPort -Kind 'frontend' -Label '前端'

# 關閉 start.ps1 用 cmd /k 開的服務視窗（服務結束後視窗仍會留著）；以命令列比對，失敗計入
if (-not (Close-LauncherWindows $BackendTitlePrefix  $BackendPort))  { $script:HadFailure = $true }
if (-not (Close-LauncherWindows $FrontendTitlePrefix $FrontendPort)) { $script:HadFailure = $true }

if ($script:HadFailure) {
    # 記錄保留，讓使用者（例如提權後）重跑 stop.bat 仍能找到正確的埠
    Fail '部分服務未能停止，請依上方訊息處理（可能需要以系統管理員身分執行 stop.bat）。啟動記錄已保留。'
}

# 只在「本次停的就是記錄中的那組」時刪除記錄，避免用明確參數停另一組服務時誤刪；刪除失敗也要回報
if ($record) {
    if ([int]$record.backendPort -eq $BackendPort -and [int]$record.frontendPort -eq $FrontendPort) {
        if (-not (Remove-PortsFile)) { Fail '服務已停止，但無法刪除啟動記錄，請手動刪除 scripts\.running-ports.json。' }
    } else {
        Write-Warn "本次停止的 port（$BackendPort / $FrontendPort）與啟動記錄不同，記錄保留"
    }
}
Write-Ok '完成。'
Start-Sleep -Seconds 2
exit 0
