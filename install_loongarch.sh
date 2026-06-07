#!/bin/bash

echo "============================================================"
echo "设备检修知识检索与作业系统 - LoongArch专用安装脚本"
echo "适配: 银河麒麟高级服务器版V11 (LoongArch架构)"
echo "============================================================"

set -e

# 检测包管理器
if command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    echo "检测到包管理器: yum (麒麟V11)"
elif command -v apt &> /dev/null; then
    PKG_MANAGER="apt"
    echo "检测到包管理器: apt"
else
    echo "[警告] 未检测到支持的包管理器 (yum/apt)"
    PKG_MANAGER=""
fi

# 检测架构
ARCH=$(uname -m)
if [ "$ARCH" != "loongarch64" ]; then
    echo "[警告] 当前架构为 $ARCH，此脚本专为LoongArch优化"
    echo "继续安装可能需要额外配置..."
fi

echo ""
echo "[步骤1] 检查系统环境..."

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] Python3未安装"
    if [ "$PKG_MANAGER" = "yum" ]; then
        echo "请执行: sudo yum install -y python3 python3-pip python3-devel"
    else
        echo "请执行: sudo apt install python3 python3-pip python3-dev"
    fi
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "  Python: $PYTHON_VERSION"

# 检查pip
if ! command -v pip3 &> /dev/null; then
    echo "[错误] pip3未安装"
    if [ "$PKG_MANAGER" = "yum" ]; then
        echo "请执行: sudo yum install -y python3-pip"
    else
        echo "请执行: sudo apt install python3-pip"
    fi
    exit 1
fi

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "[警告] Node.js未安装，前端将无法运行"
    if [ "$PKG_MANAGER" = "yum" ]; then
        echo "请执行: sudo yum install -y nodejs npm"
    else
        echo "请执行: sudo apt install nodejs npm"
    fi
    echo "或从龙芯官方下载: http://www.loongnix.cn/zh/api/nodejs/"
    NODE_INSTALLED=false
else
    NODE_VERSION=$(node --version)
    echo "  Node.js: $NODE_VERSION"
    NODE_INSTALLED=true
fi

echo ""
echo "[步骤2] 安装系统依赖..."
echo "  安装OCR和PDF处理工具..."

if [ "$PKG_MANAGER" = "yum" ]; then
    # 麒麟V11 - 使用yum
    echo "  安装基础依赖..."
    sudo yum install -y tesseract libffi-devel openssl-devel libjpeg-devel zlib-devel \
        gcc gcc-c++ make || {
        echo "[警告] 部分系统依赖安装失败，可能影响某些功能"
    }
    # 尝试安装OCR中文语言包（可能包名不同）
    sudo yum install -y tesseract-langpack-chi-sim 2>/dev/null || \
    sudo yum install -y tesseract-chi-sim 2>/dev/null || \
    echo "  [提示] OCR中文语言包可能需要手动安装"
elif [ "$PKG_MANAGER" = "apt" ]; then
    # Debian/Ubuntu - 使用apt
    sudo apt update
    sudo apt install -y tesseract-ocr tesseract-ocr-chi-sim \
        poppler-utils libffi-dev libssl-dev libjpeg-dev zlib1g-dev \
        build-essential gcc g++ make || {
        echo "[警告] 部分系统依赖安装失败，可能影响某些功能"
    }
else
    echo "[警告] 无法安装系统依赖，请手动安装"
fi

echo ""
echo "[步骤3] 配置pip镜像源..."
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://pypi.org/simple
trusted-host = pypi.org
timeout = 120
EOF
echo "  pip配置已更新 (使用官方PyPI源)"

# 检查本地pip_packages目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_PKGS="$SCRIPT_DIR/pip_packages"
if [ -d "$LOCAL_PKGS" ] && [ "$(ls -A $LOCAL_PKGS 2>/dev/null)" ]; then
    PKG_COUNT=$(ls -1 $LOCAL_PKGS | wc -l)
    echo "  检测到本地依赖包目录: $LOCAL_PKGS ($PKG_COUNT 个文件)"
    USE_LOCAL=1
else
    echo "  未检测到本地依赖包目录，将从网络下载"
    USE_LOCAL=0
fi

echo ""
echo "[步骤4] 升级pip..."
if [ "$USE_LOCAL" = "1" ]; then
    pip3 install --upgrade pip --user --find-links "$LOCAL_PKGS" --no-index 2>/dev/null || \
    pip3 install --upgrade pip --user
else
    pip3 install --upgrade pip --user
fi

echo ""
echo "[步骤5] 安装Python后端依赖..."

# 先安装基础编译工具
if [ "$PKG_MANAGER" = "yum" ]; then
    echo "  安装编译工具 (gcc-gfortran, openblas-devel等)..."
    sudo yum install -y gcc-gfortran openblas-devel patchelf || {
        echo "[警告] 部分编译工具安装失败"
    }
fi

