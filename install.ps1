<#
.SYNOPSIS
    设备检修知识检索与作业系统 - 环境安装脚本 (Windows)
.DESCRIPTION
    首次运行时安装所有依赖，包括 Python 虚拟环境和 Node.js 前端依赖
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  设备检修知识检索与作业系统 - 环境安装" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/5] 检查 Python..." -ForegroundColor Yellow
$pythonCmd = $null
foreach ($cmd in @("python", "python3")) {
    try {
        $version = & $cmd --version 2>&1
        if ($version -match "3\.(\d+)") {
            $pythonCmd = $cmd
            Write-Host "  Python: $version" -ForegroundColor Green
            break
        }
    } catch {}
}
if (-not $pythonCmd) {
    Write-Host "  错误: 未找到 Python 3.10+" -ForegroundColor Red
    Write-Host "  下载地址: https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "  安装时务必勾选 'Add Python to PATH'" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

Write-Host "[2/5] 检查 Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = & node --version 2>&1
    Write-Host "  Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  错误: 未找到 Node.js" -ForegroundColor Red
    Write-Host "  下载地址: https://nodejs.org/" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

Write-Host "[3/5] 创建 Python 虚拟环境..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "  虚拟环境已存在，跳过" -ForegroundColor Green
} else {
    & $pythonCmd -m venv venv
    Write-Host "  虚拟环境创建完成" -ForegroundColor Green
}

Write-Host "[4/5] 安装后端 Python 依赖..." -ForegroundColor Yellow
& "$ProjectRoot\venv\Scripts\Activate.ps1"
& $pythonCmd -m pip install --upgrade pip -q
& $pythonCmd -m pip install -r requirements.txt
Write-Host "  后端依赖安装完成" -ForegroundColor Green

Write-Host "[5/5] 安装前端 Node.js 依赖..." -ForegroundColor Yellow
Set-Location -LiteralPath "$ProjectRoot\frontend"
npm install
Set-Location -LiteralPath $ProjectRoot
Write-Host "  前端依赖安装完成" -ForegroundColor Green

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ""
    Write-Host "  已创建 .env 配置文件" -ForegroundColor Yellow
    Write-Host "  请编辑 .env 填写 DASHSCOPE_API_KEY" -ForegroundColor Yellow
}

foreach ($dir in @("data\pdfs", "data\images", "data\chroma_db", "data\logs")) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  下一步:" -ForegroundColor White
Write-Host "  1. 编辑 .env 填写 DASHSCOPE_API_KEY" -ForegroundColor White
Write-Host "  2. 运行 .\start.ps1 启动系统" -ForegroundColor White
Write-Host ""
