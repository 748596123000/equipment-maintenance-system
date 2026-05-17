"""
系统管理接口

提供系统管理功能：
- GET /admin/stats - 获取系统统计信息
- GET /admin/users - 获取用户列表
- POST /admin/users - 创建用户
- GET /admin/logs - 获取操作日志
- GET /admin/config - 获取配置
- PUT /admin/config - 更新配置
- POST /admin/reindex - 重建索引
- GET /admin/health - 健康检查
"""

import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.auth import require_admin, hash_password
from app.config import settings
from app.models.database import get_database
from app.utils.helpers import calculate_pagination

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_admin)])


class UserCreateRequest(BaseModel):
    """用户创建请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    display_name: str = Field(default="", description="显示名称")
    role: str = Field(default="viewer", description="角色: admin / editor / viewer")
    department: str = Field(default="", description="部门")


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    llm_model: Optional[str] = Field(default=None, description="大模型名称")
    llm_temperature: Optional[float] = Field(default=None, description="生成温度")
    llm_max_tokens: Optional[int] = Field(default=None, description="最大输出token数")
    embedding_model: Optional[str] = Field(default=None, description="Embedding模型名称")
    chunk_size: Optional[int] = Field(default=None, description="分块大小")
    chunk_overlap: Optional[int] = Field(default=None, description="分块重叠大小")
    top_k_results: Optional[int] = Field(default=None, description="检索结果数")
    retriever_score_threshold: Optional[float] = Field(default=None, description="检索相似度阈值")
    ocr_backend: Optional[str] = Field(default=None, description="OCR后端")
    ocr_use_gpu: Optional[bool] = Field(default=None, description="OCR使用GPU")
    ocr_language: Optional[str] = Field(default=None, description="OCR语言")
    vision_backend: Optional[str] = Field(default=None, description="视觉模型后端")
    local_vision_model: Optional[str] = Field(default=None, description="本地视觉模型")


@router.get("/stats", summary="获取系统统计信息")
async def get_system_stats():
    """
    获取系统运行统计数据

    Returns:
        dict: 系统统计信息
    """
    db = get_database()
    conn = db.get_connection()

    try:
        # 文档数量
        doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

        # 案例数量
        case_count = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]

        # 用户数量
        user_count = conn.execute("SELECT COUNT(*) FROM users WHERE is_active = 1").fetchone()[0]

        # 对话数量
        chat_count = conn.execute("SELECT COUNT(*) FROM chat_sessions").fetchone()[0]

        # 指引数量
        guide_count = conn.execute("SELECT COUNT(*) FROM guides").fetchone()[0]

        # 总文本块数（从文档表汇总）
        total_chunks = conn.execute("SELECT COALESCE(SUM(chunk_count), 0) FROM documents").fetchone()[0]

        # 数据库文件大小
        db_size_mb = 0.0
        if os.path.exists(settings.SQLITE_DB_PATH):
            db_size_mb = os.path.getsize(settings.SQLITE_DB_PATH) / (1024 * 1024)

        # 检查ChromaDB状态
        chroma_status = "unknown"
        try:
            chroma_dir = settings.CHROMA_PERSIST_DIR
            if os.path.exists(chroma_dir):
                chroma_status = "healthy"
            else:
                chroma_status = "not_initialized"
        except Exception:
            chroma_status = "error"

        return {
            "code": 200,
            "message": "查询成功",
            "data": {
                "document_count": doc_count,
                "case_count": case_count,
                "total_chunks": total_chunks,
                "user_count": user_count,
                "chat_count": chat_count,
                "guide_count": guide_count,
                "chroma_status": chroma_status,
                "db_size_mb": round(db_size_mb, 2),
            }
        }
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")


@router.get("/users", summary="获取用户列表")
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    role: Optional[str] = Query(default=None),
):
    """
    获取系统用户列表

    Args:
        page: 页码
        page_size: 每页数量
        role: 角色筛选

    Returns:
        dict: 用户列表
    """
    db = get_database()
    result = db.list_users(page=page, page_size=page_size, role=role)

    pagination = calculate_pagination(page, page_size, result["total"])

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "users": result["users"],
            "pagination": pagination,
        }
    }


@router.post("/users", summary="创建用户")
async def create_user(request: UserCreateRequest):
    """
    创建新用户

    Args:
        request: 用户创建请求

    Returns:
        dict: 创建的用户信息
    """
    db = get_database()

    # 检查用户名是否已存在
    existing = db.get_user_by_username(request.username)
    if existing:
        raise HTTPException(status_code=400, detail=f"用户名 '{request.username}' 已存在")

    try:
        import uuid
        user_id = str(uuid.uuid4())
        password_hash = hash_password(request.password)

        db.create_user(
            user_id=user_id,
            username=request.username,
            password_hash=password_hash,
            role=request.role,
        )

        # 记录日志
        db.save_log(
            user_id=None,
            action=f"创建用户: {request.username}",
            detail=f"role={request.role}",
        )

        return {
            "code": 200,
            "message": "用户创建成功",
            "data": {
                "user_id": user_id,
                "username": request.username,
                "role": request.role,
                "display_name": request.display_name,
            }
        }
    except Exception as e:
        logger.error(f"用户创建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")


@router.delete("/users/{user_id}", summary="删除用户")
async def delete_user(user_id: str):
    """
    删除用户（不能删除admin账户）

    Args:
        user_id: 用户ID
    """
    db = get_database()

    # 获取用户信息
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 不允许删除admin账户
    if user.get("username") == "admin":
        raise HTTPException(status_code=400, detail="不能删除管理员账户")

    try:
        db.delete_user(user_id)

        # 记录日志
        db.save_log(
            user_id=None,
            action=f"删除用户: {user.get('username', '')}",
            detail=f"user_id={user_id}",
        )

        return {"code": 200, "message": f"用户 '{user.get('username', '')}' 已删除"}
    except Exception as e:
        logger.error(f"删除用户失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")


@router.get("/logs", summary="获取操作日志")
async def get_system_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    level: Optional[str] = Query(default=None, description="日志级别筛选"),
    start_date: Optional[str] = Query(default=None, description="开始日期"),
    end_date: Optional[str] = Query(default=None, description="结束日期"),
):
    """
    获取系统操作日志

    Args:
        page: 页码
        page_size: 每页数量
        level: 日志级别筛选
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        dict: 日志列表
    """
    db = get_database()
    result = db.get_logs(
        page=page,
        page_size=page_size,
        action=level,
        start_date=start_date,
        end_date=end_date,
    )

    pagination = calculate_pagination(page, page_size, result["total"])

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "logs": result["logs"],
            "pagination": pagination,
        }
    }


@router.get("/config", summary="获取系统配置")
async def get_system_config():
    """
    获取当前系统配置信息

    Returns:
        dict: 系统配置
    """
    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "llm_model": settings.LLM_MODEL,
            "embedding_model": settings.EMBEDDING_MODEL,
            "llm_temperature": settings.LLM_TEMPERATURE,
            "llm_max_tokens": settings.LLM_MAX_TOKENS,
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP,
            "top_k_results": settings.TOP_K_RESULTS,
            "retriever_score_threshold": settings.RETRIEVER_SCORE_THRESHOLD,
            "max_upload_size": settings.MAX_UPLOAD_SIZE,
            "api_host": settings.API_HOST,
            "api_port": settings.API_PORT,
            "debug": settings.DEBUG,
            "ocr_backend": settings.OCR_BACKEND,
            "ocr_use_gpu": settings.OCR_USE_GPU,
            "ocr_language": settings.OCR_LANGUAGE,
            "vision_backend": settings.VISION_BACKEND,
            "local_vision_model": settings.LOCAL_VISION_MODEL,
        }
    }


@router.put("/config", summary="更新系统配置")
async def update_system_config(request: ConfigUpdateRequest):
    """
    更新系统运行配置（运行时生效，不持久化到.env）

    Args:
        request: 配置更新请求

    Returns:
        dict: 更新结果
    """
    updated_fields = {}

    if request.llm_model is not None:
        settings.LLM_MODEL = request.llm_model
        updated_fields["llm_model"] = request.llm_model

    if request.llm_temperature is not None:
        settings.LLM_TEMPERATURE = request.llm_temperature
        updated_fields["llm_temperature"] = request.llm_temperature

    if request.llm_max_tokens is not None:
        settings.LLM_MAX_TOKENS = request.llm_max_tokens
        updated_fields["llm_max_tokens"] = request.llm_max_tokens

    if request.embedding_model is not None:
        settings.EMBEDDING_MODEL = request.embedding_model
        updated_fields["embedding_model"] = request.embedding_model

    if request.chunk_size is not None:
        settings.CHUNK_SIZE = request.chunk_size
        updated_fields["chunk_size"] = request.chunk_size

    if request.chunk_overlap is not None:
        settings.CHUNK_OVERLAP = request.chunk_overlap
        updated_fields["chunk_overlap"] = request.chunk_overlap

    if request.top_k_results is not None:
        settings.TOP_K_RESULTS = request.top_k_results
        updated_fields["top_k_results"] = request.top_k_results

    if request.retriever_score_threshold is not None:
        settings.RETRIEVER_SCORE_THRESHOLD = request.retriever_score_threshold
        updated_fields["retriever_score_threshold"] = request.retriever_score_threshold

    if request.ocr_backend is not None:
        settings.OCR_BACKEND = request.ocr_backend
        updated_fields["ocr_backend"] = request.ocr_backend

    if request.ocr_use_gpu is not None:
        settings.OCR_USE_GPU = request.ocr_use_gpu
        updated_fields["ocr_use_gpu"] = request.ocr_use_gpu

    if request.ocr_language is not None:
        settings.OCR_LANGUAGE = request.ocr_language
        updated_fields["ocr_language"] = request.ocr_language

    if request.vision_backend is not None:
        settings.VISION_BACKEND = request.vision_backend
        updated_fields["vision_backend"] = request.vision_backend

    if request.local_vision_model is not None:
        settings.LOCAL_VISION_MODEL = request.local_vision_model
        updated_fields["local_vision_model"] = request.local_vision_model

    if not updated_fields:
        raise HTTPException(status_code=400, detail="没有需要更新的配置项")

    db = get_database()
    for field, value in [
        ("llm_model", request.llm_model),
        ("llm_temperature", str(request.llm_temperature) if request.llm_temperature is not None else None),
        ("llm_max_tokens", str(request.llm_max_tokens) if request.llm_max_tokens is not None else None),
        ("embedding_model", request.embedding_model),
        ("chunk_size", str(request.chunk_size) if request.chunk_size is not None else None),
        ("chunk_overlap", str(request.chunk_overlap) if request.chunk_overlap is not None else None),
        ("top_k_results", str(request.top_k_results) if request.top_k_results is not None else None),
        ("retriever_score_threshold", str(request.retriever_score_threshold) if request.retriever_score_threshold is not None else None),
        ("ocr_backend", request.ocr_backend),
        ("ocr_use_gpu", str(request.ocr_use_gpu) if request.ocr_use_gpu is not None else None),
        ("ocr_language", request.ocr_language),
        ("vision_backend", request.vision_backend),
        ("local_vision_model", request.local_vision_model),
    ]:
        if value is not None:
            db.set_config(field, str(value))

    # 记录日志
    db.save_log(
        user_id=None,
        action="更新系统配置",
        detail=f"fields={list(updated_fields.keys())}",
    )

    return {
        "code": 200,
        "message": "配置更新成功",
        "data": updated_fields,
    }


@router.post("/reindex", summary="重建索引")
async def rebuild_index():
    """
    重建ChromaDB向量索引

    Returns:
        dict: 重建进度信息
    """
    try:
        from app.core.retriever import get_retriever
        retriever = get_retriever()
        result = retriever.rebuild_index()

        # 记录日志
        db = get_database()
        db.save_log(
            user_id=None,
            action="重建向量索引",
            detail=f"status={result.get('status')}, chunks={result.get('total_chunks', 0)}",
        )

        return {
            "code": 200,
            "message": "索引重建任务已提交",
            "data": result,
        }
    except Exception as e:
        logger.error(f"索引重建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")


@router.get("/health", summary="健康检查")
async def health_check():
    """
    系统健康检查，检查各组件状态

    Returns:
        dict: 健康状态信息
    """
    health_info = {
        "status": "healthy",
        "service": "equipment-maintenance-system",
        "version": "1.0.0",
        "components": {},
    }

    # 检查数据库
    try:
        db = get_database()
        conn = db.get_connection()
        conn.execute("SELECT 1")
        health_info["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_info["components"]["database"] = {"status": "error", "message": str(e)}
        health_info["status"] = "degraded"

    # 检查ChromaDB
    try:
        from app.core.retriever import get_retriever
        retriever = get_retriever()
        retriever._ensure_collection()
        health_info["components"]["chromadb"] = {"status": "healthy"}
    except Exception as e:
        health_info["components"]["chromadb"] = {"status": "error", "message": str(e)}
        health_info["status"] = "degraded"

    # 检查LLM服务
    try:
        from app.services.llm_service import get_llm_service
        llm_service = get_llm_service()
        available = llm_service.is_available()
        health_info["components"]["llm"] = {
            "status": "healthy" if available else "unavailable",
            "model": settings.LLM_MODEL,
        }
        if not available:
            health_info["status"] = "degraded"
    except Exception as e:
        health_info["components"]["llm"] = {"status": "error", "message": str(e)}
        health_info["status"] = "degraded"

    # 检查Embedding服务
    try:
        from app.services.embedding_service import get_embedding_service
        embedding_service = get_embedding_service()
        available = embedding_service.is_available()
        health_info["components"]["embedding"] = {
            "status": "healthy" if available else "unavailable",
            "model": settings.EMBEDDING_MODEL,
        }
        if not available:
            health_info["status"] = "degraded"
    except Exception as e:
        health_info["components"]["embedding"] = {"status": "error", "message": str(e)}
        health_info["status"] = "degraded"

    return {
        "code": 200 if health_info["status"] == "healthy" else 503,
        "message": "系统正常" if health_info["status"] == "healthy" else "部分组件异常",
        "data": health_info,
    }


@router.get("/gpu-status", summary="获取GPU状态")
async def get_gpu_status():
    """
    获取GPU加速相关状态信息，包括GPU设备、OCR服务、视觉模型

    Returns:
        dict: GPU状态信息
    """
    from app.utils.gpu_utils import get_gpu_info
    from app.services.ocr_service import get_ocr_service
    from app.services.vision_service import get_vision_service

    gpu_info = get_gpu_info()

    ocr_svc = get_ocr_service()
    ocr_status = {
        "backend": settings.OCR_BACKEND,
        "use_gpu": settings.OCR_USE_GPU,
        "language": settings.OCR_LANGUAGE,
        "available": ocr_svc.is_available,
        "engine_loaded": ocr_svc._initialized and ocr_svc._engine is not None,
    }

    vision_svc = get_vision_service()
    current_vision_backend = vision_svc.backend
    if current_vision_backend == "auto":
        if gpu_info["available"]:
            current_vision_backend = "local (auto)"
        elif settings.DASHSCOPE_API_KEY:
            current_vision_backend = "dashscope (auto)"
        else:
            current_vision_backend = "unavailable (auto)"

    vision_status = {
        "backend": settings.VISION_BACKEND,
        "local_model": settings.LOCAL_VISION_MODEL,
        "local_available": vision_svc.is_local_available if gpu_info["available"] else False,
        "current_backend": current_vision_backend,
    }

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "gpu": gpu_info,
            "ocr": ocr_status,
            "vision": vision_status,
        },
    }


@router.post("/gpu-cache/clear", summary="清理GPU缓存")
async def clear_gpu_cache_endpoint():
    """
    手动清理GPU显存缓存（torch + paddle）

    Returns:
        dict: 清理结果
    """
    from app.utils.gpu_utils import clear_gpu_cache as do_clear

    do_clear()

    return {
        "code": 200,
        "message": "GPU缓存已清理",
        "data": {"cleared": True},
    }