if [ "$USE_LOCAL" = "1" ]; then
    echo "  从本地pip_packages安装所有依赖 (离线模式)..."
    echo "  纯Python包将直接安装，源码包将在LoongArch上编译..."
    echo "  注意: 编译过程可能需要10-30分钟，请耐心等待..."
    echo ""
    pip3 install --user --find-links "$LOCAL_PKGS" --no-index \
        -r requirements-loongarch.txt 2>&1 | tee install.log
    
    # 检查安装结果
    if [ $? -ne 0 ]; then
        echo ""
        echo "[警告] 部分包离线安装失败，尝试从网络补充安装..."
        pip3 install --user \
            onnxruntime hf-xet propcache 2>&1 | tee install_online.log || {
            echo "[提示] 以下包可能需要手动安装: onnxruntime, hf-xet, propcache"
        }
    fi
else
    echo "  从网络安装..."
    pip3 install --user -r requirements-loongarch.txt || {
        echo "[警告] 部分依赖安装失败"
    }
fi

# 检查numpy是否正常工作
echo ""
echo "  检查numpy fortran链接..."
python3 -c "import numpy; numpy.linalg.eig([[1,2],[3,4]])" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  [警告] numpy fortran链接有问题，尝试自动修复..."
    if [ -f "fix_numpy_fortran.py" ]; then
        python3 fix_numpy_fortran.py
    else
        echo "  [提示] 请手动运行: python3 fix_numpy_fortran.py"
    fi
fi

echo ""
echo "[步骤5] 安装ML依赖 (可选，用于本地模型)..."
echo "  注意: LoongArch上torch可能需要源码编译，耗时较长"
read -p "是否安装ML依赖(torch/transformers)? [y/N]: " INSTALL_ML
if [ "$INSTALL_ML" = "y" ] || [ "$INSTALL_ML" = "Y" ]; then
    echo "  安装torch (可能需要较长时间)..."
    pip3 install --user torch transformers accelerate || {
        echo "[警告] ML依赖安装失败，本地视觉模型功能不可用"
        echo "  建议: 使用云端LLM API替代"
    }
    
    echo "  安装sentence-transformers..."
    pip3 install --user sentence-transformers || {
        echo "[警告] Embedding模型安装失败"
    }
else
    echo "  跳过ML依赖安装"
fi

echo ""
echo "[步骤6] 配置LoongArch专用环境变量..."

# 创建.env文件（如果不存在）
if [ ! -f ".env" ]; then
    echo "  创建.env配置文件..."
    cp .env.example .env
    
    # 设置LoongArch专用配置
    sed -i 's/^# CHROMA_DB_IMPL=duckdb+parquet/CHROMA_DB_IMPL=duckdb+parquet/' .env
    sed -i 's/^# ANNOY_ENABLED=0/ANNOY_ENABLED=0/' .env
    
    echo "  已启用LoongArch兼容配置:"
    echo "    - CHROMA_DB_IMPL=duckdb+parquet"
    echo "    - ANNOY_ENABLED=0"
fi

echo ""
echo "[步骤7] 安装前端依赖..."
if [ "$NODE_INSTALLED" = true ]; then
    echo "  进入前端目录..."
    cd frontend
    
    echo "  安装npm依赖..."
    npm install || {
        echo "[警告] npm依赖安装失败"
        echo "  可尝试: rm -rf node_modules package-lock.json && npm install"
    }
    
    echo "  构建前端..."
    npm run build || {
        echo "[警告] 前端构建失败"
    }
    
    cd ..
else
    echo "  跳过前端安装 (Node.js未安装)"
fi

echo ""
echo "[步骤8] 创建数据目录..."
mkdir -p data/pdfs data/images data/chroma_db
echo "  数据目录已创建"

echo ""
echo "============================================================"
echo "安装完成!"
echo "============================================================"

echo ""
echo "下一步操作:"
echo ""
echo "1. 配置LLM服务:"
echo "   方式A - 使用云端API (推荐):"
echo "     编辑 .env 文件，设置:"
echo "       LLM_BACKEND=dashscope"
echo "       DASHSCOPE_API_KEY=your_api_key"
echo "       LLM_MODEL=qwen-max"
echo ""
echo "   方式B - 使用本地Ollama:"
echo "     安装Ollama: 参考 http://www.loongnix.cn/zh/api/ollama/"
echo "     下载模型: ollama pull qwen2.5:7b"
echo "     编辑 .env 文件，设置:"
echo "       LLM_BACKEND=ollama"
echo "       LLM_API_BASE_URL=http://localhost:11434/v1"
echo "       LLM_MODEL=qwen2.5:7b"
echo ""
echo "2. 启动服务:"
echo "   后端: python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "   前端: cd frontend && npm run dev"
echo ""
echo "3. 访问系统:"
echo "   http://localhost:3000 (开发模式)"
echo "   http://服务器IP (生产模式)"
echo ""
echo "注意事项:"
echo "- LoongArch架构下，部分Python包可能需要源码编译"
echo "- ChromaDB已配置为duckdb后端，避免hnswlib兼容问题"
echo "- 建议使用云端LLM API，本地模型性能可能受限"
echo ""
echo "如有问题，请参考 DEPLOY_LOONGARCH.md 文档"