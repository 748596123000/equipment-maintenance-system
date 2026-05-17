<#
.SYNOPSIS
    设备检修知识检索与作业系统 - 一键启动脚本 (Windows)
.DESCRIPTION
    自动检测环境、安装依赖、启动后端和前端服务
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  设备检修知识检索与作业系统 - Windows 启动脚本" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/6] 检查 Python 环境..." -ForegroundColor Yellow
$pythonCmd = $null
foreach ($cmd in @("python", "python3")) {
    try {
        $version = & $cmd --version 2>&1
        if ($version -match "3\.(\d+)") {
            $pythonCmd = $cmd
            Write-Host "  找到 Python: $version" -ForegroundColor Green
            break
        }
    } catch {}
}
if (-not $pythonCmd) {
    Write-Host "  错误: 未找到 Python 3.10+" -ForegroundColor Red
    Write-Host "  请安装 Python: https://www.python.org/downloads/" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

Write-Host "[2/6] 检查 Node.js 环境..." -ForegroundColor Yellow
try {
    $nodeVersion = & node --version 2>&1
    Write-Host "  找到 Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  错误: 未找到 Node.js 18+" -ForegroundColor Red
    Write-Host "  请安装 Node.js: https://nodejs.org/" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

Write-Host "[3/6] 检查环境配置..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "  未找到 .env 文件，从模板创建..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "  已创建 .env 文件，请编辑后重新运行！" -ForegroundColor Red
    Write-Host "  必须配置 DASHSCOPE_API_KEY" -ForegroundColor Red
    notepad ".env"
    Read-Host "按回车退出"
    exit 1
}

$envContent = Get-Content ".env" -Raw
if ($envContent -match "your_api_key_here") {
    Write-Host "  警告: .env 中 DASHSCOPE_API_KEY 未配置" -ForegroundColor Red
    Write-Host "  AI问答功能将不可用，是否继续？(Y/N)" -ForegroundColor Yellow
    $continue = Read-Host
    if ($continue -ne "Y" -and $continue -ne "y") {
        notepad ".env"
        exit 1
    }
}

Write-Host "[4/6] 检查 Python 虚拟环境..." -ForegroundColor Yellow
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "  创建虚拟环境..." -ForegroundColor Yellow
    & $pythonCmd -m venv venv
    Write-Host "  虚拟环境创建完成" -ForegroundColor Green
}

& "$ProjectRoot\venv\Scripts\Activate.ps1"

Write-Host "[5/6] 检查后端依赖..." -ForegroundColor Yellow
if (-not (Test-Path "venv\Lib\site-packages\fastapi")) {
    Write-Host "  安装后端依赖（首次可能需要几分钟）..." -ForegroundColor Yellow
    & $pythonCmd -m pip install -r requirements.txt -q
    Write-Host "  后端依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "  后端依赖已就绪" -ForegroundColor Green
}

Write-Host "[6/6] 检查前端依赖..." -ForegroundColor Yellow
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "  安装前端依赖（首次可能需要几分钟）..." -ForegroundColor Yellow
    Set-Location -LiteralPath "$ProjectRoot\frontend"
    npm install
    Set-Location -LiteralPath $ProjectRoot
    Write-Host "  前端依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "  前端依赖已就绪" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  环境检查完成，正在启动服务..." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "清理旧进程..." -ForegroundColor Yellow
$oldPython = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmdLine -match "uvicorn"
    } catch { $false }
}
if ($oldPython) {
    $oldPython | Stop-Process -Force
    Write-Host "  已停止旧的后端进程" -ForegroundColor Yellow
}

$oldNode = Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmdLine -match "vite"
    } catch { $false }
}
if ($oldNode) {
    $oldNode | Stop-Process -Force
    Write-Host "  已停止旧的前端进程" -ForegroundColor Yellow
}

Start-Sleep -Seconds 1

foreach ($dir in @("data\pdfs", "data\images", "data\chroma_db", "data\logs")) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Host "启动后端服务 (端口 8000)..." -ForegroundColor Yellow
$backendLog = Join-Path $ProjectRoot "data\logs\api.log"
Start-Process -FilePath "python" `
    -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $backendLog

Write-Host "  等待后端就绪..." -ForegroundColor Yellow
$ready = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 1
    Write-Host "." -NoNewline
}
Write-Host ""

if ($ready) { Write-Host "  后端已就绪" -ForegroundColor Green }
else { Write-Host "  警告: 后端未在30秒内就绪，请检查日志: $backendLog" -ForegroundColor Red }

Write-Host "启动前端服务 (端口 3000)..." -ForegroundColor Yellow
$frontendDir = "$ProjectRoot\frontend"
$frontendBat = Join-Path $ProjectRoot "data\_start_frontend.bat"
$batLines = @(
    "@echo off",
    "cd /d ""$frontendDir""",
    "npm run dev"
)
Set-Content -Value ($batLines -join "`r`n") -Path $frontendBat -Encoding ASCII
Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c","`"$frontendBat`"" `
    -WindowStyle Minimized

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  系统已启动！" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  前端:  http://localhost:3000" -ForegroundColor White
Write-Host "  API:   http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "  管理员: admin / admin123" -ForegroundColor White
Write-Host "  用户:   user  / user123" -ForegroundColor White
Write-Host ""
Write-Host "  使用 stop.ps1 停止所有服务" -ForegroundColor Yellow
Write-Host ""

Start-Process "http://localhost:3000"
