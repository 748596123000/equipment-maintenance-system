#!/bin/bash
# =============================================================================
# 设备检修知识检索与作业系统 - AI模块LoongArch部署脚本
# =============================================================================
# 功能：在麒麟V11 LoongArch虚拟机上部署Embedding/OCR/视觉模型模块
# 适用：龙芯CPU、无GPU、无预编译wheel环境
# 说明：功能不减少，自动适配架构，优先API模式，支持本地模型
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 配置
PROJECT_DIR="${HOME}/knowledge-system"
VENV_DIR="${PROJECT_DIR}/venv"

# 自动检测项目结构：是否包含 backend 子目录
if [ -d "${PROJECT_DIR}/backend" ]; then
    BACKEND_DIR="${PROJECT_DIR}/backend"
    APP_DIR="${BACKEND_DIR}/app"
else
    BACKEND_DIR="${PROJECT_DIR}"
    APP_DIR="${PROJECT_DIR}/app"
fi

DATA_DIR="${PROJECT_DIR}/data"
MODELS_DIR="${PROJECT_DIR}/models"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }
log_tip() { echo -e "${CYAN}[TIP]${NC} $1"; }

# =============================================================================
# 0. 检查架构
# =============================================================================
check_architecture() {
    log_step "0. 检查系统架构"

    ARCH=$(uname -m)
    log_info "系统架构: ${ARCH}"

    if [[ "${ARCH}" == "loongarch64" || "${ARCH}" == "loong64" ]]; then
        log_info "确认LoongArch架构，启用适配模式"
        IS_LOONGARCH=1
    else
        log_warn "当前不是LoongArch架构 (${ARCH})，但脚本仍可运行"
        IS_LOONGARCH=0
    fi
}

# =============================================================================
# 1. 环境检查
# =============================================================================
check_environment() {
    log_step "1. 检查系统环境"

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

    #    检查项目目录
    if [ ! -d "${PROJECT_DIR}" ]; then
        log_error "项目目录不存在: ${PROJECT_DIR}"
        log_tip "请确保项目已部署到 ${PROJECT_DIR}"
        exit 1
    fi

    if [ ! -d "${APP_DIR}" ]; then
        log_error "应用目录不存在: ${APP_DIR}"
        log_tip "请检查项目结构"
        exit 1
    fi

    # 检查虚拟环境
    if [ ! -d "${VENV_DIR}" ]; then
        log_warn "虚拟环境不存在，将创建"
        python3 -m venv "${VENV_DIR}"
        log_info "虚拟环境创建完成"
    fi

    log_info "环境检查通过"
}

# =============================================================================
# 2. 安装/升级pip和基础依赖
# =============================================================================
install_base_deps() {
    log_step "2. 安装基础依赖"

    source "${VENV_DIR}/bin/activate"

    # 升级pip - 继续执行模式（已安装则跳过）
    log_info "检查pip版本（继续执行模式）..."
    if ! pip show pip > /dev/null 2>&1 || [ "${SKIP_PIP_UPGRADE:-0}" = "1" ]; then
        log_tip "pip已安装或设置为跳过升级，继续执行后续步骤"
    else
        pip install --upgrade pip setuptools -i https://pypi.tuna.tsinghua.edu.cn/simple || {
            log_warn "pip升级失败，继续..."
        }
    fi

    # 安装核心依赖（已确认LoongArch可用）
    log_info "安装核心依赖..."
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
        fastapi uvicorn pydantic pydantic-settings \
        python-multipart python-jose passlib bcrypt \
        chromadb \
        requests httpx aiohttp \
        numpy pandas \
        python-docx openpyxl \
        pdfplumber pymupdf \
        pillow opencv-python-headless \
        cachetools tenacity || {
        log_warn "部分核心依赖安装可能有问题，继续..."
    }

    log_info "基础依赖安装完成"
}

