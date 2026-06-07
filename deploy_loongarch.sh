#!/bin/bash
# =============================================================================
# 设备检修知识检索与作业系统 - 麒麟V11 LoongArch 部署脚本
# =============================================================================
# 功能：在麒麟V11 LoongArch虚拟机上完成AI模块的部署和配置
# 适用：龙芯CPU、无GPU、无预编译wheel环境
# 说明：优先使用DashScope API，本地模型需手动配置
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
PROJECT_DIR="${HOME}/knowledge-system"
VENV_DIR="${PROJECT_DIR}/venv"
BACKEND_DIR="${PROJECT_DIR}/backend"
DATA_DIR="${PROJECT_DIR}/data"
MODELS_DIR="${PROJECT_DIR}/models"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# =============================================================================
# 1. 环境检查
# =============================================================================
check_environment() {
    log_step "1. 检查系统环境"

    # 检查架构
    ARCH=$(uname -m)
    log_info "系统架构: ${ARCH}"
    if [[ "${ARCH}" != "loongarch64" && "${ARCH}" != "loong64" ]]; then
        log_warn "当前不是LoongArch架构，但脚本仍可运行"
    fi

    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "未找到python3，请先安装Python 3.9+"
        exit 1
    fi
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    log_info "Python版本: ${PYTHON_VERSION}"

    # 检查pip
    if ! command -v pip3 &> /dev/null; then
        log_error "未找到pip3"
        exit 1
    fi

    # 检查虚拟环境
    if [ ! -d "${VENV_DIR}" ]; then
        log_warn "虚拟环境不存在，将创建"
        python3 -m venv "${VENV_DIR}"
    fi

    log_info "环境检查通过"
}

# =============================================================================
# 2. 安装基础依赖
# =============================================================================
install_base_deps() {
    log_step "2. 安装基础依赖"

    source "${VENV_DIR}/bin/activate"

    # 升级pip
    pip install --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple

    # 安装核心依赖（已确认LoongArch可用）
    log_info "安装核心依赖..."
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
        fastapi uvicorn pydantic pydantic-settings \
        python-multipart python-jose passlib bcrypt \
        chromadb sqlite3-fts5 \
        requests httpx aiohttp \
        numpy pandas \
        python-docx openpyxl \
        pdfplumber pymupdf \
        pillow opencv-python-headless \
        cachetools tenacity

    log_info "基础依赖安装完成"
}

# =============================================================================
# 3. 安装AI模块依赖（可选）
# =============================================================================
install_ai_deps() {
    log_step "3. 安装AI模块依赖"

    source "${VENV_DIR}/bin/activate"

    # DashScope API（推荐，无需本地模型）
    log_info "安装DashScope SDK..."
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple dashscope openai

    # 可选：RapidOCR（需确认ONNX Runtime支持）
    log_info "尝试安装RapidOCR（如失败可跳过）..."
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple rapidocr-onnxruntime || {
        log_warn "RapidOCR安装失败，将使用API OCR模式"
    }

    # 可选：llama-cpp-python（本地Embedding）
    log_info "尝试安装llama-cpp-python（如失败可跳过）..."
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple llama-cpp-python || {
        log_warn "llama-cpp-python安装失败，将使用API Embedding模式"
    }

    # 可选：本地视觉模型依赖（非常耗时，不推荐）
    if [ "${INSTALL_LOCAL_VISION:-0}" = "1" ]; then
        log_info "安装本地视觉模型依赖（耗时较长）..."
        pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
            torch torchvision transformers accelerate qwen-vl-utils || {
            log_warn "本地视觉模型依赖安装失败，将使用API模式"
        }
    else
        log_info "跳过本地视觉模型依赖（设置 INSTALL_LOCAL_VISION=1 可安装）"
    fi

    log_info "AI模块依赖安装完成"
}

# =============================================================================
# 4. 配置环境变量
# =============================================================================
setup_config() {
    log_step "4. 配置环境变量"

    ENV_FILE="${BACKEND_DIR}/.env"

    # 如果.env不存在，创建模板
    if [ ! -f "${ENV_FILE}" ]; then
        log_info "创建.env配置文件..."
        cat > "${ENV_FILE}" << 'EOF'
# =============================================================================
# 设备检修知识检索与作业系统 - LoongArch配置
# =============================================================================

# ---------- DashScope API配置（推荐） ----------
# 从 https://dashscope.console.aliyun.com/ 获取API Key
DASHSCOPE_API_KEY=your_api_key_here

# ---------- Embedding配置 ----------
# 使用DashScope API（推荐）
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_DIMENSION=1024

# 或使用本地llama.cpp模型（需手动下载GGUF）
# LLAMA_CPP_EMBED_MODEL_PATH=/path/to/your/embedding-model.gguf

# ---------- LLM配置 ----------
# 使用DashScope API
LLM_BACKEND=dashscope
LLM_MODEL=qwen-max

# 或使用本地llama.cpp（需配置llama.cpp服务）
# LLM_BACKEND=openai_compatible
# LLM_API_BASE_URL=http://localhost:11435/v1
# LLM_API_KEY=not-needed

# ---------- OCR配置 ----------
# api: 使用DashScope（推荐）
# rapidocr: 本地RapidOCR（需安装rapidocr-onnxruntime）
# none: 禁用OCR
OCR_BACKEND=api
OCR_USE_GPU=false
OCR_LANGUAGE=ch

# ---------- 视觉模型配置 ----------
# dashscope: 使用DashScope API（推荐）
# local: 本地模型（需安装torch/transformers，非常耗时）
VISION_BACKEND=dashscope
LOCAL_VISION_MODEL=Qwen/Qwen2-VL-2B-Instruct

# ---------- 数据库配置 ----------
CHROMA_PERSIST_DIR=./data/chroma_db
SQLITE_DB_PATH=./data/app.db

# ---------- 文件存储 ----------
UPLOAD_DIR=./data/pdfs
IMAGE_DIR=./data/images

# ---------- 服务配置 ----------
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# ---------- 安全配置 ----------
SECRET_KEY=change-this-to-a-secure-random-string
ACCESS_TOKEN_EXPIRE_HOURS=24

# ---------- CORS配置 ----------
CORS_ORIGINS=["http://localhost","http://localhost:80"]
ALLOWED_HOSTS=["*"]
EOF
        log_warn "请编辑 ${ENV_FILE} 配置您的API Key"
    else
        log_info ".env文件已存在"
    fi

    # 创建数据目录
    mkdir -p "${DATA_DIR}/chroma_db" "${DATA_DIR}/pdfs" "${DATA_DIR}/images" "${MODELS_DIR}"

    log_info "配置完成"
}

