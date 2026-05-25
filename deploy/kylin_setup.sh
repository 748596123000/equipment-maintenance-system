#!/bin/bash
# ============================================================
# 设备检修知识检索与作业系统 - 银河麒麟部署脚本
# 适配：银河麒麟高级服务器版 V10/V11 + LoongArch架构
#
# 硬件要求（赛题要求）：
#   CPU: LoongArch架构 四核及以上
#   内存: 8GB以上
#   硬盘: 256GB以上
#   操作系统: 银河麒麟高级服务器操作系统 V11/V10
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "=========================================="
echo "  设备检修知识检索与作业系统 - 部署脚本"
echo "  目标环境：银河麒麟 + LoongArch"
echo "=========================================="

# ---- 1. 系统环境检测 ----
echo "[1/8] 检测系统环境..."

ARCH=$(uname -m)
echo "  CPU架构: $ARCH"

if [ "$ARCH" != "loongarch64" ]; then
    echo "  ⚠ 警告: 当前架构为 $ARCH，非LoongArch64"
    echo "  本脚本主要针对LoongArch架构优化"
    echo "  如在x86_64上开发测试，可继续执行"
fi

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "  操作系统: $NAME $VERSION"
    if [[ "$NAME" == *"Kylin"* ]]; then
        echo "  ✓ 银河麒麟操作系统检测通过"
    fi
else
    echo "  ⚠ 无法检测操作系统版本"
fi

# 检测硬件资源
echo "  硬件资源检测:"
CPU_CORES=$(nproc 2>/dev/null || echo "未知")
MEM_TOTAL=$(free -m 2>/dev/null | awk '/Mem:/{print $2}' || echo "未知")
DISK_AVAIL=$(df -BG . 2>/dev/null | awk 'NR==2{print $4}' || echo "未知")
echo "    CPU核心数: $CPU_CORES (要求: 四核及以上)"
echo "    内存: ${MEM_TOTAL}MB (要求: 8GB以上)"
echo "    可用磁盘: ${DISK_AVAIL}G (要求: 256GB以上)"

# 检测Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo "  Python: $PYTHON_VERSION"
else
    echo "  ✗ 未检测到Python3，正在安装..."
    sudo yum install -y python3 python3-pip python3-devel || \
    sudo apt install -y python3 python3-pip python3-venv || \
    echo "  ✗ 请手动安装Python 3.10+"
    exit 1
fi

# 检测Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version 2>&1)
    echo "  Node.js: $NODE_VERSION"
else
    echo "  ⚠ 未检测到Node.js，前端需预构建或安装Node.js"
fi

# ---- 2. 创建虚拟环境 ----
echo "[2/8] 创建Python虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✓ 虚拟环境已创建"
else
    echo "  ✓ 虚拟环境已存在，跳过创建"
fi
source venv/bin/activate
echo "  ✓ 虚拟环境已激活"

# ---- 3. 安装Python依赖 ----
echo "[3/8] 安装Python依赖..."
pip install --upgrade pip

if [ "$ARCH" = "loongarch64" ]; then
    echo "  检测到LoongArch架构，使用适配安装方式..."
    pip install --no-cache-dir -r requirements.txt \
        -i https://pypi.loongnix.cn/loongnix/pypi/simple \
        --trusted-host pypi.loongnix.cn 2>&1 | tee install.log
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo "  ⚠ 部分包安装失败，尝试备用方案..."
        pip install chromadb --no-deps 2>/dev/null || true
        pip install duckdb parquet 2>/dev/null || true
        pip install --no-cache-dir -r requirements.txt --use-pep517 2>&1 | tee -a install.log
    fi
else
    pip install --no-cache-dir -r requirements.txt
fi
echo "  ✓ Python依赖安装完成"

# ---- 4. 构建前端 ----
echo "[4/8] 构建React前端..."
if [ -d "frontend/dist" ] && [ "$(ls -A frontend/dist 2>/dev/null)" ]; then
    echo "  ✓ 前端构建产物已存在，跳过构建"
elif command -v node &> /dev/null; then
    echo "  正在构建前端..."
    cd frontend
    npm ci --registry=https://registry.npmmirror.com 2>/dev/null || npm install --registry=https://registry.npmmirror.com
    npm run build
    cd "$PROJECT_DIR"
    echo "  ✓ 前端构建完成"
