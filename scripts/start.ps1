# ============================================================
#  Auto-KenBurns 一鍵啟動（Windows PowerShell 5.1 相容）
#  由根目錄 start.bat 呼叫；也可直接執行：
#    powershell -ExecutionPolicy Bypass -File scripts\start.ps1 [-BackendPort 8000] [-FrontendPort 5173] [-WaitLimitSeconds 90]
#  連接埠優先順序：參數 > 環境變數 BACKEND_PORT / FRONTEND_PORT > 預設值（見 _common.ps1）
# ============================================================
param(
    [int]$BackendPort = 0,
    [int]$FrontendPort = 0,
    [int]$WaitLimitSeconds = 90
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$Host.UI.RawUI.WindowTitle = 'Auto-KenBurns 啟動器'

. (Join-Path $PSScriptRoot '_common.ps1')

$BackendPort  = Resolve-Port $PSBoundParameters.ContainsKey('BackendPort')  $BackendPort  'BACKEND_PORT'  $DefaultBackendPort
$FrontendPort = Resolve-Port $PSBoundParameters.ContainsKey('FrontendPort') $FrontendPort 'FRONTEND_PORT' $DefaultFrontendPort
Assert-PortConfig $BackendPort $FrontendPort
if ($WaitLimitSeconds -lt 1) { Fail "WaitLimitSeconds 必須 >= 1（收到 $WaitLimitSeconds）" }

$Root        = $ProjectRoot
$VenvDir     = Join-Path $Root 'backend\venv'
$VenvPy      = Join-Path $VenvDir 'Scripts\python.exe'
$ReqFile     = Join-Path $Root 'backend\requirements.txt'
$FrontendDir = Join-Path $Root 'frontend'
Set-Location $Root

# 本次啟動的服務視窗（cmd /k）Process 物件；沿用既有服務時為 $null
$startedBackend  = $null
$startedFrontend = $null

function Test-BackendPackages {
    # 以 cmd 包一層把 stderr 丟掉，避免 PowerShell 5.1 把原生程式的 stderr 包成 ErrorRecord
    & cmd.exe /c "`"$VenvPy`" -c `"import uvicorn, fastapi, imgutils`" >nul 2>&1"
    return ($LASTEXITCODE -eq 0)
}

function Test-PythonVersion {
    & cmd.exe /c "`"$VenvPy`" -c `"import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)`" >nul 2>&1"
    return ($LASTEXITCODE -eq 0)
}

function Test-ExistingService([int]$Port, [string]$Kind, [string]$Label) {
    # 啟動前檢查：port 空著回 $false；「全部」占用者都是本專案服務才回 $true（沿用）；
    # 只要有任何非本專案或無法驗證的占用者（例如 Vite 綁 ::1、另一程式綁 127.0.0.1 同一 port）就報錯。
    # 此時尚未啟動任何程序，Fail 不會留下孤兒
    if (-not (Test-PortListening $Port)) { return $false }
    $projectOwners = @(); $foreignOwner = $null; $foreignInfo = $null; $unverifiable = @()
    foreach ($ownerPid in (Get-PortOwners $Port)) {
        $info = Get-ProcessInfo $ownerPid
        if (-not $info) { $unverifiable += $ownerPid; continue }
        if (Test-ProjectProcess $info $Kind) { $projectOwners += $ownerPid; continue }
        if (-not $foreignOwner) { $foreignOwner = $ownerPid; $foreignInfo = $info }
    }
    if ($foreignOwner) {
        $hint = ''
        if ($Kind -eq 'frontend' -and $foreignInfo.CommandLine -match 'vite') {
            # 是 Vite 但路徑對不上：可能是從 subst 磁碟機、符號連結或 UNC 路徑啟動的本專案前端
            $hint = "（該程序是 Vite，但命令列路徑不在 $ProjectRoot 之下；若是從 subst / 符號連結 / UNC 路徑啟動的本專案前端，請改從同一路徑啟動或先手動停止它）"
        }
        Fail "port $Port 被非本專案的程式占用（PID $foreignOwner，$($foreignInfo.Name)）$hint。請停止該程式，或改用 BACKEND_PORT / FRONTEND_PORT 指定其他 port"
    }
    if ($unverifiable.Count -gt 0) {
        Fail "port $Port 的占用者 PID $($unverifiable -join ', ') 無法取得程序資料，無法驗證身分。請手動確認後停止該程式，或改用其他 port"
    }
    Write-Warn "port $Port 已有本專案的${Label}在執行（PID $($projectOwners -join ', ')），沿用。若要重啟請先執行 stop.bat"
    return $true
}

function Test-ServiceAlive($Proc, [bool]$Reused, [int]$Port) {
    # 本次啟動：cmd /k 視窗在裡面的服務崩潰後仍會留著，因此以「視窗是否還有子程序（排除 conhost）」判斷。
    # 沿用既有服務：沒有 Process 物件，改以「port 是否仍在監聽」判斷
    if ($Reused) { return (Test-PortListening $Port) }
    if (-not $Proc) { return $false }
    if ($Proc.HasExited) { return $false }
    return ((Get-ChildProcessIds $Proc.Id).Count -gt 0)
}

function Get-RemainingSeconds($Stopwatch, [double]$DeadlineSeconds) {
    # 距離絕對 deadline（以 Stopwatch 秒數表示）還剩多少秒，最小 0
    return [Math]::Max(0.0, $DeadlineSeconds - $Stopwatch.Elapsed.TotalSeconds)
}

function Get-HttpBody([int]$Port, [string]$Path, $Stopwatch, [double]$DeadlineSeconds) {
    # uvicorn 綁 0.0.0.0（IPv4）、Vite 綁 ::1（IPv6），PowerShell 5.1 解析 localhost 不會自動退回，兩個位址都試。
    # 每個位址的逾時各自依「距 deadline 的剩餘秒數」重新計算（上限 2 秒），剩餘不足 1 秒就不再發出請求。
    # 回傳回應內容字串；全部失敗回傳 $null
    foreach ($h in @('127.0.0.1', '[::1]')) {
        $remaining = Get-RemainingSeconds $Stopwatch $DeadlineSeconds
        if ($remaining -lt 1) { break }
        # 向下取整：剩 1.9 秒只給 1 秒逾時，單次請求不會突破 deadline（Invoke-WebRequest 的逾時粒度為整數秒）
        $t = [int][Math]::Min(2, [Math]::Floor($remaining))
        try {
            $resp = Invoke-WebRequest -UseBasicParsing -TimeoutSec $t -Uri "http://$h`:$Port$Path"
            return [string]$resp.Content
        } catch {}
    }
    return $null
}

function Test-HttpOnce([int]$Port, [string]$Path, $Stopwatch, [double]$DeadlineSeconds) {
    return ($null -ne (Get-HttpBody $Port $Path $Stopwatch $DeadlineSeconds))
}

function Sleep-UntilDeadline($Stopwatch, [double]$DeadlineSeconds, [int]$Seconds) {
    $remaining = Get-RemainingSeconds $Stopwatch $DeadlineSeconds
    $ms = [int][Math]::Floor([Math]::Min($Seconds * 1000, [Math]::Max(0, $remaining * 1000)))
    if ($ms -gt 0) { Start-Sleep -Milliseconds $ms }
}

function Test-BothAlive {
    # 兩個服務都必須存活（包含已經 ready 的那個），回傳最先發現死亡的服務名稱或 $null
    if (-not (Test-ServiceAlive $startedBackend $reuseBackend $BackendPort)) { return '後端' }
    if (-not (Test-ServiceAlive $startedFrontend $reuseFrontend $FrontendPort)) { return '前端' }
    return $null
}

function Wait-Services($Stopwatch, [double]$DeadlineSeconds) {
    # 以絕對 deadline 同時等待兩個服務；每次 HTTP 探測的逾時受剩餘時間限制。
    # 寬限期後每輪先檢查「兩個」服務存活（含已 ready 者）再探測：本次啟動的服務視窗內程序已結束、
    # 或沿用的服務不再監聽，就立即失敗；成功返回前再驗證一次存活
    $backendReady = $false; $frontendReady = $false
    $graceSeconds = 3   # Start-Process 後給 cmd 一點時間 spawn 出 python / node，避免誤判為已崩潰
    $iteration = 0
    while ((Get-RemainingSeconds $Stopwatch $DeadlineSeconds) -gt 0) {
        $iteration++
        # 寬限：牆鐘至少 3 秒且至少跑過一輪探測（慢機上單輪探測可能就超過 3 秒）
        if ($Stopwatch.Elapsed.TotalSeconds -ge $graceSeconds -and $iteration -ge 2) {
            $dead = Test-BothAlive
            if ($dead) {
                Write-Warn "${dead}程序已結束（啟動失敗或沿用的服務已停止）。"
                return @{ Backend = ($backendReady -and $dead -ne '後端'); Frontend = ($frontendReady -and $dead -ne '前端') }
            }
        }
        if (-not $backendReady -and (Test-HttpOnce $BackendPort '/health' $Stopwatch $DeadlineSeconds)) {
            $backendReady = $true; Write-Host "後端就緒（$([int]$Stopwatch.Elapsed.TotalSeconds) 秒）。"
        }
        if (-not $frontendReady -and (Test-HttpOnce $FrontendPort '/' $Stopwatch $DeadlineSeconds)) {
            $frontendReady = $true; Write-Host "前端就緒（$([int]$Stopwatch.Elapsed.TotalSeconds) 秒）。"
        }
        if ($backendReady -and $frontendReady) {
            $dead = Test-BothAlive
            if ($dead) {
                Write-Warn "${dead}在就緒後隨即結束。"
                return @{ Backend = ($dead -ne '後端'); Frontend = ($dead -ne '前端') }
            }
            return @{ Backend = $true; Frontend = $true }
        }
        Sleep-UntilDeadline $Stopwatch $DeadlineSeconds 1
    }
    if (-not $backendReady)  { Write-Warn "後端在 $WaitLimitSeconds 秒內未回應。" }
    if (-not $frontendReady) { Write-Warn "前端在 $WaitLimitSeconds 秒內未回應。" }
    return @{ Backend = $backendReady; Frontend = $frontendReady }
}

function Get-InstanceId([int]$Port, $Stopwatch, [double]$DeadlineSeconds) {
    # 從 /health 取出 instance_id；取不到回傳 $null
    $body = Get-HttpBody $Port '/health' $Stopwatch $DeadlineSeconds
    if (-not $body) { return $null }
    try {
        $json = $body | ConvertFrom-Json
        if ($json.instance_id) { return [string]$json.instance_id }
    } catch {}
    return $null
}

function Test-ProxyPairing($Stopwatch, [double]$DeadlineSeconds) {
    # 配對階段有自己的絕對 deadline（由呼叫端決定）。在期限內重試：直連後端與經前端 proxy 的 /health
    # 必須回同一個 instance_id。看到不一致時隔 1 秒再取樣一次，連續兩次不同才判 mismatch
    # （沿用 --reload 後端時，存檔重啟會換 instance_id，避免取樣落在重啟前後被誤判）。
    # 每輪同時檢查兩個服務存活。回傳 'ok' / 'mismatch' / 'unreachable' / 'died'
    $mismatchStreak = 0
    while ((Get-RemainingSeconds $Stopwatch $DeadlineSeconds) -gt 0) {
        if (Test-BothAlive) { return 'died' }
        $direct  = Get-InstanceId $BackendPort  $Stopwatch $DeadlineSeconds
        $proxied = Get-InstanceId $FrontendPort $Stopwatch $DeadlineSeconds
        if ($direct -and $proxied) {
            if ($direct -eq $proxied) { return 'ok' }
            $mismatchStreak++
            Write-Warn "直連後端 instance_id=$direct，經前端 proxy 取得 instance_id=$proxied（第 $mismatchStreak 次不一致）"
            if ($mismatchStreak -ge 2) { return 'mismatch' }
        } else {
            $mismatchStreak = 0
        }
        Sleep-UntilDeadline $Stopwatch $DeadlineSeconds 1
    }
    # 期限內曾觀察到不一致但來不及二次確認：回報不一致比「取不到」更貼近實際現象
    if ($mismatchStreak -ge 1) { return 'mismatch' }
    return 'unreachable'
}

function Stop-StartedProcesses {
    # 只清理本次啟動、且命令列仍能辨識為本啟動器服務視窗的程序（避免 PID 重用誤殺）；不動 ports 檔
    foreach ($entry in @(@($startedBackend, $BackendTitlePrefix, $BackendPort), @($startedFrontend, $FrontendTitlePrefix, $FrontendPort))) {
        $proc = $entry[0]
        if (-not $proc -or $proc.HasExited) { continue }
        $info = Get-ProcessInfo $proc.Id
        if (Test-LauncherWindow $info $entry[1] $entry[2]) {
            Write-Host "  結束本次啟動的服務視窗 PID $($proc.Id) 及其子程序"
            Stop-ProcessTree $proc.Id | Out-Null
        } else {
            Write-Warn "  PID $($proc.Id) 已不是本啟動器的服務視窗，略過"
        }
    }
}

function Get-StopHint {
    # 啟動失敗時尚未寫入記錄，stop.bat 不帶參數會退回預設埠；給出可直接執行的指令
    return "stop.bat -BackendPort $BackendPort -FrontendPort $FrontendPort"
}

function Fail-AfterStart([string]$Message) {
    # 啟動後失敗：統一印出可直接執行的 stop 指令（此時尚未寫入記錄，stop.bat 不帶參數會退回預設埠）
    Write-Host ''
    Write-Host "[錯誤] $Message" -ForegroundColor Red
    Write-Host '正在清理本次啟動的程序 ...'
    Stop-StartedProcesses
    Write-Host "若仍有服務在執行，請執行「$(Get-StopHint)」停止。" -ForegroundColor Yellow
    exit 1
}

Write-Host ''
Write-Host ' ============================================'
Write-Host '  Auto-KenBurns 一鍵啟動'
Write-Host "  後端 port: $BackendPort   前端 port: $FrontendPort"
Write-Host ' ============================================'
Write-Host ''

# ---------- [1/5] Python 虛擬環境 ----------
if (-not (Test-Path $VenvPy)) {
    Write-Step '[1/5] 找不到虛擬環境，正在建立 backend\venv ...'
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv $VenvDir }
    if (-not (Test-Path $VenvPy)) {
        if (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv $VenvDir }
    }
    if (-not (Test-Path $VenvPy)) { Fail '建立虛擬環境失敗，請確認已安裝 Python 3.10 以上版本。' }
}
if (-not (Test-PythonVersion)) {
    Fail "backend\venv 的 Python 版本低於 3.10，請刪除 backend\venv 後以 Python 3.10 以上版本重新執行。"
}
if (-not (Test-BackendPackages)) {
    Write-Step '[1/5] 虛擬環境缺少必要套件（uvicorn / fastapi / imgutils），安裝 requirements（首次執行需數分鐘）...'
    & $VenvPy -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { Write-Warn 'pip 升級失敗，繼續嘗試安裝依賴。' }
    & $VenvPy -m pip install -r $ReqFile
    if ($LASTEXITCODE -ne 0) { Fail '安裝後端依賴失敗。' }
    if (-not (Test-BackendPackages)) { Fail '套件安裝後仍無法載入，請手動檢查 backend\requirements.txt。' }
}
Write-Step "[1/5] Python 虛擬環境 OK（$VenvPy）"

