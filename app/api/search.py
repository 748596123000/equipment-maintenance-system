"""
知识检索接口

提供多种检索方式：
- POST /search/text - 文本语义检索
- POST /search/keyword - 关键词检索
- POST /search/hybrid - 混合检索（语义+关键词）
- POST /search/model - 设备型号检索
- POST /search/image - 图片检索（上传图片->描述->检索）
"""

import base64
import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.models.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


class TextSearchRequest(BaseModel):
    """文本检索请求"""
    query: str = Field(..., min_length=1, max_length=1000, description="检索查询文本")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    category: Optional[str] = Field(default=None, description="限定检索分类")
    threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="相似度阈值")


class KeywordSearchRequest(BaseModel):
    """关键词检索请求"""
    keywords: List[str] = Field(..., min_length=1, description="关键词列表")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    match_mode: Literal["any", "all"] = Field(default="any", description="匹配模式: any(任一) / all(全部)")


class ImageSearchRequest(BaseModel):
    """图片检索请求"""
    image_base64: str = Field(..., max_length=10_000_000, description="Base64编码的图片数据")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")


class ModelSearchRequest(BaseModel):
    """设备型号检索请求"""
    model_number: str = Field(..., min_length=1, description="设备型号")
    query: Optional[str] = Field(default=None, description="附加查询条件")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")


class HybridSearchRequest(BaseModel):
    """混合检索请求"""
    query: str = Field(..., min_length=1, description="检索查询文本")
    keywords: Optional[List[str]] = Field(default=None, description="附加关键词")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="语义检索权重")
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="关键词检索权重")


def _format_search_results(results) -> List[dict]:
    """
    格式化检索结果为统一输出格式

    Args:
        results: 检索引擎返回的结果列表

    Returns:
        List[dict]: 统一格式的结果列表
    """
    formatted = []
    for r in results:
        if hasattr(r, "to_dict"):
            data = r.to_dict()
        elif isinstance(r, dict):
            data = r
        else:
            continue

        formatted.append({
            "content": data.get("content", ""),
            "source": data.get("source", "未知来源"),
            "page": data.get("page_number"),
            "score": round(data.get("score", 0.0), 4),
            "metadata": {
                "chunk_id": data.get("chunk_id", ""),
                "category": data.get("category", ""),
                "section_title": data.get("metadata", {}).get("section_title", "") if isinstance(data.get("metadata"), dict) else "",
            }
        })
    return formatted


@router.post("/text", summary="文本语义检索")
async def text_search(request: TextSearchRequest):
    """
    基于语义的文本检索，使用Embedding向量进行相似度匹配

    Args:
        request: 文本检索请求参数

    Returns:
        dict: 检索结果列表，按相似度降序排列
    """
    try:
        from app.core.retriever import get_retriever
        retriever = get_retriever()
        results = retriever.search(
            query=request.query,
            top_k=request.top_k,
        )

        formatted_results = _format_search_results(results)

        # 记录检索日志
        db = get_database()
        db.save_log(
            user_id=None,
            action=f"文本语义检索: {request.query[:50]}",
            detail=f"mode=text, top_k={request.top_k}, results={len(formatted_results)}",
        )

        return {
            "code": 200,
            "message": "检索成功",
            "data": {
                "query": request.query,
                "total": len(formatted_results),
                "results": formatted_results,
            }
        }
    except Exception as e:
        logger.error(f"文本检索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")


@router.post("/keyword", summary="关键词检索")
async def keyword_search(request: KeywordSearchRequest):
    """
    基于关键词的精确检索，支持多关键词组合匹配

    Args:
        request: 关键词检索请求参数

    Returns:
        dict: 检索结果列表
    """
    try:
        from app.core.retriever import get_retriever
        retriever = get_retriever()
        results = retriever.keyword_search(
            keywords=request.keywords,
            top_k=request.top_k,
            match_mode=request.match_mode,
        )

        formatted_results = _format_search_results(results)

        # 记录检索日志
        db = get_database()
        db.save_log(
            user_id=None,
            action=f"关键词检索: {', '.join(request.keywords[:5])}",
            detail=f"mode=keyword, match={request.match_mode}, results={len(formatted_results)}",
        )

        return {
            "code": 200,
            "message": "检索成功",
            "data": {
                "keywords": request.keywords,
                "total": len(formatted_results),
                "results": formatted_results,
            }
        }
    except Exception as e:
        logger.error(f"关键词检索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")


