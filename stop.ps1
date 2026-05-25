<#
.SYNOPSIS
    设备检修知识检索与作业系统 - 停止脚本 (Windows)
.DESCRIPTION
    停止所有后端和前端服务进程
#>

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  停止设备检修知识检索与作业系统" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$stopped = 0

$uvicornProcs = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmdLine -match "uvicorn"
    } catch { $false }
}

if ($uvicornProcs) {
    foreach ($proc in $uvicornProcs) {
        Write-Host "  停止后端进程 PID=$($proc.Id)..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force
        $stopped++
    }
    Write-Host "  后端已停止" -ForegroundColor Green
} else {
    Write-Host "  未发现后端进程" -ForegroundColor Gray
}

$viteProcs = Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmdLine -match "vite"
    } catch { $false }
}

if ($viteProcs) {
    foreach ($proc in $viteProcs) {
        Write-Host "  停止前端进程 PID=$($proc.Id)..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force
        $stopped++
    }
    Write-Host "  前端已停止" -ForegroundColor Green
} else {
    Write-Host "  未发现前端进程" -ForegroundColor Gray
}

Write-Host ""
if ($stopped -gt 0) {
    Write-Host "  已停止 $stopped 个进程" -ForegroundColor Green
} else {
    Write-Host "  没有运行中的服务进程" -ForegroundColor Yellow
}
Write-Host ""
