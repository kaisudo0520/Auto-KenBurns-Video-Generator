# ============================================================
#  Auto-KenBurns 啟動器共用設定與函式（由 start.ps1 / stop.ps1 dot-source）
#  Windows PowerShell 5.1 相容：不使用 &&、??、三元運算子
# ============================================================

$script:DefaultBackendPort  = 8000
$script:DefaultFrontendPort = 5173
$script:ProjectRoot         = Split-Path -Parent $PSScriptRoot
$script:PortsFile           = Join-Path $PSScriptRoot '.running-ports.json'
# 視窗標題維持 ASCII；cmd /k 的命令列會含 "title <prefix><port>"，作為關窗時的身分依據
$script:BackendTitlePrefix  = 'Auto-KenBurns Backend :'
$script:FrontendTitlePrefix = 'Auto-KenBurns Frontend :'

function Write-Step([string]$Message) { Write-Host $Message -ForegroundColor Cyan }
function Write-Warn([string]$Message) { Write-Host $Message -ForegroundColor Yellow }
function Write-Ok([string]$Message)   { Write-Host $Message -ForegroundColor Green }

function Fail([string]$Message) {
    # 不在這裡 pause：由 start.bat / stop.bat 的 pause 統一處理，避免按兩次 Enter
    Write-Host "[錯誤] $Message" -ForegroundColor Red
    exit 1
}

function Resolve-Port([bool]$Provided, [int]$Explicit, [string]$EnvName, [int]$Default) {
    # 優先順序：明確參數 > 環境變數 > 預設值。
    # 明確參數即使是 0 / 負數也原樣回傳，交給 Assert-PortConfig 報錯（不可靜默退回）；
    # 環境變數不是整數時退回預設並警告，避免參數繫結炸出紅字堆疊。
    # 與 vite.config.ts 的 parsePort 差異：兩者都只收 ASCII 十進位；超出 1~65535 時那邊退回預設並警告，這邊由 Assert-PortConfig 直接報錯
    if ($Provided) { return $Explicit }
    $raw = [Environment]::GetEnvironmentVariable($EnvName)
    if ([string]::IsNullOrWhiteSpace($raw)) { return $Default }
    # 只接受 ASCII 十進位數字（與 vite.config.ts 的 parsePort 一致；不接受 '+8010'、'0x1f40' 等）
    $parsed = 0
    if ($raw.Trim() -match '^[0-9]+$' -and [int]::TryParse($raw.Trim(), [ref]$parsed)) { return $parsed }
    Write-Warn "環境變數 $EnvName='$raw' 不是十進位整數，改用預設值 $Default"
    return $Default
}

function Assert-PortConfig([int]$BackendPort, [int]$FrontendPort) {
    foreach ($pair in @(@('後端', $BackendPort), @('前端', $FrontendPort))) {
        $label = $pair[0]; $port = $pair[1]
        if ($port -lt 1 -or $port -gt 65535) { Fail "$label port $port 不在 1~65535 範圍內" }
    }
    if ($BackendPort -eq $FrontendPort) { Fail "後端與前端不能使用同一個 port（$BackendPort）" }
}

