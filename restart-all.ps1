param(
    [string]$Port = "8000",
    [string]$Tunnel = "acuviz"
)

Write-Host "=== Acupuncture AI - Restart All ===" -ForegroundColor Yellow

# Kill old processes
Write-Host "Stopping old processes..." -ForegroundColor Cyan
Get-Process -Name "python" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 1

# Start backend
Write-Host "Starting backend on port $Port..." -ForegroundColor Green
$backendDir = Join-Path $PSScriptRoot "backend"
$venvActivate = Join-Path $backendDir ".venv\Scripts\Activate.ps1"

$initScript = @"
& "$venvActivate"
python -m uvicorn main:app --host 0.0.0.0 --port $Port
"@

Start-Process -FilePath "pwsh" -ArgumentList "-NoExit", "-Command", $initScript -WindowStyle Normal

Start-Sleep 3

# Test backend
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:$Port/api/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "Backend OK: $($resp.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "Backend not responding yet, waiting..." -ForegroundColor Yellow
    Start-Sleep 3
}

# Start tunnel
Write-Host "Starting tunnel on subdomain '$Tunnel'..." -ForegroundColor Green
$tunnelScript = "lt --port $Port --subdomain $Tunnel"
Start-Process -FilePath "pwsh" -ArgumentList "-NoExit", "-Command", $tunnelScript -WindowStyle Normal

Write-Host "=== Done ===" -ForegroundColor Yellow
Write-Host "Local: http://localhost:$Port" -ForegroundColor Cyan
Write-Host "Tunnel: https://$Tunnel.loca.lt" -ForegroundColor Cyan