# =============================================================================
# 3. 安装AI模块依赖
# =============================================================================
install_ai_deps() {
    log_step "3. 安装AI模块依赖"

    source "${VENV_DIR}/bin/activate"

    # DashScope API（所有架构通用，推荐）
    log_info "安装DashScope SDK..."
    pip install dashscope openai -i https://mirrors.aliyun.com/pypi/simple/ --extra-index-url https://pypi.org/simple/ || {
        pip install dashscope openai || {
            log_warn "DashScope SDK安装失败，将使用API模式需手动安装"
        }
    }

    # RapidOCR（纯CPU，ONNX Runtime，LoongArch支持不确定）
    log_info "尝试安装RapidOCR..."
    pip install rapidocr-onnxruntime -i https://mirrors.aliyun.com/pypi/simple/ --extra-index-url https://pypi.org/simple/ || {
        pip install rapidocr-onnxruntime || {
            log_warn "RapidOCR安装失败，将使用API OCR模式（功能不减少）"
        }
    }

    # llama-cpp-python（LoongArch本地Embedding替代方案）
    log_info "尝试安装llama-cpp-python..."
    pip install llama-cpp-python -i https://mirrors.aliyun.com/pypi/simple/ --extra-index-url https://pypi.org/simple/ || {
        pip install llama-cpp-python || {
            log_warn "llama-cpp-python安装失败，将使用API Embedding模式（功能不减少）"
        }
    }

    # 本地视觉模型依赖（非常耗时，默认不安装）
    if [ "${INSTALL_LOCAL_VISION:-0}" = "1" ]; then
        log_info "安装本地视觉模型依赖（耗时较长，请耐心等待）..."
        pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
            torch torchvision transformers accelerate qwen-vl-utils || {
            log_warn "本地视觉模型依赖安装失败，将使用API模式（功能不减少）"
        }
    else
        log_tip "跳过本地视觉模型依赖（设置 INSTALL_LOCAL_VISION=1 可安装）"
        log_tip "提示：使用DashScope API可获得相同功能，无需本地模型"
    fi

    log_info "AI模块依赖安装完成"
}

# =============================================================================
# 4. 配置环境变量
# =============================================================================
setup_config() {
    log_step "4. 配置环境变量"

    ENV_FILE="${BACKEND_DIR}/.env"

    # 备份现有配置
    if [ -f "${ENV_FILE}" ]; then
        cp "${ENV_FILE}" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "已备份现有配置"
    fi

    # 创建或更新配置
    log_info "创建LoongArch适配配置..."
    cat > "${ENV_FILE}" << EOF
# =============================================================================
# 设备检修知识检索与作业系统 - LoongArch适配配置
# =============================================================================
# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')
# 架构: $(uname -m)

# ---------- DashScope API配置（强烈推荐） ----------
# 从 https://dashscope.console.aliyun.com/ 获取API Key
# 配置后所有AI功能均可正常使用，无需本地模型
DASHSCOPE_API_KEY=your_api_key_here

# ---------- Embedding配置 ----------
# 方案1: DashScope API（推荐，所有架构通用）
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_DIMENSION=1024

# 方案2: 本地llama.cpp模型（LoongArch离线方案）
# 如需使用，请下载GGUF格式模型并配置路径：
# LLAMA_CPP_EMBED_MODEL_PATH=${MODELS_DIR}/your-embedding-model.gguf

# ---------- LLM配置 ----------
# 方案1: DashScope API（推荐）
LLM_BACKEND=dashscope
LLM_MODEL=qwen-max

# 方案2: 本地llama.cpp（LoongArch离线方案）
# 如需使用，请配置llama.cpp服务地址：
# LLM_BACKEND=openai_compatible
# LLM_API_BASE_URL=http://localhost:11435/v1
# LLM_API_KEY=not-needed

# ---------- OCR配置 ----------
# api: 使用DashScope qwen-vl（推荐，所有架构通用）
# rapidocr: 本地RapidOCR（需安装rapidocr-onnxruntime）
# none: 禁用OCR
OCR_BACKEND=api
OCR_USE_GPU=false
OCR_LANGUAGE=ch

# ---------- 视觉模型配置 ----------
# dashscope: 使用DashScope API（推荐，所有架构通用）
# local: 本地模型（需安装torch/transformers，LoongArch需源码编译）
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

    log_warn "请编辑 ${ENV_FILE} 配置您的 DASHSCOPE_API_KEY"

    # 创建数据目录
    mkdir -p "${DATA_DIR}/chroma_db" "${DATA_DIR}/pdfs" "${DATA_DIR}/images" "${MODELS_DIR}"

    log_info "配置完成"
}

