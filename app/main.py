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
from contextlib import asynccontextmanager
from typing import AsyncGenerator

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理

    启动时：
    - 确保数据目录存在
    - 初始化数据库连接和表结构
    - 初始化ChromaDB向量数据库
    - 预加载Embedding模型

    关闭时：
    - 关闭数据库连接
    - 释放模型资源
    """
    logger.info("=" * 60)
    logger.info("设备检修知识检索与作业系统 - 正在启动...")
    logger.info("=" * 60)

    # 确保必要的目录存在
    settings.ensure_directories()
    logger.info("数据目录检查完成")

    # 初始化数据库
    from app.models.database import get_database
    db = get_database()
    db.init_db()
    logger.info("数据库初始化完成")

    # 初始化ChromaDB
    try:
        from app.core.retriever import get_retriever
        retriever = get_retriever()
        retriever.init_collection()
        logger.info("向量数据库初始化完成")
    except Exception as e:
        logger.warning(f"向量数据库初始化失败（系统仍可运行）: {e}")

    # 初始化图片检索集合
    try:
        from app.core.image_retriever import ImageRetriever
        image_retriever = ImageRetriever()
        image_retriever.init_collection()
        logger.info("图片向量集合初始化完成")
    except Exception as e:
        logger.warning(f"图片向量集合初始化失败（系统仍可运行）: {e}")

    # 预加载Embedding模型（检查API Key是否配置）
    try:
        from app.services.embedding_service import get_embedding_service
        embedding_service = get_embedding_service()
        if embedding_service.is_available():
            logger.info(f"Embedding模型就绪: {settings.EMBEDDING_MODEL}")
        else:
            logger.warning("Embedding API Key未配置，向量化功能不可用")
    except Exception as e:
        logger.warning(f"Embedding模型加载失败: {e}")

    # 检查LLM服务
    try:
        from app.services.llm_service import get_llm_service
        llm_service = get_llm_service()
        if llm_service.is_available():
            logger.info(f"大语言模型就绪: {settings.LLM_MODEL}")
        else:
            logger.warning("LLM API Key未配置，AI问答功能不可用")
    except Exception as e:
        logger.warning(f"LLM服务检查失败: {e}")

    # 初始化示例数据
    try:
        from app.utils.init_data import init_sample_data
        init_sample_data()
    except Exception as e:
        logger.warning(f"示例数据初始化失败: {e}")

    logger.info("系统启动完成，开始接收请求")

    yield

    # 关闭时清理资源
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
        description="基于多模态大模型技术的设备检修知识检索与作业系统API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
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
    from app.api.search import router as search_router
    from app.api.chat import router as chat_router
    from app.api.guide import router as guide_router
    from app.api.case import router as case_router
    from app.api.admin import router as admin_router

    app.include_router(auth_router, prefix="/api/v1/auth", tags=["用户认证"])
    app.include_router(upload_router, prefix="/api/v1/upload", tags=["文件上传"])
    app.include_router(search_router, prefix="/api/v1/search", tags=["知识检索"])
    app.include_router(chat_router, prefix="/api/v1/chat", tags=["AI问答"])
    app.include_router(guide_router, prefix="/api/v1/guide", tags=["作业指引"])
    app.include_router(case_router, prefix="/api/v1/case", tags=["检修案例"])
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["系统管理"])

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
