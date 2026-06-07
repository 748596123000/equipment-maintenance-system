# 设备检修知识检索与作业系统 - 快速启动
# 右键 -> 使用 PowerShell 运行

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  设备检修知识检索与作业系统" -ForegroundColor Cyan
Write-Host "  Equipment Maintenance Knowledge System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) {
    $ProjectRoot = $PSCommandPath | Split-Path -Parent
}
Set-Location $ProjectRoot

# ========== 检测 Python 环境 ==========
Write-Host "[检查] 正在检测 Python 环境..." -ForegroundColor Yellow

$PythonCmd = $null
try { $PythonCmd = (Get-Command python -ErrorAction SilentlyContinue).Source } catch {}
if (-not $PythonCmd) {
    try { $PythonCmd = (Get-Command python3 -ErrorAction SilentlyContinue).Source } catch {}
}

if (-not $PythonCmd) {
    Write-Host "[错误] 未找到 Python，请安装 Python 3.10+ 或激活 Conda 环境" -ForegroundColor Red
    Write-Host ""
    Write-Host "提示：如果使用 Conda，请先运行：" -ForegroundColor White
    Write-Host "  conda activate torch_gpu" -ForegroundColor Yellow
    Write-Host "  然后再运行此脚本" -ForegroundColor White
    Read-Host "按回车退出"
    exit 1
}

$PyVersion = & $PythonCmd --version 2>&1
Write-Host "[OK] Python 已找到: $PyVersion" -ForegroundColor Green

# ========== 检测虚拟环境 ==========
if ($env:CONDA_PREFIX) {
    Write-Host "[OK] Conda 环境已激活: $($env:CONDA_PREFIX)" -ForegroundColor Green
} elseif ($env:VIRTUAL_ENV) {
    Write-Host "[OK] 虚拟环境已激活: $($env:VIRTUAL_ENV)" -ForegroundColor Green
} else {
    Write-Host "[提示] 未检测到虚拟环境，建议使用 Conda 或 venv" -ForegroundColor DarkYellow
}

# ========== 检测项目目录 ==========
if (-not (Test-Path "app\main.py")) {
    Write-Host "[错误] 未找到 app\main.py，请在项目根目录运行此脚本" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}
if (-not (Test-Path "frontend")) {
    Write-Host "[错误] 未找到 frontend 目录" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}
Write-Host "[OK] 项目目录检查通过" -ForegroundColor Green

# ========== 检测 .pip_packages ==========
if (Test-Path ".pip_packages") {
    Write-Host "[OK] 检测到 CUDA 扩展包 (.pip_packages)" -ForegroundColor Green
}

# ========== 检测 Ollama 服务 ==========
Write-Host "[检查] 正在检测 Ollama 服务..." -ForegroundColor Yellow
try {
    $null = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "[OK] Ollama 服务正在运行" -ForegroundColor Green
} catch {
    Write-Host "[警告] Ollama 服务未运行，正在尝试启动..." -ForegroundColor DarkYellow
    try {
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -ErrorAction Stop
        Start-Sleep -Seconds 3
        $null = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
        Write-Host "[OK] Ollama 服务已启动" -ForegroundColor Green
    } catch {
        Write-Host "[警告] Ollama 启动失败，LLM/Embedding 功能可能不可用" -ForegroundColor DarkYellow
        Write-Host "       请手动运行: ollama serve" -ForegroundColor DarkYellow
    }
}

# ========== 检测前端依赖 ==========
Write-Host "[检查] 正在检测前端依赖..." -ForegroundColor Yellow
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "[安装] 首次运行，正在安装前端依赖..." -ForegroundColor Yellow
    Set-Location "$ProjectRoot\frontend"
    & npm install
    Set-Location $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] 前端依赖安装失败" -ForegroundColor Red
        Read-Host "按回车退出"
        exit 1
    }
}
Write-Host "[OK] 前端依赖已就绪" -ForegroundColor Green

# ========== 创建数据目录 ==========
@("data", "data\pdfs", "data\images", "data\chroma_db") | ForEach-Object {
    if (-not (Test-Path $_)) { New-Item -ItemType Directory -Path $_ -Force | Out-Null }
}

# ========== 启动后端 ==========
Write-Host ""
Write-Host "[1/2] 正在启动后端服务..." -ForegroundColor Yellow
Write-Host "      地址: http://localhost:8000" -ForegroundColor Gray
Write-Host "      文档: http://localhost:8000/docs" -ForegroundColor Gray

$BackendCmd = "cd '$ProjectRoot'; & '$PythonCmd' -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $BackendCmd

Start-Sleep -Seconds 4

# ========== 启动前端 ==========
Write-Host "[2/2] 正在启动前端服务..." -ForegroundColor Yellow
Write-Host "      地址: http://localhost:3000" -ForegroundColor Gray

$FrontendCmd = "cd '$ProjectRoot\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $FrontendCmd

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  系统启动完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  前端界面: http://localhost:3000" -ForegroundColor White
Write-Host "  后端API:  http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "  管理员: admin / admin123" -ForegroundColor White
Write-Host "  普通用户: user / user123" -ForegroundColor White
Write-Host ""
Write-Host "  提示：" -ForegroundColor DarkYellow
Write-Host "    - 首次使用请先在 API管理 中配置模型" -ForegroundColor Gray
Write-Host "    - Ollama 模型需手动拉取: ollama pull qwen2.5:7b" -ForegroundColor Gray
Write-Host "    - Embedding 模型首次使用时自动拉取" -ForegroundColor Gray
Write-Host ""

Start-Sleep -Seconds 3
Start-Process "http://localhost:3000"
