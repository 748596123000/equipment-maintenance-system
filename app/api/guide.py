"""
作业指引接口

提供AI驱动的作业指引生成功能：
- POST /guide/generate - 生成作业指引
- GET /guide/stream - SSE流式生成作业指引
- GET /guide/list - 获取历史指引列表
- GET /guide/{guide_id} - 获取指引详情
- GET /guide/export/{guide_id} - 导出指引（返回文本格式）
"""

import json
import logging
import uuid
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.models.database import get_database
from app.utils.helpers import calculate_pagination

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


class GuideGenerateRequest(BaseModel):
    """作业指引生成请求"""
    task_description: str = Field(..., min_length=1, max_length=5000, description="作业任务描述")
    equipment_model: Optional[str] = Field(default=None, description="设备型号")
    equipment_type: Optional[str] = Field(default=None, description="设备类型")
    work_environment: Optional[str] = Field(default=None, description="作业环境描述")
    safety_level: Literal["low", "standard", "high", "critical"] = Field(default="standard", description="安全等级: low / standard / high / critical")
    detail_level: Literal["brief", "medium", "detailed"] = Field(default="medium", description="详细程度: brief / medium / detailed")


@router.post("/generate", summary="生成作业指引")
async def generate_guide(request: GuideGenerateRequest, current_user: dict = Depends(get_current_user)):
    """
    基于任务描述和设备信息，AI自动生成结构化的作业指引

    系统将：
    1. 根据任务描述检索相关知识
    2. 结合设备信息和安全要求
    3. 生成步骤化的作业指引

    Args:
        request: 作业指引生成请求

    Returns:
        dict: 生成的作业指引内容
    """
    guide_id = str(uuid.uuid4())
    db = get_database()

    try:
        # 步骤1: 检索相关知识
        from app.core.retriever import get_retriever
        retriever = get_retriever()

        search_query = request.task_description
        if request.equipment_type:
            search_query = f"{request.equipment_type} {request.task_description}"
        if request.equipment_model:
            search_query = f"{request.equipment_model} {search_query}"

        search_results = retriever.hybrid_search(
            query=search_query,
            top_k=10,
        )

        # 构建知识上下文
        knowledge_context = ""
        for r in search_results:
            if hasattr(r, "to_dict"):
                data = r.to_dict()
            elif isinstance(r, dict):
                data = r
            else:
                continue
            source = data.get("source", "未知来源")
            content = data.get("content", "")
            knowledge_context += f"[来源: {source}]\n{content}\n\n"

        # 步骤2: 调用作业指引生成引擎
        from app.core.guide_generator import GuideGenerator
        generator = GuideGenerator()
        guide = generator.generate(
            task_description=request.task_description,
            device_model=request.equipment_model,
            equipment_type=request.equipment_type,
            work_environment=request.work_environment,
            safety_level=request.safety_level,
            detail_level=request.detail_level,
        )

        # 步骤3: 保存到数据库
        guide_dict = guide.to_dict()
        guide_content = json.dumps(guide_dict, ensure_ascii=False, indent=2)

        conn = db.get_connection()
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO guides (id, title, task_description, equipment_type, equipment_model,
               safety_level, guide_content, created_by, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (guide_id, guide.title, request.task_description,
             request.equipment_type or "", request.equipment_model or "",
             request.safety_level, guide_content, current_user["id"], now, now),
        )
        conn.commit()

        # 记录日志
        db.save_log(
            user_id=current_user["id"],
            action=f"生成作业指引: {guide.title}",
            detail=f"guide_id={guide_id}, steps={len(guide.steps)}",
        )

        return {
            "code": 200,
            "message": "作业指引生成成功",
            "data": guide_dict,
        }

    except Exception as e:
        logger.error(f"作业指引生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.get("/stream", summary="SSE流式生成作业指引")
async def stream_guide(
    task_description: str = Query(..., min_length=1, description="作业任务描述"),
    equipment_model: Optional[str] = Query(default=None, description="设备型号"),
    equipment_type: Optional[str] = Query(default=None, description="设备类型"),
    safety_level: str = Query(default="standard", description="安全等级"),
    detail_level: str = Query(default="medium", description="详细程度"),
):
    """
    SSE流式生成作业指引，逐步返回每个步骤的内容

    Args:
        task_description: 作业任务描述
        equipment_model: 设备型号
        equipment_type: 设备类型
        safety_level: 安全等级
        detail_level: 详细程度

    Returns:
        StreamingResponse: SSE流式响应
    """
    guide_id = str(uuid.uuid4())
    db = get_database()

    async def generate_stream():
        """SSE事件流生成器"""
        try:
            # 发送指引ID
            yield f"data: {json.dumps({'type': 'guide_id', 'guide_id': guide_id})}\n\n"

            # 检索相关知识
            from app.core.retriever import get_retriever
            retriever = get_retriever()
            search_query = f"{equipment_type or ''} {task_description}"
            search_results = retriever.hybrid_search(query=search_query, top_k=10)

            knowledge_context = ""
            for r in search_results:
                if hasattr(r, "to_dict"):
                    data = r.to_dict()
                elif isinstance(r, dict):
                    data = r
                else:
                    continue
                knowledge_context += f"[来源: {data.get('source', '')}]\n{data.get('content', '')}\n\n"

            # 流式生成
            from app.core.guide_generator import GuideGenerator
            generator = GuideGenerator()

            full_content = ""
            for chunk in generator.stream_generate(
                task_description=task_description,
                device_model=equipment_model,
                equipment_type=equipment_type,
                safety_level=safety_level,
                detail_level=detail_level,
            ):
                full_content += chunk
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

            # 保存到数据库
            conn = db.get_connection()
            now = datetime.now().isoformat()
            conn.execute(
                """INSERT INTO guides (id, title, task_description, equipment_type, equipment_model,
                   safety_level, guide_content, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (guide_id, f"作业指引 - {task_description[:30]}", task_description,
                 equipment_type or "", equipment_model or "",
                 safety_level, full_content, now, now),
            )
            conn.commit()

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"流式生成失败: {e}", exc_info=True)
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


@router.get("/list", summary="获取历史指引列表")
async def list_guides(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    equipment_type: Optional[str] = Query(default=None),
):
    """
    获取已生成的作业指引列表

    Args:
        page: 页码
        page_size: 每页数量
        equipment_type: 设备类型筛选

    Returns:
        dict: 作业指引列表
    """
    db = get_database()
    conn = db.get_connection()

    # 构建查询条件
    conditions = []
    params: list = []
    if equipment_type:
        conditions.append("equipment_type = ?")
        params.append(equipment_type)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # 查询总数
    count_result = conn.execute(
        f"SELECT COUNT(*) FROM guides {where_clause}", params
    ).fetchone()
    total = count_result[0]

    # 查询列表
    offset = (page - 1) * page_size
    cursor = conn.execute(
        f"""SELECT id, title, task_description, equipment_type, equipment_model,
                   safety_level, created_at
            FROM guides {where_clause}
            ORDER BY created_at DESC LIMIT ? OFFSET ?""",
        params + [page_size, offset],
    )
    guides = []
    for row in cursor.fetchall():
        guides.append({
            "guide_id": row["id"],
            "title": row["title"],
            "task_description": row["task_description"],
            "equipment_type": row["equipment_type"],
            "equipment_model": row["equipment_model"],
            "safety_level": row["safety_level"],
            "created_at": row["created_at"],
        })

    pagination = calculate_pagination(page, page_size, total)

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "guides": guides,
            "pagination": pagination,
        }
    }


@router.get("/{guide_id}", summary="获取作业指引详情")
async def get_guide(guide_id: str, current_user: dict = Depends(get_current_user)):
    """
    获取指定ID的作业指引完整内容

    Args:
        guide_id: 指引ID

    Returns:
        dict: 作业指引详情
    """
    db = get_database()
    conn = db.get_connection()
    cursor = conn.execute(
        "SELECT * FROM guides WHERE id = ?", (guide_id,)
    )
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="作业指引不存在")

    if row["created_by"] and row["created_by"] != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="无权访问此作业指引")

    # 解析指引内容
    guide_content = {}
    try:
        guide_content = json.loads(row["guide_content"])
    except (json.JSONDecodeError, TypeError):
        guide_content = {"raw_content": row["guide_content"]}

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "guide_id": row["id"],
            "title": row["title"],
            "task_description": row["task_description"],
            "equipment_type": row["equipment_type"],
            "equipment_model": row["equipment_model"],
            "safety_level": row["safety_level"],
            "guide_content": guide_content,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    }


@router.get("/export/{guide_id}", summary="导出指引")
async def export_guide(guide_id: str, current_user: dict = Depends(get_current_user)):
    """
    导出作业指引为纯文本格式

    Args:
        guide_id: 指引ID

    Returns:
        PlainTextResponse: 纯文本格式的指引内容
    """
    db = get_database()
    conn = db.get_connection()
    cursor = conn.execute(
        "SELECT * FROM guides WHERE id = ?", (guide_id,)
    )
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="作业指引不存在")

    if row["created_by"] and row["created_by"] != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="无权访问此作业指引")

    # 解析指引内容并生成文本
    try:
        guide_data = json.loads(row["guide_content"])
    except (json.JSONDecodeError, TypeError):
        guide_data = {"raw_content": row["guide_content"]}

    # 生成纯文本格式
    text_lines = []
    text_lines.append(f"{'='*60}")
    text_lines.append(f"  {guide_data.get('title', row['title'])}")
    text_lines.append(f"{'='*60}")
    text_lines.append("")

    # 任务概述
    if guide_data.get("task_summary"):
        text_lines.append("【任务概述】")
        text_lines.append(guide_data["task_summary"])
        text_lines.append("")

    # 准备工作
    if guide_data.get("preparation"):
        text_lines.append("【准备工作】")
        for i, item in enumerate(guide_data["preparation"], 1):
            text_lines.append(f"  {i}. {item}")
        text_lines.append("")

    # 安全注意事项
    if guide_data.get("safety_notes"):
        text_lines.append("【安全注意事项】")
        for note in guide_data["safety_notes"]:
            text_lines.append(f"  - {note}")
        text_lines.append("")

    # 作业步骤
    if guide_data.get("steps"):
        text_lines.append("【作业步骤】")
        text_lines.append("-" * 40)
        for step in guide_data["steps"]:
            num = step.get("step_number", "?")
            title = step.get("title", "")
            text_lines.append(f"\n  步骤 {num}: {title}")
            text_lines.append(f"  {'~' * 30}")

            desc = step.get("description", "")
            if desc:
                text_lines.append(f"  {desc}")

            warnings = step.get("warnings", [])
            if warnings:
                text_lines.append("  [安全警告]")
                for w in warnings:
                    text_lines.append(f"    !! {w}")

            tools = step.get("tools_required", [])
            if tools:
                text_lines.append(f"  [所需工具]: {', '.join(tools)}")

            est_time = step.get("estimated_time", "")
            if est_time:
                text_lines.append(f"  [预计耗时]: {est_time}")

            tips = step.get("tips", [])
            if tips:
                text_lines.append("  [操作提示]")
                for tip in tips:
                    text_lines.append(f"    * {tip}")

        text_lines.append("")

    # 完成标准
    if guide_data.get("completion_criteria"):
        text_lines.append("【完成标准】")
        for i, criterion in enumerate(guide_data["completion_criteria"], 1):
            text_lines.append(f"  {i}. {criterion}")
        text_lines.append("")

    text_lines.append(f"{'='*60}")
    text_lines.append(f"生成时间: {row['created_at']}")
    text_lines.append(f"{'='*60}")

    export_text = "\n".join(text_lines)

    return PlainTextResponse(
        content=export_text,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=guide_{guide_id}.txt",
        },
    )