else
    echo "  ⚠ 未安装Node.js，无法构建前端"
    echo "  请在另一台机器上构建前端后，将 frontend/dist/ 目录复制过来"
    echo "  构建命令: cd frontend && npm ci && npm run build"
fi

# ---- 5. 配置Nginx ----
echo "[5/8] 配置Nginx前端服务..."
if command -v nginx &> /dev/null; then
    if [ -d "frontend/dist" ]; then
        sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
        sudo cp frontend/nginx.conf /etc/nginx/conf.d/equipment-maintenance.conf 2>/dev/null || \
        sudo cp frontend/nginx.conf /etc/nginx/conf.d/default.conf 2>/dev/null || true
        sudo mkdir -p /usr/share/nginx/html
        sudo cp -r frontend/dist/* /usr/share/nginx/html/ 2>/dev/null || true
        sudo nginx -t 2>/dev/null && echo "  ✓ Nginx配置验证通过" || echo "  ⚠ Nginx配置验证失败"
    else
        echo "  ⚠ 前端构建产物不存在，跳过Nginx配置"
    fi
else
    echo "  ⚠ 未安装Nginx，前端将通过开发服务器运行"
    echo "  安装Nginx: sudo yum install -y nginx || sudo apt install -y nginx"
fi

# ---- 6. 配置环境变量 ----
echo "[6/8] 配置环境变量..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "  ✓ 已从.env.example创建.env文件"
        echo ""
        echo "  ⚠ 请编辑.env文件，配置以下项："
        echo "    - DASHSCOPE_API_KEY: 通义千问API密钥（云端模型）"
        echo "    - LLM_BACKEND: 大模型后端 (dashscope/openai_compatible/ollama)"
        echo "    - LLM_MODEL: 模型名称"
        echo "    - LLM_API_BASE_URL: API地址（Ollama/OpenAI兼容后端）"
        echo ""
        echo "  LoongArch本地部署推荐配置："
        echo "    LLM_BACKEND=ollama"
        echo "    LLM_API_BASE_URL=http://localhost:11434/v1"
        echo "    LLM_MODEL=qwen2.5:7b"
    else
        echo "  ⚠ 未找到.env.example，请手动创建.env文件"
    fi
else
    echo "  ✓ .env文件已存在"
fi

# ---- 7. 初始化数据目录和数据库 ----
echo "[7/8] 初始化数据目录和数据库..."
mkdir -p data/pdfs data/images data/chroma_db data/logs
echo "  ✓ 数据目录已创建"

python -c "
from app.models.database import init_db
init_db()
print('  ✓ 数据库初始化完成')
" 2>/dev/null || echo "  ⚠ 数据库初始化跳过（首次运行时将自动初始化）"

# ---- 8. 安装Ollama（可选） ----
echo "[8/8] 检测Ollama本地大模型..."
if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>&1 || echo "未知")
    echo "  ✓ Ollama已安装: $OLLAMA_VERSION"
    echo "  可用模型:"
    ollama list 2>/dev/null | head -10 || echo "    (无已下载模型)"
    echo ""
    echo "  推荐下载模型: ollama pull qwen2.5:7b"
elif [ "$ARCH" = "loongarch64" ]; then
    echo "  ⚠ Ollama在LoongArch上需要从源码编译"
    echo "  参考: https://github.com/ollama/ollama"
    echo "  或使用云端DashScope API作为替代"
else
    echo "  ⚠ Ollama未安装"
    echo "  安装: curl -fsSL https://ollama.com/install.sh | sh"
    echo "  安装后运行: ollama pull qwen2.5:7b"
fi

# ---- 部署完成 ----
echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "  启动方式："
echo "    方式1 (一键启动): bash deploy/start.sh"
echo "    方式2 (手动启动):"
echo "      source venv/bin/activate"
echo "      uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "      sudo nginx  # 或 sudo systemctl start nginx"
echo ""
echo "  访问地址:"
echo "    前端界面: http://localhost:80 (Nginx)"
echo "    开发前端: http://localhost:3000 (npm run dev)"
echo "    API文档:  http://localhost:8000/docs"
echo ""
echo "  系统管理:"
echo "    默认管理员: admin / admin123"
echo "    首次登录后请及时修改密码"
echo ""
