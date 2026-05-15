"""
检修案例接口

提供检修案例的管理和检索功能：
- POST /case/create - 创建检修案例
- GET /case/list - 获取案例列表（支持分页、筛选）
- GET /case/{case_id} - 获取案例详情
- PUT /case/{case_id} - 更新案例
- DELETE /case/{case_id} - 删除案例
- POST /case/search - 检索案例
- POST /case/review - 审核案例（通过/拒绝）
"""

import json
import logging
import uuid
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.auth import get_current_user, require_admin
from app.models.database import get_database
from app.utils.helpers import calculate_pagination

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class CaseCreateRequest(BaseModel):
    """案例创建请求"""
    title: str = Field(..., min_length=1, max_length=200, description="案例标题")
    equipment_type: str = Field(..., min_length=1, description="设备类型")
    equipment_model: str = Field(default="", description="设备型号")
    fault_description: str = Field(..., min_length=1, description="故障描述")
    fault_analysis: str = Field(default="", description="故障分析")
    repair_process: str = Field(default="", description="维修过程")
    repair_result: str = Field(default="", description="维修结果")
    lessons_learned: str = Field(default="", description="经验教训")
    tags: List[str] = Field(default_factory=list, description="标签")


class CaseUpdateRequest(BaseModel):
    """案例更新请求"""
    title: Optional[str] = Field(default=None, description="案例标题")
    fault_description: Optional[str] = Field(default=None, description="故障描述")
    fault_analysis: Optional[str] = Field(default=None, description="故障分析")
    repair_process: Optional[str] = Field(default=None, description="维修过程")
    repair_result: Optional[str] = Field(default=None, description="维修结果")
    lessons_learned: Optional[str] = Field(default=None, description="经验教训")
    tags: Optional[List[str]] = Field(default=None, description="标签")


class CaseReviewRequest(BaseModel):
    """案例审核请求"""
    case_id: str = Field(..., description="案例ID")
    status: Literal["approved", "rejected"] = Field(..., description="审核状态: approved / rejected")
    review_comment: str = Field(default="", description="审核意见")


class CaseSearchRequest(BaseModel):
    """案例检索请求"""
    query: str = Field(..., min_length=1, description="检索关键词")
    equipment_type: Optional[str] = Field(default=None, description="设备类型筛选")
    tags: Optional[List[str]] = Field(default=None, description="标签筛选")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


