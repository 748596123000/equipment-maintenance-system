"""
FastAPI主入口模块

系统后端API服务的入口文件，负责：
- 创建FastAPI应用实例
- 配置CORS跨域中间件
- 注册所有API路由
- 管理应用生命周期事件（启动/关闭）
- 配置全局异常处理
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

_local_packages = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".pip_packages")
if os.path.isdir(_local_packages) and _local_packages not in sys.path:
    sys.path.insert(0, _local_packages)

if not os.environ.get("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings, get_settings
from app.utils.logger import setup_logger

# 设置日志
setup_logger(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


def _auto_detect_backends():
    import requests as _req

    db_config_loaded = False
    try:
        from app.models.database import get_database
        db = get_database()
        db_llm_model = db.get_config("llm_model")
        db_llm_backend = db.get_config("llm_backend")
        if db_llm_backend and db_llm_model:
            settings.LLM_BACKEND = db_llm_backend
            settings.LLM_MODEL = db_llm_model
            db_llm_base_url = db.get_config("llm_api_base_url")
            if db_llm_base_url:
                settings.LLM_API_BASE_URL = db_llm_base_url
            db_llm_api_key = db.get_config("llm_api_key")
            if db_llm_api_key:
                settings.LLM_API_KEY = db_llm_api_key
            db_config_loaded = True
            logger.info(f"从数据库加载LLM配置: {db_llm_backend}/{db_llm_model}")
    except Exception:
        pass

    llm_detected = None

    try:
        ollama_url = settings.LLM_API_BASE_URL or "http://localhost:11434"
        api_url = ollama_url.rstrip("/")
        if api_url.endswith("/v1"):
            api_url = api_url[:-3]
        resp = _req.get(f"{api_url}/api/tags", timeout=3)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            if models:
                if db_config_loaded:
                    model_name = settings.LLM_MODEL
                    llm_detected = f"ollama/{model_name}"
                    logger.info(f"使用数据库配置的 Ollama 模型: {model_name}")
                else:
                    import psutil
                    available_mem_gb = psutil.virtual_memory().available / (1024**3)
                    suitable_model = None
                    for m in models:
                        name = m["name"].lower()
                        size_gb = m.get("size", 0) / (1024**3)
                        if size_gb < available_mem_gb * 0.6:
                            suitable_model = m["name"]
                            break
                    model_name = suitable_model or models[0]["name"]
                    settings.LLM_BACKEND = "ollama"
                    settings.LLM_MODEL = model_name
                    if not settings.LLM_API_BASE_URL:
                        settings.LLM_API_BASE_URL = ollama_url
                    llm_detected = f"ollama/{model_name}"
                    logger.info(f"自动检测到 Ollama 本地模型: {model_name}")
    except Exception:
        pass

    if not llm_detected:
        try:
            resp = _req.get("http://localhost:11434/api/tags", timeout=3)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                if models:
                    if db_config_loaded:
                        model_name = settings.LLM_MODEL
                    else:
                        import psutil
                        available_mem_gb = psutil.virtual_memory().available / (1024**3)
                        suitable_model = None
                        for m in models:
                            size_gb = m.get("size", 0) / (1024**3)
                            if size_gb < available_mem_gb * 0.6:
                                suitable_model = m["name"]
                                break
                        model_name = suitable_model or models[0]["name"]
                    settings.LLM_BACKEND = "ollama"
                    settings.LLM_MODEL = model_name
                    settings.LLM_API_BASE_URL = "http://localhost:11434"
                    llm_detected = f"ollama/{model_name}"
                    logger.info(f"自动检测到 Ollama 本地模型: {model_name}")
        except Exception:
            pass

    if llm_detected:
        logger.info(f"LLM 后端: {llm_detected}")
        try:
            from app.models.database import get_database
            db = get_database()
            db.set_config("llm_backend", "ollama")
            db.set_config("llm_model", model_name)
            db.set_config("llm_api_base_url", settings.LLM_API_BASE_URL)
        except Exception:
            pass
    else:
        logger.warning("未检测到可用的 LLM 后端，AI问答功能不可用")
        logger.warning("请配置 DASHSCOPE_API_KEY 或启动 Ollama 服务")

    vision_model_id = None
    try:
        from huggingface_hub import scan_cache_dir
        cache = scan_cache_dir()
        vision_models = ["Qwen/Qwen2-VL-2B-Instruct", "Qwen/Qwen2-VL-7B-Instruct", "openbmb/MiniCPM-V-2_6"]
        for repo in cache.repos:
            if repo.repo_id in vision_models:
                vision_model_id = repo.repo_id
                break
    except Exception:
        cache_dir = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
        for mid in ["Qwen/Qwen2-VL-2B-Instruct", "Qwen/Qwen2-VL-7B-Instruct", "openbmb/MiniCPM-V-2_6"]:
            model_dir = os.path.join(cache_dir, "hub", f"models--{mid.replace('/', '--')}")
            if os.path.exists(model_dir):
                vision_model_id = mid
                break

    if vision_model_id:
        settings.LOCAL_VISION_MODEL = vision_model_id
        settings.VISION_BACKEND = "local"
        logger.info(f"视觉模型: 本地 {vision_model_id}")
        try:
            from app.models.database import get_database
            db = get_database()
            db.set_config("local_vision_model", vision_model_id)
            db.set_config("vision_backend", "local")
        except Exception:
            pass
        try:
            from app.services.vision_service import reset_vision_service
            reset_vision_service()
        except Exception:
            pass
    elif settings.DASHSCOPE_API_KEY and settings.DASHSCOPE_API_KEY != "your_api_key_here":
        settings.VISION_BACKEND = "dashscope"
        logger.info("视觉模型: DashScope API")
    else:
        settings.VISION_BACKEND = "auto"
        logger.warning("未检测到可用的视觉模型后端")

    ocr_detected = None
    try:
        import paddleocr
        ocr_detected = "paddleocr"
    except ImportError:
        pass
    if not ocr_detected:
        try:
            import rapidocr_onnxruntime
            ocr_detected = "rapidocr"
        except ImportError:
            pass
    if ocr_detected:
        settings.OCR_BACKEND = "auto"
        logger.info(f"OCR 后端: {ocr_detected} (auto)")
        try:
            from app.models.database import get_database
            db = get_database()
            db.set_config("ocr_backend", "auto")
        except Exception:
            pass
    else:
        logger.warning("未检测到可用的 OCR 后端")

    logger.info("=" * 40)
    logger.info("自动检测完成，当前配置:")
    logger.info(f"  LLM: {settings.LLM_BACKEND}/{settings.LLM_MODEL}")
    logger.info(f"  视觉: {settings.VISION_BACKEND}/{settings.LOCAL_VISION_MODEL}")
    logger.info(f"  OCR: {settings.OCR_BACKEND}")
    logger.info(f"  Embedding: {settings.EMBEDDING_MODEL}")
    logger.info("=" * 40)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("=" * 60)
    logger.info("设备检修知识检索与作业系统 - 正在启动...")
    logger.info("=" * 60)

    settings.ensure_directories()
    logger.info("数据目录检查完成")

    from app.models.database import get_database
    db = get_database()
    db.init_db()
    logger.info("数据库初始化完成")

    from app.core.retriever import get_retriever
    _retriever = get_retriever()
    logger.info("检索引擎已注册（懒加载）")

    from app.core.image_retriever import get_image_retriever
    _image_retriever = get_image_retriever()
    logger.info("图片检索已注册（懒加载）")

    from app.services.embedding_service import get_embedding_service
    embedding_service = get_embedding_service()
    if embedding_service.is_available():
        logger.info(f"Embedding模型就绪: {settings.EMBEDDING_MODEL}")
    else:
        logger.warning("Embedding API Key未配置，向量化功能不可用")

    _auto_detect_backends()

    from app.services.llm_service import get_llm_service
    llm_service = get_llm_service()
    if llm_service.is_available():
        logger.info(f"大语言模型就绪: {settings.LLM_BACKEND}/{settings.LLM_MODEL}")
    else:
        logger.warning(f"当前LLM后端 {settings.LLM_BACKEND} 不可用")

    if settings.VISION_BACKEND == "local" and settings.LOCAL_VISION_MODEL:
        import threading
        def _warmup_vision():
            try:
                from app.services.vision_service import get_vision_service
                vs = get_vision_service()
                vs.warmup()
            except Exception as e:
                logger.warning(f"视觉模型预热失败: {e}")
        warmup_thread = threading.Thread(target=_warmup_vision, daemon=True)
        warmup_thread.start()

    from app.utils.init_data import init_sample_data
    init_sample_data()

    from app.api.profile import init_user_profile_table
    init_user_profile_table()

    logger.info("系统启动完成，开始接收请求")

    import threading
    def _warmup():
        try:
            from app.core.retriever import get_retriever
            retriever = get_retriever()
            retriever.init_collection()
            logger.info("ChromaDB 预热完成")
        except Exception as e:
            logger.warning(f"ChromaDB 预热失败: {e}")
        try:
            from app.services.vision_service import get_vision_service
            vision_svc = get_vision_service()
            _ = vision_svc.current_backend
            logger.info("Vision 服务预热完成")
        except Exception as e:
            logger.warning(f"Vision 服务预热失败: {e}")
    threading.Thread(target=_warmup, daemon=True).start()

    yield

    logger.info("系统正在关闭...")
    try:
        db.close()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e}")
    logger.info("系统已安全关闭")


def create_app() -> FastAPI:
    """
    创建并配置FastAPI应用实例

    Returns:
        FastAPI: 配置完成的FastAPI应用
    """
    app = FastAPI(
        title="设备检修知识检索与作业系统",
        description="""
