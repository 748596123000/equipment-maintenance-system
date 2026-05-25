"""
系统管理接口

提供系统管理功能：
- GET /admin/stats - 获取系统统计信息
- GET /admin/users - 获取用户列表
- POST /admin/users - 创建用户
- GET /admin/logs - 获取操作日志
- GET /admin/config - 获取配置
- PUT /admin/config - 更新配置
- POST /admin/test-connection - 测试API连接
- POST /admin/reindex - 重建索引
- GET /admin/health - 健康检查
- GET /admin/gpu-status - GPU状态
- POST /admin/gpu-cache/clear - 清理GPU缓存
- GET /admin/llm/models - LLM模型列表
- GET /admin/llm/status - LLM服务状态
- GET /admin/services/status - 所有服务状态
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

CONFIG_FIELD_MAP = {
    "dashscope_api_key": ("DASHSCOPE_API_KEY", str, True),
    "llm_backend": ("LLM_BACKEND", str, False),
    "llm_model": ("LLM_MODEL", str, False),
    "llm_temperature": ("LLM_TEMPERATURE", float, False),
    "llm_max_tokens": ("LLM_MAX_TOKENS", int, False),
    "llm_api_base_url": ("LLM_API_BASE_URL", str, False),
    "llm_api_key": ("LLM_API_KEY", str, True),
    "embedding_model": ("EMBEDDING_MODEL", str, False),
    "chunk_size": ("CHUNK_SIZE", int, False),
    "chunk_overlap": ("CHUNK_OVERLAP", int, False),
    "top_k_results": ("TOP_K_RESULTS", int, False),
    "retriever_score_threshold": ("RETRIEVER_SCORE_THRESHOLD", float, False),
    "ocr_backend": ("OCR_BACKEND", str, False),
    "ocr_use_gpu": ("OCR_USE_GPU", bool, False),
    "ocr_language": ("OCR_LANGUAGE", str, False),
    "vision_backend": ("VISION_BACKEND", str, False),
    "local_vision_model": ("LOCAL_VISION_MODEL", str, False),
}

SECRET_FIELDS = {"dashscope_api_key", "llm_api_key"}


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    display_name: str = Field(default="", description="显示名称")
    role: str = Field(default="viewer", description="角色: admin / editor / viewer")
    department: str = Field(default="", description="部门")


class ConfigUpdateRequest(BaseModel):
    dashscope_api_key: Optional[str] = Field(default=None, description="DashScope API密钥")
    llm_backend: Optional[str] = Field(default=None, description="LLM后端类型")
    llm_model: Optional[str] = Field(default=None, description="大模型名称")
    llm_temperature: Optional[float] = Field(default=None, description="生成温度")
    llm_max_tokens: Optional[int] = Field(default=None, description="最大输出token数")
    llm_api_base_url: Optional[str] = Field(default=None, description="OpenAI兼容API基础URL")
    llm_api_key: Optional[str] = Field(default=None, description="OpenAI兼容API密钥")
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


class TestConnectionRequest(BaseModel):
    service: str = Field(..., description="服务类型: llm / embedding / vision / ocr")
    backend: Optional[str] = Field(default=None, description="后端类型(可选，默认用当前配置)")
    api_key: Optional[str] = Field(default=None, description="API密钥(可选，默认用当前配置)")
    base_url: Optional[str] = Field(default=None, description="API基础URL(可选，默认用当前配置)")
    model: Optional[str] = Field(default=None, description="模型名称(可选，默认用当前配置)")


@router.get("/stats", summary="获取系统统计信息")
async def get_system_stats():
    db = get_database()
    conn = db.get_connection()

    try:
        doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        case_count = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        user_count = conn.execute("SELECT COUNT(*) FROM users WHERE is_active = 1").fetchone()[0]
        chat_count = conn.execute("SELECT COUNT(*) FROM chat_sessions").fetchone()[0]
        guide_count = conn.execute("SELECT COUNT(*) FROM guides").fetchone()[0]
        total_chunks = conn.execute("SELECT COALESCE(SUM(chunk_count), 0) FROM documents").fetchone()[0]

        db_size_mb = 0.0
        if os.path.exists(settings.SQLITE_DB_PATH):
            db_size_mb = os.path.getsize(settings.SQLITE_DB_PATH) / (1024 * 1024)

        chroma_status = "unknown"
        try:
            chroma_dir = settings.CHROMA_PERSIST_DIR
            if os.path.exists(chroma_dir) and os.listdir(chroma_dir):
                chroma_status = "healthy"
            elif os.path.exists(chroma_dir):
                chroma_status = "empty"
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
    db = get_database()

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
    db = get_database()

    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.get("username") == "admin":
        raise HTTPException(status_code=400, detail="不能删除管理员账户")

    try:
        db.delete_user(user_id)
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
    config_data = {}
    for field_name, (attr_name, _, is_secret) in CONFIG_FIELD_MAP.items():
        value = getattr(settings, attr_name, None)
        if is_secret and value:
            config_data[field_name] = "******"
        else:
            config_data[field_name] = value

    config_data.update({
        "max_upload_size": settings.MAX_UPLOAD_SIZE,
        "api_host": settings.API_HOST,
        "api_port": settings.API_PORT,
        "debug": settings.DEBUG,
    })

    return {
        "code": 200,
        "message": "查询成功",
        "data": config_data,
    }


@router.put("/config", summary="更新系统配置")
async def update_system_config(request: ConfigUpdateRequest):
    updated_fields = {}
    db = get_database()
    need_reset_llm = False
    need_reset_ocr = False
    need_reset_vision = False
    need_reset_embedding = False

    for field_name, (attr_name, type_func, is_secret) in CONFIG_FIELD_MAP.items():
        value = getattr(request, field_name, None)
        if value is None:
            continue
        if is_secret and value == "******":
            continue

        setattr(settings, attr_name, type_func(value))
        updated_fields[field_name] = "******" if is_secret else value
        db.set_config(field_name, str(value))

        if field_name in ("llm_backend", "llm_model", "llm_temperature", "llm_max_tokens",
                          "llm_api_base_url", "llm_api_key", "dashscope_api_key"):
            need_reset_llm = True
        if field_name in ("dashscope_api_key",):
            need_reset_embedding = True
        if field_name in ("ocr_backend", "ocr_use_gpu", "ocr_language"):
            need_reset_ocr = True
        if field_name in ("vision_backend", "local_vision_model", "dashscope_api_key"):
            need_reset_vision = True

    if not updated_fields:
        raise HTTPException(status_code=400, detail="没有需要更新的配置项")

    db.save_log(
        user_id=None,
        action="更新系统配置",
        detail=f"fields={list(updated_fields.keys())}",
    )

    if need_reset_llm:
        from app.services.llm_service import reset_llm_service
        reset_llm_service()
    if need_reset_embedding:
        from app.services.embedding_service import reset_embedding_service
        reset_embedding_service()
    if need_reset_ocr:
        from app.services.ocr_service import reset_ocr_service
        reset_ocr_service()
    if need_reset_vision:
        from app.services.vision_service import reset_vision_service
        reset_vision_service()

    return {
        "code": 200,
        "message": "配置更新成功",
        "data": updated_fields,
    }


@router.post("/test-connection", summary="测试API连接")
async def test_connection(request: TestConnectionRequest):
    service = request.service.lower()
    result = {
        "service": service,
        "success": False,
        "message": "",
        "latency_ms": 0,
    }

    import time

    if service == "llm":
        backend = request.backend or settings.LLM_BACKEND
        api_key = request.api_key or (settings.DASHSCOPE_API_KEY if backend == "dashscope" else settings.LLM_API_KEY)
        base_url = request.base_url or settings.LLM_API_BASE_URL
        model = request.model or settings.LLM_MODEL

        try:
            from app.services.llm_service import LLMService, DASHSCOPE_BASE_URL, OLLAMA_DEFAULT_URL, MINIMAX_BASE_URL, DEEPSEEK_BASE_URL, ZHIPU_BASE_URL, BAICHUAN_BASE_URL, MOONSHOT_BASE_URL, SILICONFLOW_BASE_URL, LLM_PROVIDER_INFO
            start = time.time()

            if backend == "dashscope":
                svc = LLMService(api_key=api_key, model=model, backend="dashscope")
                svc.chat([{"role": "user", "content": "hi"}], max_tokens=5)
            elif backend == "ollama":
                url = base_url or f"{OLLAMA_DEFAULT_URL}/v1"
                svc = LLMService(api_key=api_key or "ollama", model=model, backend="ollama", base_url=url)
                svc.chat([{"role": "user", "content": "hi"}], max_tokens=5)
            elif backend == "openai_compatible":
                if not base_url:
                    raise ValueError("OpenAI兼容模式需要提供API基础URL")
                svc = LLMService(api_key=api_key, model=model, backend="openai_compatible", base_url=base_url)
                svc.chat([{"role": "user", "content": "hi"}], max_tokens=5)
            elif backend == "minimax":
                svc = LLMService(api_key=api_key, model=model, backend="minimax")
                svc.chat([{"role": "user", "content": "hi"}], max_tokens=5)
            elif backend == "deepseek":
                svc = LLMService(api_key=api_key, model=model, backend="deepseek")
                svc.chat([{"role": "user", "content": "hi"}], max_tokens=5)
            elif backend == "zhipu":
                svc = LLMService(api_key=api_key, model=model, backend="zhipu")
                svc.chat([{"role": "user", "content": "hi"}], max_tokens=5)
            elif backend == "baichuan":
                svc = LLMService(api_key=api_key, model=model, backend="baichuan")
                svc.chat([{"role": "user", "content": "hi"}], max_tokens=5)
            elif backend == "moonshot":
                svc = LLMService(api_key=api_key, model=model, backend="moonshot")
                svc.chat([{"role": "user", "content": "hi"}], max_tokens=5)
            elif backend == "siliconflow":
                svc = LLMService(api_key=api_key, model=model, backend="siliconflow")
                svc.chat([{"role": "user", "content": "hi"}], max_tokens=5)

            elapsed = (time.time() - start) * 1000
            result["success"] = True
            result["message"] = f"连接成功，模型: {model}，延迟: {elapsed:.0f}ms"
            result["latency_ms"] = round(elapsed, 1)
        except Exception as e:
            result["message"] = f"连接失败: {str(e)[:200]}"

    elif service == "embedding":
        api_key = request.api_key or settings.DASHSCOPE_API_KEY
        model = request.model or settings.EMBEDDING_MODEL

        if not api_key or api_key == "your_api_key_here":
            result["message"] = "DashScope API Key 未配置"
        else:
            try:
                import dashscope
                from dashscope import TextEmbedding
                dashscope.api_key = api_key

                start = time.time()
                resp = TextEmbedding.call(model=model, input="test")
                elapsed = (time.time() - start) * 1000

                if resp.status_code == 200:
                    dim = len(resp.output['embeddings'][0]['embedding'])
                    result["success"] = True
                    result["message"] = f"连接成功，模型: {model}，维度: {dim}，延迟: {elapsed:.0f}ms"
                    result["latency_ms"] = round(elapsed, 1)
                else:
                    result["message"] = f"API返回错误 (status={resp.status_code})"
            except Exception as e:
                result["message"] = f"连接失败: {str(e)[:200]}"

    elif service == "vision":
        backend = request.backend or settings.VISION_BACKEND
        api_key = request.api_key or settings.DASHSCOPE_API_KEY

        if backend == "dashscope" or (backend == "auto" and api_key):
            if not api_key or api_key == "your_api_key_here":
                result["message"] = "DashScope API Key 未配置"
            else:
                try:
                    import dashscope
                    from dashscope import MultiModalConversation

                    dashscope.api_key = api_key
                    start = time.time()
                    resp = MultiModalConversation.call(
                        model="qwen-vl-plus",
                        messages=[{
                            "role": "user",
                            "content": [{"text": "hi"}]
                        }],
                    )
                    elapsed = (time.time() - start) * 1000

                    if resp.status_code == 200:
                        result["success"] = True
                        result["message"] = f"DashScope视觉API连接成功，延迟: {elapsed:.0f}ms"
                        result["latency_ms"] = round(elapsed, 1)
                    else:
                        result["message"] = f"API返回错误 (status={resp.status_code})"
                except Exception as e:
                    result["message"] = f"连接失败: {str(e)[:200]}"
        elif backend == "local":
            try:
                from app.services.vision_service import get_vision_service
                vision_svc = get_vision_service()
                if vision_svc.is_local_available:
                    result["success"] = True
                    result["message"] = f"本地视觉模型可用: {settings.LOCAL_VISION_MODEL}"
                else:
                    result["message"] = f"本地视觉模型不可用: {settings.LOCAL_VISION_MODEL}"
            except Exception as e:
                result["message"] = f"检测失败: {str(e)[:200]}"
        else:
            result["message"] = "无可用的视觉模型后端"

    elif service == "ocr":
        try:
            from app.services.ocr_service import get_ocr_service
            ocr_svc = get_ocr_service()
            start = time.time()
            test_result = ocr_svc.recognize("测试OCR连接")
            elapsed = (time.time() - start) * 1000

            if test_result is not None:
                result["success"] = True
                result["message"] = f"OCR服务可用，后端: {settings.OCR_BACKEND}，延迟: {elapsed:.0f}ms"
                result["latency_ms"] = round(elapsed, 1)
            else:
                result["message"] = f"OCR服务不可用，后端: {settings.OCR_BACKEND}"
        except Exception as e:
            result["message"] = f"连接失败: {str(e)[:200]}"

    else:
        raise HTTPException(status_code=400, detail=f"不支持的服务类型: {service}")

    return {
        "code": 200,
        "message": "测试完成",
        "data": result,
    }


@router.get("/services/status", summary="获取所有服务状态")
async def get_all_services_status():
    services = {}

    try:
        from app.services.llm_service import get_llm_service
        llm = get_llm_service()
        services["llm"] = {
            "available": llm.is_available(),
            "backend": settings.LLM_BACKEND,
            "model": settings.LLM_MODEL,
        }
    except Exception as e:
        services["llm"] = {"available": False, "error": str(e)[:100]}

    try:
        from app.services.embedding_service import get_embedding_service
        emb = get_embedding_service()
        services["embedding"] = {
            "available": emb.is_available(),
            "model": settings.EMBEDDING_MODEL,
        }
    except Exception as e:
        services["embedding"] = {"available": False, "error": str(e)[:100]}

    try:
        from app.services.ocr_service import get_ocr_service
        ocr = get_ocr_service()
        services["ocr"] = {
            "available": ocr.is_available if ocr._initialized else (settings.OCR_BACKEND != "none"),
            "backend": settings.OCR_BACKEND,
        }
    except Exception as e:
        services["ocr"] = {"available": False, "error": str(e)[:100]}

    try:
        from app.services.vision_service import get_vision_service
        vision = get_vision_service()
        services["vision"] = {
            "available": vision.current_backend != "unavailable",
            "backend": settings.VISION_BACKEND,
            "current_backend": vision.current_backend,
        }
    except Exception as e:
        services["vision"] = {"available": False, "error": str(e)[:100]}

    has_key = bool(settings.DASHSCOPE_API_KEY and settings.DASHSCOPE_API_KEY != "your_api_key_here")
    services["dashscope"] = {
        "available": has_key,
        "api_key_set": has_key,
    }

    minimax_key = bool(settings.LLM_API_KEY and settings.LLM_API_KEY != "your_api_key_here")
    services["minimax"] = {
        "available": minimax_key,
        "api_key_set": minimax_key,
    }

    return {
        "code": 200,
        "message": "查询成功",
        "data": services,
    }


@router.post("/reindex", summary="重建索引")
async def rebuild_index():
    try:
        from app.core.retriever import get_retriever
        retriever = get_retriever()
        result = retriever.rebuild_index()

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
    health_info = {
        "status": "healthy",
        "service": "equipment-maintenance-system",
        "version": "1.0.0",
        "components": {},
    }

    try:
        db = get_database()
        conn = db.get_connection()
        conn.execute("SELECT 1")
        health_info["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_info["components"]["database"] = {"status": "error", "message": str(e)}
        health_info["status"] = "degraded"

    try:
        from app.core.retriever import get_retriever
        retriever = get_retriever()
        retriever._ensure_collection()
        health_info["components"]["chromadb"] = {"status": "healthy"}
    except Exception as e:
        health_info["components"]["chromadb"] = {"status": "error", "message": str(e)}
        health_info["status"] = "degraded"

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
    from app.utils.gpu_utils import get_gpu_info
    from app.services.ocr_service import get_ocr_service
    from app.services.vision_service import get_vision_service

    gpu_info = get_gpu_info()

    ocr_svc = get_ocr_service()
    ocr_status = {
        "backend": settings.OCR_BACKEND,
        "use_gpu": settings.OCR_USE_GPU,
        "language": settings.OCR_LANGUAGE,
        "available": ocr_svc.is_available if ocr_svc._initialized else (settings.OCR_BACKEND != "none"),
        "engine_loaded": ocr_svc._initialized and ocr_svc._engine is not None,
        "engine_type": ocr_svc.engine_type,
    }

    vision_svc = get_vision_service()
    current_vision_backend = vision_svc.current_backend
    if current_vision_backend == "auto":
        if vision_svc.is_local_available:
            current_vision_backend = "local (auto)"
        elif settings.DASHSCOPE_API_KEY:
            current_vision_backend = "dashscope (auto)"
        else:
            current_vision_backend = "unavailable (auto)"

    vision_status = {
        "backend": settings.VISION_BACKEND,
        "local_model": settings.LOCAL_VISION_MODEL,
        "local_available": vision_svc.is_local_available,
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
    from app.utils.gpu_utils import clear_gpu_cache as do_clear
    do_clear()

    return {
        "code": 200,
        "message": "GPU缓存已清理",
        "data": {"cleared": True},
    }


@router.get("/llm/models", summary="获取LLM可用模型列表")
async def get_llm_models(
    backend: Optional[str] = Query(default=None, description="LLM后端类型"),
    base_url: Optional[str] = Query(default=None, description="API基础URL"),
    api_key: Optional[str] = Query(default=None, description="API密钥"),
):
    from app.services.llm_service import LLMService

    query_backend = backend or settings.LLM_BACKEND
    models = []

    if query_backend == "dashscope":
        models = [
            {"id": "qwen-max", "name": "Qwen Max（最强）"},
            {"id": "qwen-plus", "name": "Qwen Plus（均衡）"},
            {"id": "qwen-turbo", "name": "Qwen Turbo（最快）"},
            {"id": "qwen-long", "name": "Qwen Long（长文本）"},
        ]
    elif query_backend == "minimax":
        models = [
            {"id": "abab6.5s-chat", "name": "ABAB 6.5S Chat（推荐）"},
            {"id": "abab6.5g-chat", "name": "ABAB 6.5G Chat"},
            {"id": "abab5.5s-chat", "name": "ABAB 5.5S Chat"},
            {"id": "abab5.5g-chat", "name": "ABAB 5.5G Chat"},
        ]
    elif query_backend == "deepseek":
        models = [
            {"id": "deepseek-chat", "name": "DeepSeek Chat（推荐）"},
            {"id": "deepseek-coder", "name": "DeepSeek Coder（代码）"},
            {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner（推理）"},
        ]
    elif query_backend == "zhipu":
        models = [
            {"id": "glm-4", "name": "GLM-4（最强）"},
            {"id": "glm-4-flash", "name": "GLM-4-Flash（快速）"},
            {"id": "glm-3-turbo", "name": "GLM-3-Turbo（均衡）"},
        ]
    elif query_backend == "baichuan":
        models = [
            {"id": "Baichuan4", "name": "Baichuan4（推荐）"},
            {"id": "Baichuan3-Turbo", "name": "Baichuan3-Turbo"},
            {"id": "Baichuan2-Open", "name": "Baichuan2-Open"},
        ]
    elif query_backend == "moonshot":
        models = [
            {"id": "moonshot-v1-128k", "name": "Moonshot V1 128K（长文本）"},
            {"id": "moonshot-v1-32k", "name": "Moonshot V1 32K（推荐）"},
            {"id": "moonshot-v1-8k", "name": "Moonshot V1 8K"},
        ]
    elif query_backend == "siliconflow":
        models = [
            {"id": "Qwen/Qwen2.5-72B-Instruct", "name": "Qwen2.5-72B（推荐）"},
            {"id": "deepseek-ai/DeepSeek-V2.5", "name": "DeepSeek V2.5"},
            {"id": "THUDM/GLM-4-9B-Chat", "name": "GLM-4-9B"},
            {"id": "Qwen/Qwen2-VL-72B-Instruct", "name": "Qwen2-VL-72B"},
        ]
    elif query_backend == "ollama":
        ollama_available = LLMService.check_ollama_available()
        ollama_models = LLMService.list_ollama_models() if ollama_available else []
        models = [{"id": m["name"], "name": m["name"]} for m in ollama_models]
    elif query_backend == "openai_compatible":
        url = base_url or settings.LLM_API_BASE_URL
        key = api_key or settings.LLM_API_KEY
        if url:
            try:
                import requests as req
                headers = {"Content-Type": "application/json"}
                if key:
                    headers["Authorization"] = f"Bearer {key}"
                resp = req.get(f"{url.rstrip('/')}/models", headers=headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("data", []):
                        mid = m.get("id", "")
                        models.append({"id": mid, "name": mid})
            except Exception as e:
                logger.debug(f"获取OpenAI兼容模型列表失败: {e}")

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "backend": query_backend,
            "models": models,
        },
    }


@router.get("/llm/status", summary="获取LLM服务状态")
async def get_llm_status():
    from app.services.llm_service import LLMService, OLLAMA_DEFAULT_URL

    backend = settings.LLM_BACKEND
    status_info = {
        "backend": backend,
        "model": settings.LLM_MODEL,
        "available": False,
        "connection": "unknown",
    }

    if backend == "dashscope":
        status_info["available"] = bool(settings.DASHSCOPE_API_KEY and settings.DASHSCOPE_API_KEY != "your_api_key_here")
        status_info["connection"] = "ok" if status_info["available"] else "no_api_key"
    elif backend == "ollama":
        ollama_available = LLMService.check_ollama_available()
        status_info["available"] = ollama_available
        status_info["connection"] = "ok" if ollama_available else "unreachable"
        status_info["url"] = settings.LLM_API_BASE_URL or OLLAMA_DEFAULT_URL
    elif backend == "openai_compatible":
        url = settings.LLM_API_BASE_URL
        if url:
            status_info["available"] = LLMService.check_api_available(url, settings.LLM_API_KEY)
            status_info["connection"] = "ok" if status_info["available"] else "error"
            status_info["url"] = url
        else:
            status_info["connection"] = "no_url"
    elif backend == "minimax":
        status_info["available"] = bool(settings.LLM_API_KEY and settings.LLM_API_KEY != "your_api_key_here")
        status_info["connection"] = "ok" if status_info["available"] else "no_api_key"
        status_info["url"] = "https://api.minimax.chat/v1"
    elif backend == "deepseek":
        status_info["available"] = bool(settings.LLM_API_KEY and settings.LLM_API_KEY != "your_api_key_here")
        status_info["connection"] = "ok" if status_info["available"] else "no_api_key"
        status_info["url"] = "https://api.deepseek.com/v1"
    elif backend == "zhipu":
        status_info["available"] = bool(settings.LLM_API_KEY and settings.LLM_API_KEY != "your_api_key_here")
        status_info["connection"] = "ok" if status_info["available"] else "no_api_key"
        status_info["url"] = "https://open.bigmodel.cn/api/paas/v4"
    elif backend == "baichuan":
        status_info["available"] = bool(settings.LLM_API_KEY and settings.LLM_API_KEY != "your_api_key_here")
        status_info["connection"] = "ok" if status_info["available"] else "no_api_key"
        status_info["url"] = "https://api.baichuan-ai.com/v1"
    elif backend == "moonshot":
        status_info["available"] = bool(settings.LLM_API_KEY and settings.LLM_API_KEY != "your_api_key_here")
        status_info["connection"] = "ok" if status_info["available"] else "no_api_key"
        status_info["url"] = "https://api.moonshot.cn/v1"
    elif backend == "siliconflow":
        status_info["available"] = bool(settings.LLM_API_KEY and settings.LLM_API_KEY != "your_api_key_here")
        status_info["connection"] = "ok" if status_info["available"] else "no_api_key"
        status_info["url"] = "https://api.siliconflow.cn/v1"

    return {
        "code": 200,
        "message": "查询成功",
        "data": status_info,
    }