@router.post("/create", summary="创建检修案例")
async def create_case(request: CaseCreateRequest, current_user: dict = Depends(get_current_user)):
    """
    创建新的检修案例记录

    Args:
        request: 案例创建请求

    Returns:
        dict: 创建的案例信息
    """
    case_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    db = get_database()

    try:
        conn = db.get_connection()
        conn.execute(
            """INSERT INTO cases (id, title, description, device_model, fault_type, solution,
               author_id, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (case_id, request.title, request.fault_description, request.equipment_model,
             "", request.repair_result,
             current_user["id"], "pending", now, now),
        )
        conn.commit()

        # 记录日志
        db.save_log(
            user_id=current_user["id"],
            action=f"创建检修案例: {request.title}",
            detail=f"case_id={case_id}",
        )

        return {
            "code": 200,
            "message": "案例创建成功",
            "data": {
                "case_id": case_id,
                "title": request.title,
                "status": "pending",
                "created_at": now,
            }
        }
    except Exception as e:
        logger.error(f"案例创建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")


@router.get("/list", summary="获取案例列表")
async def list_cases(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    equipment_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None, description="状态筛选"),
):
    """
    获取检修案例列表，支持分页和筛选

    Args:
        page: 页码
        page_size: 每页数量
        equipment_type: 设备类型筛选
        status: 状态筛选

    Returns:
        dict: 案例列表
    """
    db = get_database()
    conn = db.get_connection()

    # 构建查询条件
    conditions = []
    params: list = []
    if status:
        conditions.append("status = ?")
        params.append(status)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # 查询总数
    count_result = conn.execute(
        f"SELECT COUNT(*) FROM cases {where_clause}", params
    ).fetchone()
    total = count_result[0]

    # 查询列表
    offset = (page - 1) * page_size
    cursor = conn.execute(
        f"""SELECT id, title, description, device_model, fault_type, solution,
                   status, created_at, updated_at
            FROM cases {where_clause}
            ORDER BY created_at DESC LIMIT ? OFFSET ?""",
        params + [page_size, offset],
    )

    cases = []
    for row in cursor.fetchall():
        cases.append({
            "case_id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "device_model": row["device_model"],
            "fault_type": row["fault_type"],
            "solution": row["solution"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })

    pagination = calculate_pagination(page, page_size, total)

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "cases": cases,
            "pagination": pagination,
        }
    }


@router.get("/{case_id}", summary="获取案例详情")
async def get_case(case_id: str):
    """
    获取指定案例的详细信息

    Args:
        case_id: 案例ID

    Returns:
        dict: 案例详情
    """
    db = get_database()
    conn = db.get_connection()
    cursor = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="案例不存在")

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "case_id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "device_model": row["device_model"],
            "fault_type": row["fault_type"],
            "solution": row["solution"],
            "author_id": row["author_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    }


@router.put("/{case_id}", summary="更新案例")
async def update_case(case_id: str, request: CaseUpdateRequest, current_user: dict = Depends(get_current_user)):
    """
    更新指定案例的信息

    Args:
        case_id: 案例ID
        request: 更新请求

    Returns:
        dict: 更新结果
    """
    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute("SELECT id, author_id FROM cases WHERE id = ?", (case_id,))
    case = cursor.fetchone()
    if not case:
        raise HTTPException(status_code=404, detail="案例不存在")

    if current_user.get("role") != "admin" and case["author_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="无权操作此案例")

    # 构建更新字段
    update_fields = []
    update_values = []

    if request.title is not None:
        update_fields.append("title = ?")
        update_values.append(request.title)
    if request.fault_description is not None:
        update_fields.append("description = ?")
        update_values.append(request.fault_description)
    if request.repair_result is not None:
        update_fields.append("solution = ?")
        update_values.append(request.repair_result)

    if not update_fields:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    update_fields.append("updated_at = ?")
    update_values.append(datetime.now().isoformat())
    update_values.append(case_id)

    sql = f"UPDATE cases SET {', '.join(update_fields)} WHERE id = ?"
    conn.execute(sql, update_values)
    conn.commit()

    # 记录日志
    db.save_log(
        user_id=None,
        action=f"更新检修案例: {case_id}",
        detail=f"fields={', '.join(update_fields)}",
    )

    return {
        "code": 200,
        "message": "更新成功",
        "data": {"case_id": case_id}
    }


@router.delete("/{case_id}", summary="删除案例")
async def delete_case(case_id: str, current_user: dict = Depends(get_current_user)):
    """
    删除指定案例

    Args:
        case_id: 案例ID

    Returns:
        dict: 删除结果
    """
    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute("SELECT id, title, author_id FROM cases WHERE id = ?", (case_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="案例不存在")

    if current_user.get("role") != "admin" and row["author_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="无权操作此案例")

    # 删除案例
    conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    conn.commit()

    # 记录日志
    db.save_log(
        user_id=None,
        action=f"删除检修案例: {row['title']}",
        detail=f"case_id={case_id}",
    )

    return {
        "code": 200,
        "message": "删除成功",
        "data": {"case_id": case_id}
    }


@router.post("/search", summary="检索案例")
async def search_cases(request: CaseSearchRequest):
    """
    基于语义的案例检索，快速找到相似的检修案例

    Args:
        request: 案例检索请求

    Returns:
        dict: 匹配的案例列表
    """
    db = get_database()
    conn = db.get_connection()

    try:
        # 构建查询条件
        conditions = []
        params: list = []

        # 关键词模糊搜索
        conditions.append("(title LIKE ? OR description LIKE ?)")
        like_pattern = f"%{_escape_like(request.query)}%"
        params.extend([like_pattern, like_pattern])

        if request.tags:
            tag_conditions = []
            for tag in request.tags:
                tag_conditions.append("description LIKE ?")
                params.append(f"%{_escape_like(tag)}%")
            if tag_conditions:
                conditions.append(f"({' OR '.join(tag_conditions)})")

        where_clause = "WHERE " + " AND ".join(conditions)

        # 查询总数
        count_result = conn.execute(
            f"SELECT COUNT(*) FROM cases {where_clause}", params
        ).fetchone()
        total = count_result[0]

        # 查询列表
        offset = (request.page - 1) * request.page_size
        cursor = conn.execute(
            f"""SELECT id, title, description, device_model, fault_type, solution,
                       status, created_at
                FROM cases {where_clause}
                ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            params + [request.page_size, offset],
        )

        cases = []
        for row in cursor.fetchall():
            cases.append({
                "case_id": row["id"],
                "title": row["title"],
                "description": row["description"][:200],
                "device_model": row["device_model"],
                "fault_type": row["fault_type"],
                "solution": row["solution"],
                "status": row["status"],
                "created_at": row["created_at"],
            })

        return {
            "code": 200,
            "message": "检索成功",
            "data": {
                "query": request.query,
                "cases": cases,
                "total": total,
            }
        }
    except Exception as e:
        logger.error(f"案例检索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")


@router.post("/review", summary="审核案例")
async def review_case(request: CaseReviewRequest, admin: dict = Depends(require_admin)):
    """
    对案例进行审核操作（通过/拒绝）

    Args:
        request: 审核请求

    Returns:
        dict: 审核结果
    """
    if request.status not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400,
            detail="审核状态无效，可选值: approved / rejected"
        )

    db = get_database()
    conn = db.get_connection()

    # 检查案例是否存在
    cursor = conn.execute("SELECT id, title, status FROM cases WHERE id = ?", (request.case_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="案例不存在")

    if row["status"] != "pending_review":
        raise HTTPException(
            status_code=400,
            detail=f"案例当前状态为 '{row['status']}'，无法审核"
        )

    # 更新审核状态
    now = datetime.now().isoformat()
    conn.execute(
        """UPDATE cases SET status = ?, updated_at = ?
           WHERE id = ?""",
        (request.status, now, request.case_id),
    )
    conn.commit()

    # 记录日志
    status_text = "通过" if request.status == "approved" else "拒绝"
    db.save_log(
        user_id=None,
        action=f"审核案例{status_text}: {row['title']}",
        detail=f"case_id={request.case_id}, status={request.status}, comment={request.review_comment}",
    )

    return {
        "code": 200,
        "message": f"案例已{status_text}",
        "data": {
            "case_id": request.case_id,
            "status": request.status,
            "review_comment": request.review_comment,
        }
    }