## 系统简介

基于多模态大模型技术的设备检修知识检索与作业系统，为工业设备检修提供智能化支持。

## 主要功能

### 📚 知识检索
- 文本检索：基于向量数据库的语义搜索
- 图片检索：多模态图像内容搜索
- 智能推荐：基于用户行为的个性化推荐

### 🤖 AI助手
- 智能问答：基于大模型的故障诊断
- 作业指引：标准化检修流程指导
- 案例匹配：相似案例智能推荐

### 📤 文档管理
- 文件上传：支持多种格式文档
- 审批流程：上传-审批-发布完整流程
- 知识图谱：可视化知识关联

### 🔔 通知系统
- 双向通知：用户-管理员消息交互
- 实时提醒：声音+桌面通知
- 消息持久化：数据库存储，永不丢失

## 技术架构

- 后端框架：FastAPI
- 向量数据库：ChromaDB
- 大模型：阿里云通义千问
- 前端框架：React + Tailwind CSS
        """,
        version="2.0.0",
        terms_of_service="https://www.example.com/terms/",
        contact={
            "name": "开发团队",
            "email": "contact@example.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self'; "
                "connect-src 'self' https://dashscope.aliyuncs.com; "
                "object-src 'none'; "
                "frame-ancestors 'none';"
            )
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            if not request.url.hostname or request.url.hostname not in ("localhost", "127.0.0.1"):
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            return response

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # ========== 注册路由 ==========
    from app.api.auth import router as auth_router
    from app.api.upload import router as upload_router
    from app.api.upload import public_router as upload_public_router
    from app.api.search import router as search_router
    from app.api.chat import router as chat_router
    from app.api.guide import router as guide_router
    from app.api.case import router as case_router
    from app.api.admin import router as admin_router, public_router as admin_public_router
    from app.api.models import router as models_router
    from app.api.knowledge_graph import router as knowledge_graph_router
    from app.api.feedback import router as feedback_router
    from app.api.notifications import router as notifications_router
    from app.api.ocr import router as ocr_router
    from app.api.profile import router as profile_router

    app.include_router(auth_router, prefix="/api/v1/auth", tags=["用户认证"])
    app.include_router(upload_router, prefix="/api/v1/upload", tags=["文件上传"])
    app.include_router(upload_public_router, prefix="/api/v1/upload", tags=["文件上传-公共"])
    app.include_router(search_router, prefix="/api/v1/search", tags=["知识检索"])
    app.include_router(chat_router, prefix="/api/v1/chat", tags=["AI问答"])
    app.include_router(guide_router, prefix="/api/v1/guide", tags=["作业指引"])
    app.include_router(case_router, prefix="/api/v1/case", tags=["检修案例"])
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["系统管理"])
    app.include_router(admin_public_router, prefix="/api/v1/admin", tags=["系统管理-公共"])
    app.include_router(models_router, prefix="/api/v1/models", tags=["模型管理"])
    app.include_router(knowledge_graph_router, prefix="/api/v1/knowledge-graph", tags=["知识图谱"])
    app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["反馈标注"])
    app.include_router(notifications_router, prefix="/api/v1/notifications", tags=["通知消息"])
    app.include_router(ocr_router, prefix="/api/v1", tags=["OCR识别"])
    app.include_router(profile_router, prefix="/api/v1", tags=["用户画像"])

    # ========== 全局异常处理 ==========
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """HTTP异常处理器"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": exc.detail,
                "data": None,
            }
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """参数验证异常处理器"""
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": f"参数错误: {str(exc)}",
                "data": None,
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """全局异常处理器，捕获未处理的异常并返回统一格式"""
        logger.error(f"未处理的异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误",
                "data": None,
                "detail": str(exc) if settings.DEBUG else "请联系管理员",
            }
        )

    # ========== 健康检查端点 ==========
    @app.get("/health", tags=["系统"])
    async def health_check():
        """健康检查接口，用于监控服务状态"""
        return {"status": "ok"}

    @app.get("/health/ready", summary="就绪检查")
    async def readiness_check():
        checks = {"api": True, "database": False, "llm": False}
        try:
            from app.models.database import get_database
            db = get_database()
            db.get_stats()
            checks["database"] = True
        except Exception:
            pass
        try:
            from app.services.llm_service import get_llm_service
            llm = get_llm_service()
            checks["llm"] = llm is not None
        except Exception:
            pass
        all_ready = all(checks.values())
        return {
            "status": "ready" if all_ready else "not_ready",
            "checks": checks
        }

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import os
    import uvicorn
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "production" and settings.DEBUG:
        logger.error("生产环境不允许启用DEBUG模式！")
        settings.DEBUG = False
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG and environment != "production",
    )