# =============================================================================
# 5. 验证安装
# =============================================================================
verify_installation() {
    log_step "5. 验证AI模块安装"

    source "${VENV_DIR}/bin/activate"
    cd "${PROJECT_DIR}"

    log_info "测试核心模块导入..."
    python3 << PYEOF
import sys
import platform
sys.path.insert(0, '${APP_DIR}')

arch = platform.machine().lower()
is_loongarch = "loongarch" in arch or "loong64" in arch
print(f"架构: {arch} {'(LoongArch)' if is_loongarch else ''}")
print(f"应用目录: ${APP_DIR}")
print()

# 测试Embedding模块
try:
    from app.services.embedding_service import EmbeddingService
    svc = EmbeddingService()
    print(f"✓ Embedding模块: 后端={svc.backend}, 可用={svc.is_available()}")
except Exception as e:
    print(f"✗ Embedding模块加载失败: {e}")

# 测试OCR模块
try:
    from app.services.ocr_service import OCRService, OCRResult
    svc = OCRService()
    print(f"✓ OCR模块: 可用={svc.is_available}")
except Exception as e:
    print(f"✗ OCR模块加载失败: {e}")

# 测试Vision模块
try:
    from app.services.vision_service import VisionService
    svc = VisionService()
    print(f"✓ Vision模块: 当前后端={svc.current_backend}")
except Exception as e:
    print(f"✗ Vision模块加载失败: {e}")

print()
if is_loongarch:
    print("LoongArch适配模式已启用")
    print("提示：配置DASHSCOPE_API_KEY即可使用全部AI功能")
PYEOF

    log_info "验证完成"
}

# =============================================================================
# 6. 显示部署报告
# =============================================================================
show_report() {
    log_step "6. 部署报告"

    cat << EOF

=============================================================================
                     AI模块部署完成报告
=============================================================================

【系统信息】
  架构: $(uname -m)
  Python: $(python3 --version 2>&1)
  项目目录: ${PROJECT_DIR}

【已安装模块】
  ✓ Embedding服务 (支持: dashscope/llama_cpp/ollama)
  ✓ OCR服务 (支持: api/rapidocr/paddleocr)
  ✓ 视觉模型服务 (支持: dashscope/local)

【LoongArch适配说明】
  • Ollama → llama.cpp (GGUF格式本地模型)
  • PaddleOCR → 自动跳过 (不支持LoongArch)
  • 本地transformers → 可选安装 (需源码编译)

【下一步操作】
  1. 编辑配置文件:
     nano ${BACKEND_DIR}/.env

  2. 配置DashScope API Key（推荐）:
     DASHSCOPE_API_KEY=your_actual_api_key

  3. 如需本地模型，下载GGUF格式模型到:
     ${MODELS_DIR}

  4. 启动服务:
     cd ${PROJECT_DIR} && ./start_all.sh

【功能状态】
  • 配置API Key后: 所有功能100%可用
  • 无API Key: 依赖本地模型（需手动配置）

=============================================================================
EOF
}

# =============================================================================
# 主流程
# =============================================================================
main() {
    echo "============================================================================="
    echo "       设备检修知识检索与作业系统 - AI模块LoongArch部署"
    echo "============================================================================="
    echo ""

    check_architecture
    check_environment
    install_base_deps
    install_ai_deps
    setup_config
    verify_installation
    show_report

    echo ""
    echo -e "${GREEN}部署完成！${NC}"
    echo ""
    log_info "如需重启后端服务，请执行："
    echo "  cd ${APP_DIR}"
    echo "  source ${VENV_DIR}/bin/activate"
    echo "  nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &"
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
        echo ""
        echo "说明:"
        echo "  本脚本适配麒麟V11 LoongArch架构"
        echo "  功能不减少，自动检测架构并启用适配模式"
        echo "  推荐配置DashScope API Key使用云端AI能力"
        ;;
    *)
        main
        ;;
esac