@router.post("/hybrid", summary="混合检索")
async def hybrid_search(request: HybridSearchRequest):
    """
    混合检索模式，结合语义检索和关键词检索的结果，
    通过权重融合排序返回最优结果

    Args:
        request: 混合检索请求参数

    Returns:
        dict: 融合排序后的检索结果
    """
    try:
        from app.core.retriever import get_retriever
        retriever = get_retriever()
        results = retriever.hybrid_search(
            query=request.query,
            keywords=request.keywords,
            top_k=request.top_k,
            semantic_weight=request.semantic_weight,
            keyword_weight=request.keyword_weight,
        )

        formatted_results = _format_search_results(results)

        # 记录检索日志
        db = get_database()
        db.save_log(
            user_id=None,
            action=f"混合检索: {request.query[:50]}",
            detail=f"mode=hybrid, semantic_w={request.semantic_weight}, results={len(formatted_results)}",
        )

        return {
            "code": 200,
            "message": "混合检索成功",
            "data": {
                "query": request.query,
                "total": len(formatted_results),
                "results": formatted_results,
            }
        }
    except Exception as e:
        logger.error(f"混合检索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")


@router.post("/model", summary="设备型号检索")
async def model_search(request: ModelSearchRequest):
    """
    基于设备型号的精确检索，快速定位特定设备的检修资料

    Args:
        request: 设备型号检索请求参数

    Returns:
        dict: 匹配的设备文档和检修信息
    """
    try:
        from app.core.retriever import get_retriever
        retriever = get_retriever()
        results = retriever.model_search(
            model_number=request.model_number,
            query=request.query,
            top_k=request.top_k,
        )

        formatted_results = _format_search_results(results)

        # 记录检索日志
        db = get_database()
        db.save_log(
            user_id=None,
            action=f"设备型号检索: {request.model_number}",
            detail=f"mode=model, query={request.query}, results={len(formatted_results)}",
        )

        return {
            "code": 200,
            "message": "型号检索成功",
            "data": {
                "model_number": request.model_number,
                "total": len(formatted_results),
                "results": formatted_results,
            }
        }
    except Exception as e:
        logger.error(f"型号检索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")


@router.post("/image", summary="图片检索")
async def image_search(request: ImageSearchRequest):
    """
    基于图片的跨模态检索，上传图片后提取特征向量进行相似度匹配

    Args:
        request: 图片检索请求参数

    Returns:
        dict: 匹配的图片和关联文档信息
    """
    try:
        from app.core.image_retriever import ImageRetriever
        image_retriever = ImageRetriever()
        results = image_retriever.search(
            image_base64=request.image_base64,
            top_k=request.top_k,
        )

        # 格式化图片检索结果
        formatted_results = []
        for r in results:
            if hasattr(r, "to_dict"):
                data = r.to_dict()
            elif isinstance(r, dict):
                data = r
            else:
                continue
            formatted_results.append({
                "content": data.get("caption", ""),
                "source": data.get("source_document", "未知来源"),
                "page": data.get("page_number"),
                "score": round(data.get("similarity", 0.0), 4),
                "metadata": {
                    "image_id": data.get("image_id", ""),
                    "image_path": data.get("image_path", ""),
                }
            })

        # 记录检索日志
        db = get_database()
        db.save_log(
            user_id=None,
            action="图片检索",
            detail=f"mode=image, results={len(formatted_results)}",
        )

        return {
            "code": 200,
            "message": "图片检索成功",
            "data": {
                "total": len(formatted_results),
                "results": formatted_results,
            }
        }
    except Exception as e:
        logger.error(f"图片检索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")
