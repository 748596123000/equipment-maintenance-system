"""
AI问答接口

提供基于RAG的智能问答功能：
- POST /chat/send - 发送问答请求
- GET /chat/stream - SSE流式问答
- GET /chat/history/{session_id} - 获取对话历史
- DELETE /chat/session/{session_id} - 删除对话会话
"""

import base64
import json
import logging
import time
import uuid
from typing import Dict, List, Literal, Optional

from cachetools import TTLCache
from fastapi import APIRouter, Depends, HTTPException, Query, Security
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.models.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])

# SSE流式认证
_stream_security = HTTPBearer(auto_error=False)


async def _verify_stream_token(token: Optional[str]) -> dict:
    from app.api.auth import _token_store
    from datetime import datetime, timezone
    if not token:
        raise HTTPException(status_code=401, detail="未提供认证凭据")
    token_data = _token_store.get(token)
    if not token_data or datetime.now(timezone.utc) > token_data.get("expires_at", datetime.min.replace(tzinfo=timezone.utc)):
        raise HTTPException(status_code=401, detail="无效或已过期的Token")
    db = get_database()
    user = db.get_user_by_id(token_data["user_id"])
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user

_response_cache: TTLCache = TTLCache(maxsize=500, ttl=3600)
_RESPONSE_CACHE_TTL = 60
_MAX_CACHE_ITEM_SIZE = 50000  # 单条缓存最大字符数

_session_last_query: TTLCache = TTLCache(maxsize=1000, ttl=7200)


class ChatRequest(BaseModel):
    """问答请求"""
    question: str = Field(..., min_length=1, max_length=5000, description="用户问题")
    session_id: Optional[str] = Field(default=None, description="会话ID，为空则创建新会话")
    context: Optional[List[dict]] = Field(default=None, description="上下文对话历史")
    search_mode: Literal["semantic", "keyword", "hybrid"] = Field(default="hybrid", description="检索模式: semantic / keyword / hybrid")
    top_k: int = Field(default=5, ge=1, le=20, description="检索结果数量")
    category: Optional[str] = Field(default=None, description="限定知识分类")
    image_base64: Optional[str] = Field(default=None, max_length=10_000_000, description="图片Base64编码（可选，用于图片问答）")


@router.get("/sessions", summary="获取会话列表")
async def list_sessions(current_user: dict = Depends(get_current_user)):
    db = get_database()
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT id, user_id, created_at, updated_at FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC",
        (current_user["id"],)
    ).fetchall()
    sessions = [{"id": r[0], "user_id": r[1], "created_at": r[2], "updated_at": r[3]} for r in rows]
    return {"code": 200, "message": "查询成功", "data": {"sessions": sessions, "total": len(sessions)}}


