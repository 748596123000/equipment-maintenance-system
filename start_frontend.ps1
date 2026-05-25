$ErrorActionPreference = "Stop"
$projectDir = "D:\Chinese team\equipment-maintenance-system-v2-fixed\.worktrees\feature-redesign\frontend"

Write-Host "Starting frontend on port 3000..."
$process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d `"$projectDir`" && npm run dev -- --port 3000" -PassThru -WindowStyle Normal

if ($process) {
    Write-Host "Frontend process started with PID: $($process.Id)"
    Write-Host "Please check the new command prompt window for frontend output"
} else {
    Write-Host "Failed to start frontend process"
}