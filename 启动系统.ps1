# Equipment Maintenance System - Quick Start
# Right-click -> Run with PowerShell

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Equipment Maintenance System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) {
    $ProjectRoot = $PSCommandPath | Split-Path -Parent
}
Set-Location $ProjectRoot

# Check venv exists
$VenvPath = Join-Path $ProjectRoot "venv\Scripts\Activate.ps1"

# Start backend
Write-Host "[1/2] Starting backend..." -ForegroundColor Yellow
$BackendCmd = "cd '$ProjectRoot'; if (Test-Path '$VenvPath') { & '$VenvPath' }; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $BackendCmd

Start-Sleep -Seconds 3

# Start frontend
Write-Host "[2/2] Starting frontend..." -ForegroundColor Yellow
$FrontendCmd = "cd '$ProjectRoot\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $FrontendCmd

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Startup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "  API:      http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "  Admin: admin / admin123" -ForegroundColor White
Write-Host "  User:  user / user123" -ForegroundColor White
Write-Host ""

Start-Sleep -Seconds 3
Start-Process "http://localhost:3000"