function Test-PortListening([int]$Port) {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Get-PortOwners([int]$Port) {
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $conns) { return @() }
    return @($conns | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Get-ProcessInfo([int]$ProcId) {
    $p = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcId" -ErrorAction SilentlyContinue
    if (-not $p) { return $null }
    return [PSCustomObject]@{
        Id          = $ProcId
        Name        = $p.Name
        ParentId    = $p.ParentProcessId
        CommandLine = [string]$p.CommandLine
    }
}

function Get-ChildProcessIds([int]$ParentId) {
    # 排除 conhost.exe：每個主控台視窗都會掛一個，不代表服務仍在執行
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ParentId" -ErrorAction SilentlyContinue
    if (-not $children) { return @() }
    return @($children | Where-Object { $_.Name -ne 'conhost.exe' } | Select-Object -ExpandProperty ProcessId)
}

function Test-ProjectProcess($Info, [string]$Kind) {
    # 只認本專案的服務程序，避免依 port 盲殺無關程式。
    # backend：命令列以 token 邊界含 backend.main:app。刻意不比對專案路徑：跑錯環境（例如 Anaconda 的 uvicorn）
    #          但仍是從本專案根目錄啟動的後端，命令列不含路徑，而那正是需要被停掉的情況。
    #          代價：同機另一份本專案 clone 若占用同一 port 也會被視為本專案。
    # frontend：命令列含 vite（排除 vite preview，它提供的是 dist/ 舊建置）且路徑落在本專案目錄「之下」
    #           （以專案根目錄 + 分隔符比對，避免 click-merge-ken-burn-old 這類姊妹目錄被誤認）
    if (-not $Info) { return $false }
    $cmd = $Info.CommandLine
    if ([string]::IsNullOrEmpty($cmd)) { return $false }
    switch ($Kind) {
        'backend'  { return ($cmd -match '(^|[\s"''])backend\.main:app(\s|"|''|$)') }
        'frontend' {
            $rootWithSep = $script:ProjectRoot.TrimEnd('\') + '\'
            $underRoot = $cmd.ToLower().Contains($rootWithSep.ToLower())
            return (($cmd -match 'vite') -and (-not ($cmd -match '(^|\s)preview(\s|$)')) -and $underRoot)
        }
    }
    return $false
}

function Get-LauncherPattern([string]$TitlePrefix, [int]$Port) {
    # 只比對 start.ps1 實際產生的結構：<cmd.exe> /k title <prefix><port> && ...
    # cmd 前必須是路徑分隔符或字串開頭（"C:\evil\notcmd.exe" 不得匹配）
    $esc = [regex]::Escape("$TitlePrefix$Port")
    return ('^\s*("([^"]*[\\/])?cmd(\.exe)?"|(\S*[\\/])?cmd(\.exe)?)\s+/k\s+title ' + $esc + ' && ')
}

function Test-LauncherWindow($Info, [string]$TitlePrefix, [int]$Port) {
    # start.ps1 用 cmd /k "title <prefix><port> && ..." 開的服務視窗，以錨定的命令列樣式辨識
    if (-not $Info) { return $false }
    if ($Info.Name -ne 'cmd.exe') { return $false }
    return ($Info.CommandLine -match (Get-LauncherPattern $TitlePrefix $Port))
}

function Get-LauncherWindowIds([string]$TitlePrefix, [int]$Port) {
    $cmds = Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" -ErrorAction SilentlyContinue
    if (-not $cmds) { return @() }
    $pattern = Get-LauncherPattern $TitlePrefix $Port
    $ids = @()
    foreach ($c in $cmds) {
        if ([string]$c.CommandLine -match $pattern) { $ids += [int]$c.ProcessId }
    }
    return $ids
}

function Stop-ProcessTree([int]$ProcId) {
    # 回傳 $true 表示成功；失敗時印出 taskkill 的原因，不靜默吞掉
    $output = & cmd.exe /c "taskkill /PID $ProcId /T /F 2>&1"
    if ($LASTEXITCODE -eq 0) { return $true }
    $reason = ($output | Out-String).Trim()
    Write-Warn "  taskkill PID $ProcId 失敗（exit $LASTEXITCODE）：$reason"
    return $false
}

function Close-LauncherWindows([string]$TitlePrefix, [int]$Port) {
    # 關閉服務視窗（以命令列比對，不用視窗標題盲殺）；回傳 $true 表示全部成功或無需關閉
    $ok = $true
    foreach ($winId in (Get-LauncherWindowIds $TitlePrefix $Port)) {
        Write-Host "  關閉服務視窗 PID $winId"
        if (-not (Stop-ProcessTree $winId)) { $ok = $false }
    }
    return $ok
}

function Read-PortsFile {
    if (-not (Test-Path $script:PortsFile)) { return $null }
    try {
        return (Get-Content $script:PortsFile -Raw -Encoding UTF8 | ConvertFrom-Json)
    } catch {
        Write-Warn "無法解析 $($script:PortsFile)，忽略：$($_.Exception.Message)"
        return $null
    }
}

function Write-PortsFile([int]$BackendPort, [int]$FrontendPort, $BackendPid, $FrontendPid) {
    # 回傳 $true 表示成功。先寫同目錄的唯一暫存檔再原子取代，避免讀到寫到一半的 JSON；任何 I/O 失敗都回報
    $data = [ordered]@{
        backendPort  = $BackendPort
        frontendPort = $FrontendPort
        backendPid   = $BackendPid
        frontendPid  = $FrontendPid
        startedAt    = (Get-Date).ToString('o')
    }
    $tmp = Join-Path $PSScriptRoot ('.running-ports.' + [IO.Path]::GetRandomFileName() + '.tmp')
    try {
        $data | ConvertTo-Json | Set-Content -Path $tmp -Encoding UTF8 -ErrorAction Stop
        if (Test-Path $script:PortsFile) {
            # 既有檔：[IO.File]::Replace 對應 Win32 ReplaceFile，為原子取代（Move-Item -Force 在 PS 5.1 是先刪再搬，非原子）。
            # 第三個參數必須用 [NullString]::Value，PowerShell 的 $null 會被轉成空字串而失敗。
            # Replace 對唯讀目標或被其他 handle 開著的目標會失敗（防毒掃描、編輯器），此時退回 Move-Item -Force 並短暫重試
            $replaced = $false
            for ($attempt = 1; $attempt -le 3 -and -not $replaced; $attempt++) {
                try {
                    [IO.File]::Replace($tmp, $script:PortsFile, [NullString]::Value)
                    $replaced = $true
                } catch {
                    try {
                        Move-Item -Path $tmp -Destination $script:PortsFile -Force -ErrorAction Stop
                        $replaced = $true
                    } catch {
                        if ($attempt -lt 3) { Start-Sleep -Milliseconds 300 } else { throw }
                    }
                }
            }
        } else {
            # 首次建立：同目錄 rename
            Move-Item -Path $tmp -Destination $script:PortsFile -ErrorAction Stop
        }
        return $true
    } catch {
        Write-Warn "無法寫入啟動記錄 $($script:PortsFile)：$($_.Exception.Message)"
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
        return $false
    }
}

function Remove-PortsFile {
    # 回傳 $true 表示已刪除或本來就不存在
    if (-not (Test-Path $script:PortsFile)) { return $true }
    try {
        Remove-Item $script:PortsFile -Force -ErrorAction Stop
        return $true
    } catch {
        Write-Warn "無法刪除啟動記錄 $($script:PortsFile)：$($_.Exception.Message)"
        return $false
    }
}

function Test-RecordedServicesAlive($Record) {
    # 記錄中的埠是否仍有本專案服務在跑（用來判斷記錄是否過期）
    if (-not $Record) { return $false }
    foreach ($pair in @(@([int]$Record.backendPort, 'backend'), @([int]$Record.frontendPort, 'frontend'))) {
        foreach ($ownerPid in (Get-PortOwners $pair[0])) {
            if (Test-ProjectProcess (Get-ProcessInfo $ownerPid) $pair[1]) { return $true }
        }
    }
    return $false
}
