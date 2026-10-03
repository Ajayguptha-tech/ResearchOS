$ErrorActionPreference = "Continue"

Write-Host "--- Stopping existing servers on ports 8000 and 3000 ---"
$ports = @(8000, 3000, 3001)
foreach ($p in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
    if ($connections) {
        foreach ($conn in $connections) {
            try {
                $procId = $conn.OwningProcess
                if ($procId -gt 4) {
                    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                    Write-Host "Stopped process $procId on port $p"
                }
            } catch {}
        }
    }
}

Start-Sleep -Seconds 2

$rootDir = "C:\Users\lenovo\Desktop\master\ResearchOS"
$backendDir = "$rootDir\backend"
$frontendDir = "$rootDir\frontend"
$logsDir = "$rootDir\.freebuff"

if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

$backendOutLog = "$logsDir\backend-stdout.log"
$backendErrLog = "$logsDir\backend-stderr.log"
$frontendOutLog = "$logsDir\preview.log"
$frontendErrLog = "$logsDir\preview.log.err"

$pythonExe = "$backendDir\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python.exe"
}

Write-Host "Starting Backend with $pythonExe on port 8000..."
$backendProcess = Start-Process `
    -FilePath $pythonExe `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $backendDir `
    -RedirectStandardOutput $backendOutLog `
    -RedirectStandardError $backendErrLog `
    -WindowStyle Hidden `
    -PassThru

Write-Host "Backend started with PID $($backendProcess.Id)"

Write-Host "Starting Frontend (Next.js) on port 3000..."
$frontendProcess = Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm", "run", "dev" `
    -WorkingDirectory $frontendDir `
    -RedirectStandardOutput $frontendOutLog `
    -RedirectStandardError $frontendErrLog `
    -WindowStyle Hidden `
    -PassThru

Write-Host "Frontend started with PID $($frontendProcess.Id)"

Write-Host "Waiting for servers to become ready..."
$backendReady = $false
$frontendReady = $false

for ($i = 1; $i -le 15; $i++) {
    Start-Sleep -Seconds 1
    if (-not $backendReady) {
        $bConn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
        if ($bConn) {
            $backendReady = $true
            Write-Host "Backend is listening on port 8000 after ${i}s"
        }
    }
    if (-not $frontendReady) {
        $fConn = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
        if ($fConn) {
            $frontendReady = $true
            Write-Host "Frontend is listening on port 3000 after ${i}s"
        }
    }
    if ($backendReady -and $frontendReady) {
        break
    }
}

Write-Host "`n=== Server Status ==="
Write-Host "Backend (8000): $(if ($backendReady) {'RUNNING'} else {'PENDING/ERROR - check .freebuff\backend-stderr.log'})"
Write-Host "Frontend (3000): $(if ($frontendReady) {'RUNNING'} else {'PENDING/ERROR - check .freebuff\preview.log.err'})"
