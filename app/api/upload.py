"""
PDF文件上传与审批接口

提供PDF文档的上传、审批和入库功能：
- POST /upload/pdf - 上传PDF文件（状态设为pending，等待审批）
- POST /upload/batch - 批量上传PDF文件
- GET /upload/list - 获取已上传文档列表
- DELETE /upload/{document_id} - 删除指定文档
- GET /upload/pending - 获取待审核文档列表（仅管理员）
- POST /upload/{document_id}/approve - 审批通过（仅管理员），审批后自动触发解析
- POST /upload/{document_id}/reject - 审批拒绝（仅管理员）
- GET /upload/my - 获取当前用户上传的文档列表
"""

import asyncio
import logging
import os
import threading
import uuid
from typing import List
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.api.auth import get_current_user, require_admin
from app.config import settings
from app.models.database import get_database
from app.utils.helpers import format_file_size, calculate_pagination

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


# ========== 请求模型 ==========


class ReviewRequest(BaseModel):
    """审批请求"""
    comment: str = Field(default="", description="审批意见")


# ========== 异步文档处理 ==========


def _process_document(document_id: str, filename: str, file_path: str, category: str):
    """
    处理文档：解析PDF -> 分块 -> 向量化 -> 存入向量库
    此函数在后台线程中执行，避免阻塞事件循环。

    Args:
        document_id: 文档ID
        filename: 文件名
        file_path: 文件路径
        category: 文档分类
    """
    db = get_database()
    try:
        # 更新状态为处理中
        db.update_document(document_id, status="processing")

        # 步骤1: 解析PDF（使用parse_pdf获取完整结构化结果，含图片描述）
        logger.info(f"开始解析文档: {filename} (ID: {document_id})")
        from app.core.pdf_parser import PDFParser
        parser = PDFParser(file_path)
        parse_result = parser.parse_pdf()  # 返回字典，包含图片描述段落
        page_count = parse_result.get("total_pages", 0)

        # 步骤2: 从解析结果中提取所有段落文本（含图片描述），合并后分块
        all_paragraphs = parse_result.get("paragraphs", [])
        full_text_parts = []
        for para in all_paragraphs:
            content = para.get("content", "")
            if content and content.strip():
                full_text_parts.append(content.strip())

        full_text = "\n".join(full_text_parts)
        if not full_text.strip():
            logger.warning(f"文档 {filename} 未提取到文本内容")
            conn = db.get_connection()
            conn.execute(
                "UPDATE documents SET status = 'failed', page_count = ? WHERE id = ?",
                (page_count, document_id),
            )
            conn.commit()
            return

        from app.core.chunker import TextChunker
        chunker = TextChunker()
        chunks = chunker.chunk(full_text, document_id=document_id, strategy="structure")
        chunk_count = len(chunks)

        # 步骤3: 存入ChromaDB（add_documents会自动生成embedding）
        from app.core.retriever import get_retriever
        retriever = get_retriever()
        try:
            retriever.add_documents(
                chunks=chunks,
                document_id=document_id,
                source_name=filename,
                category=category,
            )
            status = "completed"
        except Exception as emb_err:
            logger.warning(f"向量化失败（Embedding服务不可用），文档已解析但暂不可检索: {emb_err}")
            status = "parsed"  # 解析完成但未向量化

        # 步骤4: 更新数据库状态
        conn = db.get_connection()
        conn.execute(
            "UPDATE documents SET status = ?, page_count = ?, chunk_count = ? WHERE id = ?",
            (status, page_count, chunk_count, document_id),
        )
        conn.commit()

        logger.info(f"文档处理完成: {filename}, 状态={status}, 页数={page_count}, 分块数={chunk_count}")

    except Exception as e:
        logger.error(f"文档处理失败: {filename}, 错误: {e}", exc_info=True)
        conn = db.get_connection()
        conn.execute(
            "UPDATE documents SET status = 'failed' WHERE id = ?",
            (document_id,),
        )
        conn.commit()


def _process_document_background(document_id: str, filename: str, file_path: str, category: str):
    """后台线程中处理文档的包装函数，处理失败时更新状态为failed"""
    try:
        _process_document(document_id, filename, file_path, category)
        logger.info(f"文档后台处理完成: {document_id}")
    except Exception as e:
        logger.error(f"文档后台处理失败: {document_id}, 错误: {e}", exc_info=True)
        try:
            db = get_database()
            conn = db.get_connection()
            conn.execute(
                "UPDATE documents SET status = 'failed' WHERE id = ?",
                (document_id,),
            )
            conn.commit()
        except Exception as db_err:
            logger.error(f"更新文档失败状态时出错: {document_id}, 错误: {db_err}")