@router.post("/send", summary="发送问答请求")
async def chat_send(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    发送问答请求，系统将：
    1. 对用户问题进行知识检索
    2. 将检索结果作为上下文，调用大模型生成回答
    3. 返回回答及引用的知识来源

    优化：
    - 相同session的连续相似问题复用检索结果
    - 完全相同的问题在1分钟内不重复调用LLM

    Args:
        request: 问答请求参数

    Returns:
        dict: AI回答、引用来源和会话信息
    """
    import hashlib

    # 生成或复用会话ID
    session_id = request.session_id or str(uuid.uuid4())
    db = get_database()

    try:
        # Base64解码前检查大小
        if request.image_base64 and len(request.image_base64) > 10_000_000:
            raise HTTPException(status_code=400, detail="图片数据过大，请压缩后重试")
        # 步骤0: 检查响应缓存（完全相同的问题在1分钟内直接返回）
        question_hash = hashlib.md5(request.question.encode()).hexdigest()
        if question_hash in _response_cache:
            cached = _response_cache[question_hash]
            if time.time() - cached["timestamp"] < _RESPONSE_CACHE_TTL:
                logger.info(f"命中响应缓存: question='{request.question[:30]}...'")
                # 仍然保存对话记录
                db.save_chat_message(
                    session_id=session_id,
                    role="user",
                    content=request.question,
                    user_id=current_user["id"],
                )
                db.save_chat_message(
                    session_id=session_id,
                    role="assistant",
                    content=cached["answer"],
                    sources=cached["sources"],
                    confidence=cached["confidence"],
                    user_id=current_user["id"],
                )
                return {
                    "code": 200,
                    "message": "回答生成成功（缓存）",
                    "data": {
                        "session_id": session_id,
                        "answer": cached["answer"],
                        "sources": cached["sources"],
                        "confidence": round(cached["confidence"], 4),
                        "cached": True,
                    }
                }
            else:
                del _response_cache[question_hash]

        # 步骤0.5: 如果有图片，先调用image_retriever描述图片
        actual_question = request.question
        if request.image_base64:
            try:
                from app.core.image_retriever import get_image_retriever
                image_retriever = get_image_retriever()
                image_bytes = base64.b64decode(request.image_base64)
                image_description = image_retriever._extract_image_features(image_bytes)
                # 将图片描述和用户问题组合
                actual_question = f"[图片描述]: {image_description}\n\n[用户问题]: {request.question}"
                logger.info(f"图片描述生成成功，组合问题长度: {len(actual_question)}")
            except Exception as img_err:
                logger.warning(f"图片描述生成失败，仅使用文本问题: {img_err}")
                actual_question = request.question

        # 步骤1: 知识检索（相同session的连续相似问题复用检索结果）
        from app.core.retriever import get_retriever
        retriever = get_retriever()

        # 检查session级别的相似问题缓存
        search_results = None
        if session_id in _session_last_query:
            last_q = _session_last_query[session_id]["question"]
            # 简单的包含关系或前缀匹配
            if (actual_question == last_q
                    or actual_question in last_q
                    or last_q in actual_question
                    or (len(actual_question) > 3 and len(last_q) > 3
                        and (actual_question.startswith(last_q[:4]) or last_q.startswith(actual_question[:4])))):
                logger.info(f"session={session_id} 问题相似，复用上次检索结果")
                search_results = _session_last_query[session_id]["results"]

        if search_results is None:
            if request.search_mode == "semantic":
                search_results = retriever.search(
                    query=actual_question,
                    top_k=request.top_k,
                )
            elif request.search_mode == "keyword":
                keywords = actual_question.split()[:5]
                search_results = retriever.keyword_search(
                    keywords=keywords,
                    top_k=request.top_k,
                )
            else:
                search_results = retriever.hybrid_search(
                    query=actual_question,
                    top_k=request.top_k,
                )
            # 更新session级别的查询缓存
            _session_last_query[session_id] = {
                "question": actual_question,
                "results": search_results,
            }

        # 格式化检索结果
        search_results_dict = []
        for r in search_results:
            if hasattr(r, "to_dict"):
                search_results_dict.append(r.to_dict())
            elif isinstance(r, dict):
                search_results_dict.append(r)

        # 步骤2: 构建对话历史
        chat_history = []
        if request.context:
            chat_history = [
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                for msg in request.context
            ]
        else:
            # 从数据库加载历史
            history = db.get_chat_history(session_id, limit=10)
            chat_history = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in history
            ]

        # 步骤3: 调用RAG引擎生成回答
        from app.core.rag_engine import get_rag_engine
        rag_engine = get_rag_engine()
        result = rag_engine.chat(
            question=actual_question,
            search_results=search_results_dict,
            chat_history=chat_history,
        )

        answer = result["answer"]
        confidence = result["confidence"]
        sources = result.get("sources", [])

        # 步骤4: 保存对话记录到数据库
        db.save_chat_message(
            session_id=session_id,
            role="user",
            content=request.question,
            user_id=current_user["id"],
        )
        db.save_chat_message(
            session_id=session_id,
            role="assistant",
            content=answer,
            sources=sources,
            confidence=confidence,
            user_id=current_user["id"],
        )

        # 步骤5: 检查是否应该缓存（敏感问题不缓存）
        sensitive_patterns = ["密码", "password", "密钥", "token", "secret", "key"]
        should_cache = not any(p.lower() in request.question.lower() for p in sensitive_patterns)
        
        # 缓存响应结果（1分钟内相同问题直接返回）
        if should_cache:
            # 截断过长的响应以避免内存问题
            cached_answer = answer[:_MAX_CACHE_ITEM_SIZE] if len(answer) > _MAX_CACHE_ITEM_SIZE else answer
            _response_cache[question_hash] = {
                "answer": cached_answer,
                "sources": sources,
                "confidence": confidence,
                "timestamp": time.time(),
            }

        # 记录日志
        db.save_log(
            user_id=current_user["id"],
            action=f"AI问答: {request.question[:50]}",
            detail=f"session={session_id}, confidence={confidence:.2f}, sources={len(sources)}",
        )

        return {
            "code": 200,
            "message": "回答生成成功",
            "data": {
                "session_id": session_id,
                "answer": answer,
                "sources": sources,
                "confidence": round(confidence, 4),
            }
        }
    except Exception as e:
        logger.error(f"问答生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")


@router.get("/stream", summary="SSE流式问答")
async def chat_stream(
    question: str = Query(..., min_length=1, max_length=5000, description="用户问题"),
    session_id: Optional[str] = Query(default=None, description="会话ID"),
    search_mode: Literal["semantic", "keyword", "hybrid"] = Query(default="hybrid", description="检索模式"),
    top_k: int = Query(default=5, ge=1, le=20, description="检索结果数量"),
    credentials: HTTPAuthorizationCredentials = Security(_stream_security),
):
    """
    SSE流式问答接口，逐步返回回答内容

    Args:
        question: 用户问题
        session_id: 会话ID
        search_mode: 检索模式
        top_k: 检索结果数量
        credentials: 认证凭据（必需）

    Returns:
        StreamingResponse: SSE流式响应
    """
    current_user = await _verify_stream_token(credentials.credentials)
    session_id = session_id or str(uuid.uuid4())
    db = get_database()

    async def generate_stream():
        """SSE事件流生成器"""
        try:
            # 发送会话ID
            yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

            # 步骤1: 知识检索
            from app.core.retriever import get_retriever
            retriever = get_retriever()

            if search_mode == "semantic":
                search_results = retriever.search(query=question, top_k=top_k)
            elif search_mode == "keyword":
                keywords = question.split()[:5]
                search_results = retriever.keyword_search(keywords=keywords, top_k=top_k)
            else:
                search_results = retriever.hybrid_search(query=question, top_k=top_k)

            search_results_dict = [
                r.to_dict() if hasattr(r, "to_dict") else r
                for r in search_results
            ]

            # 发送检索来源信息
            sources_info = [
                {
                    "source": r.get("source", ""),
                    "content": r.get("content", "")[:200],
                    "score": r.get("score", 0),
                    "page_number": r.get("page_number"),
                }
                for r in search_results_dict[:3]
            ]
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources_info})}\n\n"

            # 步骤2: 加载历史
            history = db.get_chat_history(session_id, limit=10)
            chat_history = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in history
            ]

            # 步骤3: 流式生成回答
            from app.core.rag_engine import get_rag_engine
            rag_engine = get_rag_engine()

            context = rag_engine._build_context(search_results_dict)
            full_answer = ""

            for chunk in rag_engine.stream_generate(
                question=question,
                context=context,
                chat_history=chat_history,
            ):
                full_answer += chunk
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

            # 步骤4: 保存对话记录
            db.save_chat_message(session_id=session_id, role="user", content=question, user_id=current_user["id"] if current_user else None)
            db.save_chat_message(
                session_id=session_id,
                role="assistant",
                content=full_answer,
                sources=sources_info,
                user_id=current_user["id"] if current_user else None,
            )

            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"流式问答失败: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history/{session_id}", summary="获取对话历史")
async def get_chat_history(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=200, description="最大消息数量"),
    current_user: dict = Depends(get_current_user),
):
    """
    获取指定会话的对话历史记录

    Args:
        session_id: 会话ID
        limit: 返回的最大消息数量

    Returns:
        dict: 对话历史列表
    """
    db = get_database()
    conn = db.get_connection()
    session_row = conn.execute("SELECT user_id FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
    if session_row:
        session = dict(session_row)
        if session.get("user_id") and session["user_id"] != current_user["id"] and current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="无权访问此会话")

    history = db.get_chat_history(session_id, limit=limit)

    # 格式化消息
    messages = []
    for msg in history:
        message = {
            "id": msg.get("id", ""),
            "role": msg.get("role", ""),
            "content": msg.get("content", ""),
            "sources": msg.get("sources", []),
            "confidence": msg.get("confidence", 0.0),
            "created_at": msg.get("created_at", ""),
        }
        messages.append(message)

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "session_id": session_id,
            "messages": messages,
            "total": len(messages),
        }
    }


@router.delete("/session/{session_id}", summary="删除对话会话")
async def delete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """
    删除指定的对话会话及其所有消息记录

    Args:
        session_id: 会话ID

    Returns:
        dict: 删除结果
    """
    db = get_database()
    conn = db.get_connection()

    session_row = conn.execute("SELECT user_id FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
    if session_row:
        session = dict(session_row)
        if session.get("user_id") and session["user_id"] != current_user["id"] and current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="无权访问此会话")

    conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))

    # 再删除会话
    cursor = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    conn.commit()

    deleted = cursor.rowcount > 0

    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 记录日志
    db.save_log(
        user_id=current_user["id"],
        action=f"删除对话会话: {session_id}",
    )

    logger.info(f"会话已删除: {session_id}")

    return {
        "code": 200,
        "message": "会话删除成功",
        "data": {"session_id": session_id}
    }