# ---------- [2/5] 前端依賴 ----------
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Fail '找不到 npm，請先安裝 Node.js（https://nodejs.org/）。'
}
if (-not (Test-Path (Join-Path $FrontendDir 'node_modules'))) {
    Write-Step '[2/5] 找不到 frontend\node_modules，執行 npm install（首次執行需數分鐘）...'
    Push-Location $FrontendDir
    & npm install
    $npmExit = $LASTEXITCODE
    Pop-Location
    if ($npmExit -ne 0) { Fail 'npm install 失敗。' }
}
Write-Step '[2/5] 前端依賴 OK'

# ---------- [3/5] 啟動前檢查（尚未啟動任何程序，任何失敗都不會留下孤兒） ----------
$reuseBackend  = Test-ExistingService $BackendPort  'backend'  '後端'
$reuseFrontend = Test-ExistingService $FrontendPort 'frontend' '前端'

if ($reuseFrontend -and -not $reuseBackend) {
    # 既有 Vite 的 proxy 目標在它啟動時就固定了，無法保證指向本次要新啟動的後端
    Fail "port $FrontendPort 的既有前端無法確認指向本次的後端 port $BackendPort。請先執行「$(Get-StopHint)」再重新啟動"
}

$record = Read-PortsFile
if ($record) {
    $recBackend = [int]$record.backendPort; $recFrontend = [int]$record.frontendPort
    if ($recBackend -ne $BackendPort -or $recFrontend -ne $FrontendPort) {
        if (Test-RecordedServicesAlive $record) {
            Fail "上次以 port $recBackend / $recFrontend 啟動的服務仍在執行。請先執行「stop.bat」（會讀取該記錄），或改用相同的 port"
        }
        Write-Warn "上次啟動記錄（$recBackend / $recFrontend）已過期，將覆寫"
    } elseif ($reuseBackend -and $reuseFrontend) {
        Write-Host "沿用的前後端與上次啟動記錄一致（$recBackend / $recFrontend）"
    }
} elseif ($reuseBackend -and $reuseFrontend) {
    Write-Warn '沿用既有前後端，但找不到啟動記錄，無法確認兩者配對；稍後會以 proxy 探測驗證'
}
Write-Step '[3/5] 啟動前檢查 OK'