# ========== 上传接口 ==========


@router.post("/pdf", summary="上传PDF文件")
async def upload_pdf(
    file: UploadFile = File(..., description="PDF文件"),
    category: str = Form(default="通用", description="文档分类"),
    description: str = Form(default="", description="文档描述"),
    current_user: dict = Depends(get_current_user),
):
    """
    上传单个PDF文件，状态设为pending等待管理员审批

    Args:
        file: 上传的PDF文件
        category: 文档分类（如：变压器、开关柜、线路等）
        description: 文档描述信息

    Returns:
        dict: 包含文档ID、文件名、状态等信息
    """
    # 验证文件类型
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持PDF文件格式")

    content = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="文件大小超过限制")
    content = bytes(content)
    file_size = len(content)

    if not content.startswith(b'%PDF'):
        raise HTTPException(status_code=400, detail="文件内容不是有效的PDF格式")

    document_id = str(uuid.uuid4())

    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(settings.UPLOAD_DIR, f"{document_id}_{safe_filename}")
    try:
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"文件已保存: {file_path}")
    except Exception as e:
        logger.error(f"文件保存失败: {e}")
        raise HTTPException(status_code=500, detail="文件保存失败")

    # 记录到数据库（状态为pending，等待审批）
    db = get_database()
    db.save_document(
        document_id=document_id,
        filename=safe_filename,
        filepath=file_path,
        file_size=file_size,
        uploader_id=current_user["id"],
    )

    # 记录上传日志
    db.save_log(
        user_id=current_user["id"],
        action="上传文档",
        detail=f"filename={file.filename}, document_id={document_id}",
    )

    return {
        "code": 200,
        "message": "文件上传成功，等待管理员审批",
        "data": {
            "document_id": document_id,
            "filename": file.filename,
            "category": category,
            "file_size": file_size,
            "file_size_display": format_file_size(file_size),
            "status": "pending",
            "chunk_count": 0,
        }
    }


@router.post("/batch", summary="批量上传PDF文件")
async def batch_upload_pdfs(
    files: List[UploadFile] = File(..., description="多个PDF文件"),
    category: str = Form(default="通用", description="文档分类"),
    current_user: dict = Depends(get_current_user),
):
    """
    批量上传多个PDF文件，状态设为pending等待审批

    Args:
        files: 多个PDF文件
        category: 文档分类

    Returns:
        dict: 包含成功/失败文件列表
    """
    if not files:
        raise HTTPException(status_code=400, detail="请选择至少一个文件上传")

    results = {"success": [], "failed": []}

    for file in files:
        try:
            # 验证文件类型
            if not file.filename.lower().endswith(".pdf"):
                results["failed"].append({
                    "filename": file.filename,
                    "error": "仅支持PDF文件格式"
                })
                continue

            # 读取文件内容
            content = await file.read()
            file_size = len(content)

            # 验证文件大小
            if file_size > settings.MAX_UPLOAD_SIZE:
                results["failed"].append({
                    "filename": file.filename,
                    "error": f"文件大小超过限制（最大 {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB）"
                })
                continue

            if not content.startswith(b'%PDF'):
                results["failed"].append({"filename": file.filename, "error": "文件内容不是有效的PDF格式"})
                continue

            # 生成唯一文档ID
            document_id = str(uuid.uuid4())

            # 保存文件
            safe_filename = os.path.basename(file.filename)
            file_path = os.path.join(settings.UPLOAD_DIR, f"{document_id}_{safe_filename}")
            with open(file_path, "wb") as f:
                f.write(content)

            # 记录到数据库（状态为pending）
            db = get_database()
            db.save_document(
                document_id=document_id,
                filename=file.filename,
                filepath=file_path,
                file_size=file_size,
                uploader_id=current_user["id"],
            )

            results["success"].append({
                "filename": file.filename,
                "document_id": document_id,
                "file_size": file_size,
            })
            logger.info(f"批量上传成功: {file.filename}")

        except Exception as e:
            results["failed"].append({
                "filename": file.filename,
                "error": str(e)
            })
            logger.error(f"批量上传失败 [{file.filename}]: {e}")

    success_count = len(results["success"])
    failed_count = len(results["failed"])

    return {
        "code": 200,
        "message": f"批量上传完成，成功 {success_count} 个，失败 {failed_count} 个，等待管理员审批",
        "data": results
    }


