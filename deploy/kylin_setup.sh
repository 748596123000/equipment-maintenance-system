#!/bin/bash
# ============================================================
# 设备检修知识检索与作业系统 - 银河麒麟部署脚本
# 适配：银河麒麟高级服务器版 V10/V11 + LoongArch架构
# ============================================================

set -e

echo "=========================================="
echo "  设备检修知识检索与作业系统 - 部署脚本"
echo "  目标环境：银河麒麟 + LoongArch"
echo "=========================================="

# ---- 1. 系统环境检测 ----
echo "[1/7] 检测系统环境..."

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
else
    echo "  ⚠ 无法检测操作系统版本"
fi

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

# ---- 2. 创建虚拟环境 ----
echo "[2/7] 创建Python虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✓ 虚拟环境已创建"
else
    echo "  ✓ 虚拟环境已存在，跳过创建"
fi
source venv/bin/activate
echo "  ✓ 虚拟环境已激活"

# ---- 3. 安装Python依赖 ----
echo "[3/7] 安装Python依赖..."
pip install --upgrade pip

# LoongArch架构特殊处理
if [ "$ARCH" = "loongarch64" ]; then
    echo "  检测到LoongArch架构，使用适配安装方式..."
    # 某些包在LoongArch上需要特殊处理
    pip install --no-cache-dir -r requirements.txt 2>&1 | tee install.log
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo "  ⚠ 部分包安装失败，尝试备用方案..."
        # ChromaDB在LoongArch上的备用安装
        pip install chromadb --no-deps 2>/dev/null || true
        pip install duckdb parquet 2>/dev/null || true
        # 重试安装
        pip install --no-cache-dir -r requirements.txt --use-pep517 2>&1 | tee -a install.log
    fi
else
    pip install --no-cache-dir -r requirements.txt
fi
echo "  ✓ Python依赖安装完成"

# ---- 4. 配置环境变量 ----
echo "[4/7] 配置环境变量..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "  ✓ 已从.env.example创建.env文件"
        echo "  ⚠ 请编辑.env文件，填入您的通义千问API密钥"
    else
        echo "  ⚠ 未找到.env.example，请手动创建.env文件"
    fi
else
    echo "  ✓ .env文件已存在"
fi

# ---- 5. 初始化数据目录 ----
echo "[5/7] 初始化数据目录..."
mkdir -p data/pdfs data/images data/chroma_db data/logs
echo "  ✓ 数据目录已创建"

# ---- 6. 初始化数据库 ----
echo "[6/7] 初始化数据库..."
python -c "
from app.models.database import init_db
init_db()
print('  ✓ 数据库初始化完成')
" 2>/dev/null || echo "  ⚠ 数据库初始化跳过（首次运行时将自动初始化）"

# ---- 7. 启动服务 ----
echo "[7/7] 启动服务..."
echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "  启动方式："
echo "    后端服务: source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "    前端服务: source venv/bin/activate && streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0"
echo ""
echo "  或使用一键启动脚本:"
echo "    bash deploy/start.sh"
echo ""
echo "  访问地址:"
echo "    前端界面: http://localhost:8501"
echo "    API文档: http://localhost:8000/docs"
echo ""
