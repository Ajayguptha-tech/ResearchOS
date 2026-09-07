$ErrorActionPreference = "SilentlyContinue"

# Check if backend is running on port 8000
$backendPort = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if (-not $backendPort) {
    Write-Host "Starting backend on port 8000..."
    Start-Process -FilePath 'python' -ArgumentList '-m','uvicorn','app.main:app','--reload','--host','127.0.0.1','--port','8000' -WorkingDirectory 'C:\Users\LENOVO\Desktop\master\ResearchOS\backend' -WindowStyle Hidden
} else {
    Write-Host "Backend already running on port 8000"
}

Start-Sleep -Seconds 3

# Check if frontend is running on port 3000 or 3004
$frontendPort3000 = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
$frontendPort3004 = Get-NetTCPConnection -LocalPort 3004 -ErrorAction SilentlyContinue

if (-not $frontendPort3000 -and -not $frontendPort3004) {
    Write-Host "Starting frontend..."
    Set-Location 'C:\Users\LENOVO\Desktop\master\ResearchOS\frontend'
    Start-Process -FilePath 'node' -ArgumentList 'node_modules\next\dist\bin\next','dev' -WorkingDirectory 'C:\Users\LENOVO\Desktop\master\ResearchOS\frontend' -WindowStyle Hidden
} else {
    if ($frontendPort3000) { Write-Host "Frontend already running on port 3000" }
    if ($frontendPort3004) { Write-Host "Frontend already running on port 3004" }
}

Start-Sleep -Seconds 5

# Verify
$backendCheck = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
$frontendCheck = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
$frontendCheck4 = Get-NetTCPConnection -LocalPort 3004 -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== Server Status ==="
Write-Host "Backend (8000): $(if ($backendCheck) {'RUNNING'} else {'NOT RUNNING'})"
Write-Host "Frontend (3000): $(if ($frontendCheck) {'RUNNING'} else {'NOT RUNNING'})"
Write-Host "Frontend (3004): $(if ($frontendCheck4) {'RUNNING'} else {'NOT RUNNING'})"