# ========== 文档列表接口 ==========


@router.get("/list", summary="获取文档列表")
async def list_documents(
    category: str = Query(default=None, description="按分类筛选"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
):
    """
    获取已上传的文档列表，支持分页和分类筛选

    Args:
        category: 文档分类筛选条件
        page: 页码
        page_size: 每页数量

    Returns:
        dict: 文档列表和分页信息
    """
    db = get_database()
    result = db.list_documents(page=page, page_size=page_size)

    # 格式化文档列表
    documents = []
    for doc in result["documents"]:
        documents.append({
            "document_id": doc["id"],
            "filename": doc["filename"],
            "file_size": doc.get("file_size", 0),
            "file_size_display": format_file_size(doc.get("file_size", 0)),
            "category": doc.get("category", "通用"),
            "description": doc.get("description", ""),
            "page_count": doc.get("page_count", 0),
            "chunk_count": doc.get("chunk_count", 0),
            "status": doc.get("status", "pending"),
            "uploader_id": doc.get("uploader_id", ""),
            "reviewer_id": doc.get("reviewer_id", ""),
            "review_comment": doc.get("review_comment", ""),
            "reviewed_at": doc.get("reviewed_at", ""),
            "created_at": doc.get("upload_time", ""),
        })

    total = result["total"]
    pagination = calculate_pagination(page, page_size, total)

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "documents": documents,
            "pagination": pagination,
        }
    }


@router.get("/my", summary="获取当前用户上传的文档列表")
async def list_my_documents(
    current_user: dict = Depends(get_current_user),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
):
    """
    获取当前登录用户上传的文档列表

    Args:
        page: 页码
        page_size: 每页数量

    Returns:
        dict: 当前用户的文档列表和分页信息
    """
    db = get_database()
    result = db.list_documents_by_uploader(uploader_id=current_user["id"], page=page, page_size=page_size)

    # 格式化文档列表
    documents = []
    for doc in result["documents"]:
        documents.append({
            "document_id": doc["id"],
            "filename": doc["filename"],
            "file_size": doc.get("file_size", 0),
            "file_size_display": format_file_size(doc.get("file_size", 0)),
            "page_count": doc.get("page_count", 0),
            "chunk_count": doc.get("chunk_count", 0),
            "status": doc.get("status", "pending"),
            "review_comment": doc.get("review_comment", ""),
            "reviewed_at": doc.get("reviewed_at", ""),
            "upload_time": doc.get("upload_time", ""),
        })

    total = result["total"]
    pagination = calculate_pagination(page, page_size, total)

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "documents": documents,
            "pagination": pagination,
        }
    }


# ========== 审批接口（仅管理员） ==========


@router.get("/pending", summary="获取待审核文档列表")
async def list_pending_documents(
    admin: dict = Depends(require_admin),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
):
    """
    获取待审核的文档列表（仅管理员可访问）

    Args:
        page: 页码
        page_size: 每页数量

    Returns:
        dict: 待审核文档列表
    """
    db = get_database()
    result = db.list_documents(page=page, page_size=page_size, status="pending")

    # 格式化文档列表
    documents = []
    for doc in result["documents"]:
        # 获取上传者用户名
        uploader_name = ""
        if doc.get("uploader_id"):
            uploader = db.get_user_by_id(doc["uploader_id"])
            if uploader:
                uploader_name = uploader.get("username", "")

        documents.append({
            "document_id": doc["id"],
            "filename": doc["filename"],
            "file_size": doc.get("file_size", 0),
            "file_size_display": format_file_size(doc.get("file_size", 0)),
            "uploader_id": doc.get("uploader_id", ""),
            "uploader_name": uploader_name,
            "upload_time": doc.get("upload_time", ""),
        })

    total = result["total"]
    pagination = calculate_pagination(page, page_size, total)

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "documents": documents,
            "pagination": pagination,
        }
    }