# ---------- [4/5] 啟動服務 ----------
# 前端的 /api、/ws、/uploads、/output 全部走 Vite proxy，目標由 BACKEND_PORT 決定（見 vite.config.ts）
$env:BACKEND_PORT  = "$BackendPort"
$env:FRONTEND_PORT = "$FrontendPort"

if (-not $reuseBackend) {
    Write-Step "[4/5] 啟動後端 http://localhost:$BackendPort ..."
    # 注入 instance_id，讓後端（即使日後改成 --workers N）所有 worker 的 /health 回同一個識別
    $env:KENBURNS_INSTANCE_ID = [guid]::NewGuid().ToString('N')
    $backendCmd = "/k title $BackendTitlePrefix$BackendPort && `"$VenvPy`" -m uvicorn backend.main:app --host 0.0.0.0 --port $BackendPort"
    try {
        $startedBackend = Start-Process -FilePath 'cmd.exe' -WorkingDirectory $Root -ArgumentList $backendCmd -PassThru -ErrorAction Stop
    } catch {
        Fail-AfterStart "無法啟動後端視窗：$($_.Exception.Message)"
    }
}
if (-not $reuseFrontend) {
    Write-Step "[4/5] 啟動前端 http://localhost:$FrontendPort ..."
    $frontendCmd = "/k title $FrontendTitlePrefix$FrontendPort && npm run dev -- --port $FrontendPort --strictPort"
    try {
        $startedFrontend = Start-Process -FilePath 'cmd.exe' -WorkingDirectory $FrontendDir -ArgumentList $frontendCmd -PassThru -ErrorAction Stop
    } catch {
        Fail-AfterStart "無法啟動前端視窗：$($_.Exception.Message)"
    }
}

# ---------- [5/5] 等待就緒並驗證前後端配對 ----------
Write-Host ''
Write-Host "等待服務就緒（最多 $WaitLimitSeconds 秒；之後的前後端配對檢查另計，最多再等 $([Math]::Max(10, $WaitLimitSeconds)) 秒）..."
$waitClock = [System.Diagnostics.Stopwatch]::StartNew()
$readyDeadline = [double]$WaitLimitSeconds
$ready = Wait-Services $waitClock $readyDeadline
if (-not ($ready.Backend -and $ready.Frontend)) {
    $failed = @()
    if (-not $ready.Backend)  { $failed += '後端' }
    if (-not $ready.Frontend) { $failed += '前端' }
    Fail-AfterStart "$($failed -join '、') 未能就緒，請查看對應的服務視窗中的錯誤訊息。"
}

# 使用者實際走的是前端 proxy 路徑：比對「直連後端」與「經前端 proxy」的 /health instance_id，
# 確認前端 proxy 指向的就是本次選定的後端（而非其他埠上另一個相容的後端）。
# 配對階段有獨立的 deadline：就緒剩餘時間與 10 秒取大者（服務剛就緒，proxy 需要幾秒暖機）
$pairingDeadline = $waitClock.Elapsed.TotalSeconds + [Math]::Max(10.0, (Get-RemainingSeconds $waitClock $readyDeadline))
switch (Test-ProxyPairing $waitClock $pairingDeadline) {
    'ok'          { Write-Host '前端 proxy 指向本次的後端（instance_id 一致）。' }
    'mismatch'    { Fail-AfterStart "前端 port $FrontendPort 的 proxy 指向的不是後端 port $BackendPort 上的程序（若沿用的是手動以 --workers N 啟動且未設 KENBURNS_INSTANCE_ID 的後端，各 worker 的 instance_id 不同，也會出現此結果）。請先停止再重新啟動" }
    'unreachable' { Fail-AfterStart "無法經前端 port $FrontendPort 的 proxy 取得後端 /health。若是沿用既有前端，請先停止再重新啟動" }
    'died'        { Fail-AfterStart '配對檢查期間有服務結束，請查看服務視窗的錯誤訊息。' }
}

$backendPid  = if ($startedBackend)  { $startedBackend.Id }  else { $null }
$frontendPid = if ($startedFrontend) { $startedFrontend.Id } else { $null }
if (-not (Write-PortsFile -BackendPort $BackendPort -FrontendPort $FrontendPort -BackendPid $backendPid -FrontendPid $frontendPid)) {
    # 服務已通過就緒與配對驗證，不因記帳用的 JSON 寫不進去就拆掉；保留服務、給出明確的停止指令，並以非零碼結束讓 BAT 暫停顯示
    Write-Host ''
    Write-Host '[錯誤] 無法寫入啟動記錄。服務已啟動且驗證正常，但 stop.bat 不帶參數時將不知道本次使用的 port。' -ForegroundColor Red
    Write-Host "要停止時請執行「$(Get-StopHint)」。" -ForegroundColor Yellow
    exit 1
}

Write-Host ''
Write-Host "開啟瀏覽器 http://localhost:$FrontendPort ..."
Start-Process "http://localhost:$FrontendPort"
Write-Host ''
Write-Ok '服務已啟動。要關閉時請執行 stop.bat，或直接關閉兩個服務視窗。'
Start-Sleep -Seconds 3
exit 0