# =============================================================================
# 5. 模型下载说明
# =============================================================================
model_download_guide() {
    log_step "5. 模型下载指南"

    cat << 'EOF'

=============================================================================
                         模型下载与配置指南
=============================================================================

【推荐方案】使用DashScope API（无需本地模型）
  1. 访问 https://dashscope.console.aliyun.com/ 注册账号
  2. 获取API Key
  3. 编辑 backend/.env，设置 DASHSCOPE_API_KEY=your_key

【可选方案】本地llama.cpp模型（无需网络）
  1. 在Windows主机下载GGUF格式模型：
     - Embedding: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF
     - LLM: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF
  2. 传输到虚拟机 ${MODELS_DIR} 目录
  3. 编辑 backend/.env：
     LLAMA_CPP_EMBED_MODEL_PATH=/home/vmuser/knowledge-system/models/your-model.gguf

【可选方案】本地视觉模型（不推荐，编译耗时）
  1. 设置环境变量：export INSTALL_LOCAL_VISION=1
  2. 重新运行此脚本安装依赖
  3. 下载模型到 ${MODELS_DIR}
  4. 编辑 backend/.env：
     VISION_BACKEND=local
     LOCAL_VISION_MODEL=/path/to/local/model

=============================================================================
EOF
}

# =============================================================================
# 6. 验证安装
# =============================================================================
verify_installation() {
    log_step "6. 验证安装"

    source "${VENV_DIR}/bin/activate"

    cd "${BACKEND_DIR}"

    # 测试Python导入
    log_info "测试核心模块导入..."
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from app.services.embedding_service_loongarch import EmbeddingServiceLoongArch
    print('✓ Embedding模块加载成功')
except Exception as e:
    print(f'✗ Embedding模块加载失败: {e}')

try:
    from app.services.ocr_service_loongarch import OCRServiceLoongArch
    print('✓ OCR模块加载成功')
except Exception as e:
    print(f'✗ OCR模块加载失败: {e}')

try:
    from app.services.vision_service_loongarch import VisionServiceLoongArch
    print('✓ Vision模块加载成功')
except Exception as e:
    print(f'✗ Vision模块加载失败: {e}')
"

    log_info "验证完成"
}

# =============================================================================
# 7. 启动服务
# =============================================================================
start_services() {
    log_step "7. 启动服务"

    log_info "启动后端服务..."
    cd "${BACKEND_DIR}"
    source "${VENV_DIR}/bin/activate"

    # 后台启动
    nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
    echo $! > app.pid

    sleep 3

    # 检查是否启动成功
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        log_info "后端服务启动成功"
    else
        log_warn "后端服务可能未完全启动，请检查日志: ${BACKEND_DIR}/app.log"
    fi
}

# =============================================================================
# 主流程
# =============================================================================
main() {
    echo "============================================================================="
    echo "       设备检修知识检索与作业系统 - LoongArch部署脚本"
    echo "============================================================================="
    echo ""

    # 检查是否在项目目录
    if [ ! -d "${PROJECT_DIR}" ]; then
        log_warn "项目目录 ${PROJECT_DIR} 不存在"
        read -p "请输入项目目录路径 [默认: ${HOME}/knowledge-system]: " input_dir
        PROJECT_DIR="${input_dir:-${HOME}/knowledge-system}"
        BACKEND_DIR="${PROJECT_DIR}/backend"
        VENV_DIR="${PROJECT_DIR}/venv"
        DATA_DIR="${PROJECT_DIR}/data"
        MODELS_DIR="${PROJECT_DIR}/models"
    fi

    log_info "项目目录: ${PROJECT_DIR}"

    # 执行部署步骤
    check_environment
    install_base_deps
    install_ai_deps
    setup_config
    model_download_guide
    verify_installation

    echo ""
    echo "============================================================================="
    echo -e "${GREEN}部署完成！${NC}"
    echo ""
    echo "下一步："
    echo "  1. 编辑 ${BACKEND_DIR}/.env 配置API Key"
    echo "  2. 如需本地模型，参考上方模型下载指南"
    echo "  3. 运行 ./start_all.sh 启动所有服务"
    echo "============================================================================="
}

# 处理命令行参数
case "${1:-}" in
    --install-local-vision)
        export INSTALL_LOCAL_VISION=1
        main
        ;;
    --help|-h)
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  --install-local-vision  安装本地视觉模型依赖（耗时较长）"
        echo "  --help, -h              显示帮助"
        echo ""
        echo "环境变量:"
        echo "  INSTALL_LOCAL_VISION=1  同上"
        ;;
    *)
        main
        ;;
esac