@router.post("/{document_id}/approve", summary="审批通过文档")
async def approve_document(
    document_id: str,
    request: ReviewRequest,
    admin: dict = Depends(require_admin),
):
    """
    审批通过文档（仅管理员可操作）

    审批通过后自动触发文档解析和向量化处理。

    Args:
        document_id: 文档ID
        request: 审批请求（包含审批意见）

    Returns:
        dict: 审批结果
    """
    db = get_database()

    # 查找文档
    doc = db.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if doc["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"文档当前状态为 '{doc['status']}'，无法审批")

    # 更新审批信息
    db.update_document_review(
        document_id=document_id,
        status="approved",
        reviewer_id=admin["id"],
        review_comment=request.comment,
    )

    # 记录审批日志
    db.save_log(
        user_id=admin["id"],
        action="审批通过文档",
        detail=f"document_id={document_id}, filename={doc['filename']}, comment={request.comment}",
    )

    # 异步触发文档处理（解析 -> 分块 -> 向量化），使用后台线程避免阻塞
    file_path = doc["filepath"]
    filename = doc["filename"]
    if file_path and os.path.exists(file_path):
        # 获取文档分类（默认为"通用"）
        category = "通用"
        thread = threading.Thread(
            target=_process_document_background,
            args=(document_id, filename, file_path, category),
            daemon=True,
        )
        thread.start()

    logger.info(f"文档审批通过: {document_id} ({filename})，已触发后台处理")

    return {
        "code": 200,
        "message": "审批通过，文档已开始后台处理",
        "data": {
            "document_id": document_id,
            "status": "approved",
        }
    }


@router.post("/{document_id}/reject", summary="审批拒绝文档")
async def reject_document(
    document_id: str,
    request: ReviewRequest,
    admin: dict = Depends(require_admin),
):
    """
    审批拒绝文档（仅管理员可操作）

    Args:
        document_id: 文档ID
        request: 审批请求（包含拒绝原因）

    Returns:
        dict: 审批结果
    """
    db = get_database()

    # 查找文档
    doc = db.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if doc["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"文档当前状态为 '{doc['status']}'，无法审批")

    # 更新审批信息
    db.update_document_review(
        document_id=document_id,
        status="rejected",
        reviewer_id=admin["id"],
        review_comment=request.comment,
    )

    # 记录审批日志
    db.save_log(
        user_id=admin["id"],
        action="审批拒绝文档",
        detail=f"document_id={document_id}, filename={doc['filename']}, comment={request.comment}",
    )

    logger.info(f"文档审批拒绝: {document_id} ({filename})")

    return {
        "code": 200,
        "message": "文档已拒绝",
        "data": {
            "document_id": document_id,
            "status": "rejected",
        }
    }


# ========== PDF预览接口 ==========


@router.get("/pdf/{document_id}/preview", summary="预览PDF文档内容")
async def preview_pdf(document_id: str):
    """
    获取PDF文档的文本内容用于预览

    从数据库获取文档信息，读取PDF文件并按页提取文本内容。

    Args:
        document_id: 文档ID

    Returns:
        dict: 包含filename, page_count, uploader_name, content等信息
    """
    db = get_database()

    # 查找文档记录
    doc = db.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    file_path = doc.get("filepath", "")
    filename = doc.get("filename", "")

    # 将相对路径转为绝对路径
    if file_path and not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)

    real_upload_dir = os.path.realpath(settings.UPLOAD_DIR)
    real_file_path = os.path.realpath(file_path)
    if not real_file_path.startswith(real_upload_dir + os.sep) and real_file_path != real_upload_dir:
        raise HTTPException(status_code=403, detail="非法文件路径")

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF文件不存在")

    try:
        # 使用PDFParser按页提取文本
        from app.core.pdf_parser import PDFParser
        parser = PDFParser(file_path)
        pdf_doc = parser.parse()

        page_count = pdf_doc.total_pages
        page_contents = []

        for page in pdf_doc.pages:
            page_text = page.text.strip()
            if page_text:
                page_contents.append(f"第{page.page_number}页\n{page_text}")
            else:
                page_contents.append(f"第{page.page_number}页\n（此页无文本内容）")

        content = "\n---\n".join(page_contents)

        # 获取上传者用户名
        uploader_name = ""
        uploader_id = doc.get("uploader_id", "")
        if uploader_id:
            uploader = db.get_user_by_id(uploader_id)
            if uploader:
                uploader_name = uploader.get("username", uploader_id[:8])

        return {
            "code": 200,
            "message": "获取预览内容成功",
            "data": {
                "filename": filename,
                "page_count": page_count,
                "uploader_name": uploader_name,
                "content": content,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF预览失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF预览失败: {str(e)}")


# ========== PDF原文档在线预览接口 ==========


@router.get("/pdf/{document_id}/view", summary="在线预览PDF原文档")
async def view_pdf(document_id: str, current_user: dict = Depends(get_current_user)):
    """
    获取PDF文件用于在线预览（返回文件二进制流）

    此接口不做权限验证，因为只有已登录用户才能在前端看到预览按钮。
    返回的文件流可直接在浏览器中通过PDF.js或浏览器内置PDF插件渲染。

    Args:
        document_id: 文档ID

    Returns:
        FileResponse: PDF文件的二进制流，content_type为application/pdf
    """
    import traceback
    try:
        db = get_database()

        # 查找文档记录
        doc = db.get_document_by_id(document_id)

        # 详细日志
        logger.info(f"[PDF预览] document_id={document_id}")
        logger.info(f"[PDF预览] doc={doc}")

        if not doc:
            logger.warning(f"[PDF预览] 文档不存在: {document_id}")
            raise HTTPException(status_code=404, detail="文档不存在")

        if doc.get("status") not in ("approved", "completed") and current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="文档未通过审核，无法查看")

        file_path = doc.get("filepath", "")
        filename = doc.get("filename", "document.pdf")

        logger.info(f"[PDF预览] filepath={file_path}, filename={filename}")

        # 将相对路径转为绝对路径
        if file_path and not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
            logger.info(f"[PDF预览] abspath={file_path}")

        real_upload_dir = os.path.realpath(settings.UPLOAD_DIR)
        real_file_path = os.path.realpath(file_path)
        if not real_file_path.startswith(real_upload_dir + os.sep) and real_file_path != real_upload_dir:
            raise HTTPException(status_code=403, detail="非法文件路径")

        if not file_path or not os.path.exists(file_path):
            logger.error(f"[PDF预览] 文件不存在: {file_path}")
            raise HTTPException(status_code=404, detail="PDF文件不存在")

        logger.info(f"[PDF预览] 文件大小: {os.path.getsize(file_path)} bytes")

        # 验证文件是否为PDF
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="该文件不是PDF格式")

        def iter_file():
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk

        # 对中文文件名进行RFC 5987编码
        encoded_filename = quote(filename, safe='')

        return StreamingResponse(
            iter_file(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PDF预览] 异常: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"PDF文件读取失败: {str(e)}")


# ========== 删除接口 ==========


@router.delete("/{document_id}", summary="删除文档")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    删除指定文档及其关联的向量数据

    普通用户只能删除自己上传的文档，管理员可以删除任何文档。

    Args:
        document_id: 文档ID

    Returns:
        dict: 删除结果
    """
    db = get_database()

    # 查找文档记录
    conn = db.get_connection()
    cursor = conn.execute("SELECT filepath, filename, uploader_id FROM documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()

    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 权限检查：普通用户只能删除自己的文档
    if current_user.get("role") != "admin" and doc["uploader_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="无权删除此文档")

    file_path = doc["filepath"]
    filename = doc["filename"]

    # 将相对路径转为绝对路径
    if file_path and not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)

    # 从ChromaDB删除关联向量数据
    try:
        from app.core.retriever import get_retriever
        retriever = get_retriever()
        deleted_count = retriever.delete_by_document_id(document_id)
        logger.info(f"已从向量库删除 {deleted_count} 条记录 (文档: {document_id})")
    except Exception as e:
        logger.error(f"从向量库删除失败: {e}", exc_info=True)

    # 从数据库删除文档记录
    success = db.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=500, detail="文档删除失败")

    # 删除物理文件
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"已删除物理文件: {file_path}")
        except Exception as e:
            logger.error(f"删除物理文件失败: {e}", exc_info=True)

    # 记录操作日志
    db.save_log(
        user_id=current_user["id"],
        action=f"删除文档: {filename}",
        detail=f"document_id={document_id}",
    )

    logger.info(f"文档已删除: {document_id} ({filename})")

    return {
        "code": 200,
        "message": "文档删除成功",
        "data": {"document_id": document_id}
    }
