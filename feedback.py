"""
反馈与标注修正接口

提供AI回答反馈和标注修正功能：
- POST /feedback/submit - 提交反馈（含纠正回答）
- GET /feedback/list - 获取反馈列表
- POST /feedback/{feedback_id}/apply - 将纠正回答回写到向量库
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.auth import get_current_user, require_admin
from app.models.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


class FeedbackSubmitRequest(BaseModel):
    query: str = Field(..., min_length=1, description="用户查询")
    response: str = Field(..., min_length=1, description="AI回答")
    corrected_response: str = Field(default="", description="纠正后的回答")
    source: str = Field(default="chat", description="来源")


class FeedbackApplyRequest(BaseModel):
    document_id: Optional[str] = Field(default=None, description="关联文档ID")
    category: Optional[str] = Field(default=None, description="知识分类")


@router.post("/submit", summary="提交反馈")
async def submit_feedback(request: FeedbackSubmitRequest, current_user: dict = Depends(get_current_user)):
    db = get_database()
    try:
        feedback_id = db.save_feedback(
            query=request.query,
            response=request.response,
            corrected_response=request.corrected_response,
            source=request.source,
        )

        db.save_log(
            user_id=current_user["id"],
            action="提交AI反馈",
            detail=f"feedback_id={feedback_id}, has_correction={bool(request.corrected_response)}",
        )

        return {
            "code": 200,
            "message": "反馈提交成功",
            "data": {"feedback_id": feedback_id},
        }
    except Exception as e:
        logger.error(f"反馈提交失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="操作失败")


@router.get("/list", summary="获取反馈列表")
async def list_feedback(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: dict = Depends(require_admin),
):
    db = get_database()
    try:
        result = db.list_feedback(page=page, page_size=page_size)
        return {
            "code": 200,
            "message": "查询成功",
            "data": result,
        }
    except Exception as e:
        logger.error(f"反馈列表查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.post("/{feedback_id}/apply", summary="将纠正回答回写到向量库")
async def apply_feedback_to_knowledge(
    feedback_id: str,
    request: FeedbackApplyRequest,
    admin: dict = Depends(require_admin),
):
    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="反馈不存在")

    corrected = row["corrected_response"] if "corrected_response" in row.keys() else ""
    if not corrected:
        raise HTTPException(status_code=400, detail="该反馈没有纠正内容，无法回写")

    try:
        from app.core.retriever import get_retriever
        retriever = get_retriever()

        query_text = row["query"] if "query" in row.keys() else ""

        metadata = {
            "source": f"用户纠正 - {query_text[:50]}",
            "feedback_id": feedback_id,
            "type": "corrected_response",
        }
        if request.document_id:
            metadata["document_id"] = request.document_id
        if request.category:
            metadata["category"] = request.category

        doc_id = retriever.add_document(
            content=corrected,
            metadata=metadata,
        )

        conn.execute(
            "UPDATE feedback SET applied = 1 WHERE id = ?",
            (feedback_id,),
        )
        conn.commit()

        db.save_log(
            user_id=admin["id"],
            action="回写纠正内容到向量库",
            detail=f"feedback_id={feedback_id}, doc_id={doc_id}",
        )

        return {
            "code": 200,
            "message": "纠正内容已回写到知识库",
            "data": {
                "feedback_id": feedback_id,
                "document_id": doc_id,
            },
        }
    except Exception as e:
        logger.error(f"回写向量库失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="回写失败，请稍后重试")
