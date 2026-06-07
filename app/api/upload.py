"""
文档上传与审批接口

支持多格式文档上传、审批和入库：
- POST /upload/file - 上传文档（支持PDF/Word/Excel/PPT/文本/图片等）
- POST /upload/pdf - 上传PDF文件（兼容旧接口）
- POST /upload/batch - 批量上传文档
- GET /upload/list - 获取已上传文档列表
- DELETE /upload/{document_id} - 删除指定文档
- GET /upload/pending - 获取待审核文档列表（仅管理员）
- POST /upload/{document_id}/approve - 审批通过（仅管理员），审批后自动触发解析
- POST /upload/{document_id}/reject - 审批拒绝（仅管理员）
- GET /upload/my - 获取当前用户上传的文档列表
- GET /upload/{document_id}/preview - 预览文档文本内容
- GET /upload/{document_id}/view - 在线预览原文档

通知集成：
- 用户上传文档后自动通知管理员
- 管理员审批后自动通知用户
"""

import logging
import os
import threading
import uuid
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.auth import get_current_user, require_admin
from app.models.database import get_database
from app.config import settings
from app.core.document_parser import (
    SUPPORTED_EXTENSIONS,
    MIME_TYPE_MAP,
    get_file_extension,
    validate_file_type,
)
from app.models.database import get_database
from app.utils.helpers import format_file_size, calculate_pagination

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])
public_router = APIRouter()


async def _authenticate_request(request: Request, token: Optional[str] = None) -> dict:
    from datetime import timezone as _tz
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer as _HB
    _security = _HB(auto_error=False)
    credentials = await _security(request)
    user = None
    if credentials:
        try:
            user = await get_current_user(credentials)
        except HTTPException:
            pass
    if user is None and token:
        db = get_database()
        token_data = db.get_auth_token(token)
        if token_data:
            from datetime import datetime as _dt
            expires_at = _dt.fromisoformat(token_data["expires_at"])
            if _dt.now(_tz.utc) > expires_at:
                db.delete_auth_token(token)
                token_data = None
            else:
                u = db.get_user_by_id(token_data["user_id"])
                if u and u.get("is_active"):
                    user = {k: v for k, v in u.items() if k != "password_hash"}
    if user is None:
        raise HTTPException(status_code=401, detail="未提供认证凭据")
    return user


def safe_path_join(base_dir: str, filename: str) -> str:
    import re
    base = os.path.abspath(os.path.normpath(base_dir))
    requested = os.path.abspath(os.path.normpath(filename))
    if not requested.startswith(base + os.sep) and requested != base:
        raise ValueError("Path traversal detected")
    return requested


def sanitize_filename(filename: str) -> str:
    """
    清理文件名中的特殊字符，兼容Windows文件系统
    """
    import re
    name, ext = os.path.splitext(filename)
    base_name = name.lower()
    
    # 移除Windows不兼容的字符
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # 移除控制字符
    name = re.sub(r'[\x00-\x1f]', '', name)
    # 限制长度
    if len(name) > 100:
        name = name[:100]
    
    # 清理可能的双重扩展名或危险扩展名（检查完整文件名）
    dangerous_extensions = ['.php', '.phtml', '.js', '.jsp', '.asp', '.aspx', '.cgi', '.sh', '.bash', '.exe']
    full_lower = filename.lower()
    for dangerous in dangerous_extensions:
        if dangerous in full_lower:
            # 重命名为.txt
            return name + '.txt'
    
    return name + ext


class ReviewRequest(BaseModel):
    comment: str = Field(default="", description="审批意见")


async def _stream_upload_to_file(file: UploadFile) -> tuple:
    ext = get_file_extension(file.filename)
    if ext not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(f".{e}" for e in SUPPORTED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式 .{ext}，支持格式: {allowed}"
        )

    document_id = str(uuid.uuid4())
    safe_filename = sanitize_filename(os.path.basename(file.filename))
    final_path = os.path.join(settings.UPLOAD_DIR, f"{document_id}_{safe_filename}")
    file_size = 0
    header = bytearray()

    try:
        with open(final_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                file_size += len(chunk)
                if len(header) < 8192:
                    header.extend(chunk[:8192 - len(header)])
                if file_size > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"文件大小超过限制（最大 {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB）"
                    )

        validated_ext = validate_file_type(file.filename, bytes(header))
        if validated_ext is None:
            os.remove(final_path)
            raise HTTPException(status_code=400, detail="文件内容与扩展名不匹配，可能不是有效文件")

    except HTTPException:
        if os.path.exists(final_path):
            os.remove(final_path)
        raise
    except Exception as e:
        if os.path.exists(final_path):
            os.remove(final_path)
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

    return final_path, file_size, ext, document_id, safe_filename


def _process_document(document_id: str, filename: str, file_path: str, category: str):
    db = get_database()
    try:
        db.update_document(document_id, status="processing")

        logger.info(f"开始解析文档: {filename} (ID: {document_id})")
        from app.core.document_parser import parse_document
        parse_result = parse_document(file_path, filename)
        page_count = parse_result.get("total_pages", 0)

        all_paragraphs = parse_result.get("paragraphs", [])
        full_text_parts = []
        for para in all_paragraphs:
            content = para.get("content", "")
            if content and content.strip():
                full_text_parts.append(content.strip())

        full_text = "\n".join(full_text_parts)

        # 文本层为空时（PDF 扫描件），用图片描述段落作为 fallback 内容
        # 否则状态会被设为 failed，导致文档无法预览
        if not full_text.strip():
            image_desc_parts = []
            for para in all_paragraphs:
                meta = para.get("metadata") or {}
                if meta.get("type") == "image":
                    content = (para.get("content") or "").strip()
                    if content:
                        image_desc_parts.append(content)
            if image_desc_parts:
                full_text = "\n\n".join(image_desc_parts)
                logger.info(f"文档 {filename} 文本层为空，使用 {len(image_desc_parts)} 个图片描述段落作为 fallback")

        if not full_text.strip():
            logger.warning(f"文档 {filename} 未提取到文本内容")
            conn = db.get_connection()
            conn.execute(
                "UPDATE documents SET status = 'failed', page_count = ? WHERE id = ?",
                (page_count, document_id),
            )
            conn.commit()
            return

        _save_document_images(db, document_id, parse_result)

        from app.core.chunker import TextChunker
        chunker = TextChunker()
        chunks = chunker.chunk(full_text, document_id=document_id, strategy="structure")
        chunk_count = len(chunks)

        from app.core.retriever import get_retriever
        retriever = get_retriever()
        try:
            from app.services.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()

            chunk_texts = [c.content for c in chunks]
            chunk_ids = [c.chunk_id for c in chunks]
            chunk_metadatas = []
            for c in chunks:
                meta = {
                    "document_id": document_id,
                    "source": filename,
                    "category": category,
                    "page": c.page_number or 0,
                    "chunk_type": c.chunk_type,
                }
                if c.section_title:
                    meta["section_title"] = c.section_title
                chunk_metadatas.append(meta)

            embeddings = embedding_service.embed_texts(chunk_texts)

            retriever.add_documents(
                documents=chunk_texts,
                embeddings=embeddings,
                metadatas=chunk_metadatas,
                ids=chunk_ids,
            )
            status = "completed"
        except Exception as emb_err:
            logger.warning(f"向量化失败（Embedding服务不可用），文档已解析但暂不可检索: {emb_err}")
            status = "parsed"

        conn = db.get_connection()
        conn.execute(
            "UPDATE documents SET status = ?, page_count = ?, chunk_count = ? WHERE id = ?",
            (status, page_count, chunk_count, document_id),
        )
        conn.commit()

        logger.info(f"文档处理完成: {filename}, 状态={status}, 页数={page_count}, 分块数={chunk_count}")

    except Exception as e:
        logger.error(f"文档处理失败: {filename}, 错误: {e}", exc_info=True)
        try:
            conn = db.get_connection()
            conn.execute(
                "UPDATE documents SET status = 'failed' WHERE id = ?",
                (document_id,),
            )
            conn.commit()
        except Exception:
            pass


def _save_document_images(db, document_id: str, parse_result: dict):
    try:
        conn = db.get_connection()
        conn.execute(
            "DELETE FROM document_images WHERE document_id = ?",
            (document_id,),
        )

        paragraphs = parse_result.get("paragraphs", [])
        now = datetime.now().isoformat()
        saved_count = 0

        for para in paragraphs:
            metadata = para.get("metadata", {})
            if not metadata or metadata.get("type") != "image":
                continue

            image_path = metadata.get("image_path", "")
            if not image_path or not os.path.exists(image_path):
                continue

            image_id = str(uuid.uuid4())
            raw_content = para.get("content", "")
            has_desc = metadata.get("has_description", False)
            if has_desc and raw_content.startswith("[图片描述]"):
                description = raw_content.replace("[图片描述] ", "").replace("[图片描述]", "").strip()
            else:
                description = ""

            conn.execute(
                "INSERT INTO document_images (id, document_id, page_number, image_index, image_path, width, height, image_format, ai_description, ai_analyzed, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    image_id,
                    document_id,
                    metadata.get("page", 1),
                    metadata.get("image_index", 0),
                    image_path,
                    0,
                    0,
                    os.path.splitext(image_path)[1].lstrip(".") or "png",
                    description,
                    1 if description else 0,
                    now,
                ),
            )
            saved_count += 1

        if saved_count > 0:
            conn.commit()
            logger.info(f"保存文档图片信息: document_id={document_id}, 图片数={saved_count}")
    except Exception as e:
        logger.error(f"保存文档图片信息失败: {e}", exc_info=True)


def _start_image_description_process(document_id: str):
    try:
        import multiprocessing
        from app.core.image_description_worker import run_image_descriptions

        p = multiprocessing.Process(
            target=run_image_descriptions,
            args=(document_id,),
            daemon=True,
        )
        p.start()
        logger.info(f"已启动独立进程生成图片描述: document_id={document_id}, pid={p.pid}")
    except Exception as mp_err:
        logger.warning(f"独立进程启动失败，回退到线程模式: {mp_err}")
        desc_thread = threading.Thread(
            target=_generate_image_descriptions_background,
            args=(document_id,),
            daemon=True,
        )
        desc_thread.start()


def _process_document_background(document_id: str, filename: str, file_path: str, category: str):
    try:
        _process_document(document_id, filename, file_path, category)
        logger.info(f"文档后台处理完成: {document_id}")

        _start_image_description_process(document_id)
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


def _generate_image_descriptions_background(document_id: str):
    db = get_database()
    conn = db.get_connection()

    rows = conn.execute(
        "SELECT id, image_path, image_format, page_number, image_index FROM document_images WHERE document_id = ? AND ai_analyzed = 0",
        (document_id,),
    ).fetchall()

    if not rows:
        return

    total = len(rows)
    logger.info(f"开始后台生成图片描述: document_id={document_id}, 待处理={total}")

    try:
        from app.services.vision_service import get_vision_service
        vision = get_vision_service()
    except Exception as e:
        logger.warning(f"视觉模型不可用，跳过图片描述生成: {e}")
        return

    for idx, row in enumerate(rows):
        img_id, image_path, image_format, page_number, image_index = row
        try:
            if not image_path or not os.path.exists(image_path):
                continue

            with open(image_path, "rb") as f:
                image_bytes = f.read()

            if not image_bytes or len(image_bytes) < 100:
                continue

            description = vision.describe_image(image_bytes, image_format or "png")

            if description:
                conn.execute(
                    "UPDATE document_images SET ai_description = ?, ai_analyzed = 1 WHERE id = ?",
                    (description, img_id),
                )
                conn.commit()
                logger.info(f"图片描述生成完成: {idx + 1}/{total}, 页{page_number}图{image_index + 1}")
            else:
                logger.debug(f"图片描述为空: 页{page_number}图{image_index + 1}")

        except Exception as e:
            logger.warning(f"图片描述生成失败: 页{page_number}图{image_index + 1}, 错误: {e}")

    logger.info(f"图片描述后台生成完成: document_id={document_id}, 共处理={total}")


def _save_and_register_streamed(file_path: str, file_size: int, ext: str,
                                 document_id: str, safe_filename: str,
                                 category: str, user_id: str, original_filename: str) -> dict:
    db = get_database()
    db.save_document(
        document_id=document_id,
        filename=safe_filename,
        filepath=file_path,
        file_size=file_size,
        uploader_id=user_id,
    )

    db.save_log(
        user_id=user_id,
        action="上传文档",
        detail=f"filename={original_filename}, document_id={document_id}, type={ext}",
    )

    return {
        "document_id": document_id,
        "filename": original_filename,
        "category": category,
        "file_size": file_size,
        "file_size_display": format_file_size(file_size),
        "file_type": ext,
        "status": "pending",
        "chunk_count": 0,
    }


@router.post("/file", summary="上传文档文件")
async def upload_file(
    file: UploadFile = File(..., description="文档文件（支持PDF/Word/Excel/PPT/文本/图片）"),
    category: str = Form(default="通用", description="文档分类"),
    description: str = Form(default="", description="文档描述"),
    current_user: dict = Depends(get_current_user),
):
    file_path, file_size, ext, document_id, safe_filename = await _stream_upload_to_file(file)
    data = _save_and_register_streamed(file_path, file_size, ext, document_id, safe_filename, category, current_user["id"], file.filename)

    uploader_name = current_user.get("username", current_user["id"][:8])
    db = get_database()
    notif_id = f"notif_{uuid.uuid4().hex[:12]}"
    db.save_notification(
        notification_id=notif_id,
        notification_type="upload_pending",
        title="📤 新文档待审批",
        content=f"用户「{uploader_name}」上传了新文档「{file.filename}」，请及时审批。",
        priority="normal",
        related_id=data["document_id"],
        related_type="document",
        target_user_id=None,
        sender_name=uploader_name
    )
    logger.info(f"已发送上传通知给管理员: document_id={data['document_id']}, uploader={uploader_name}")

    return {
        "code": 200,
        "message": "文件上传成功，等待管理员审批",
        "data": data,
    }


@router.post("/pdf", summary="上传PDF文件（兼容旧接口）")
async def upload_pdf(
    file: UploadFile = File(..., description="PDF文件"),
    category: str = Form(default="通用", description="文档分类"),
    description: str = Form(default="", description="文档描述"),
    current_user: dict = Depends(get_current_user),
):
    file_path, file_size, ext, document_id, safe_filename = await _stream_upload_to_file(file)
    data = _save_and_register_streamed(file_path, file_size, ext, document_id, safe_filename, category, current_user["id"], file.filename)

    return {
        "code": 200,
        "message": "文件上传成功，等待管理员审批",
        "data": data,
    }


@router.post("/batch", summary="批量上传文档文件")
async def batch_upload_files(
    files: List[UploadFile] = File(...),
    category: str = Form(default="通用", description="文档分类"),
    current_user: dict = Depends(get_current_user),
):
    # 限制单次批量上传最多10个文件
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="单次批量上传最多10个文件")
    if not files:
        raise HTTPException(status_code=400, detail="请选择至少一个文件上传")

    results = {"success": [], "failed": []}

    for file in files:
        try:
            file_path, file_size, ext, document_id, safe_filename = await _stream_upload_to_file(file)
            data = _save_and_register_streamed(file_path, file_size, ext, document_id, safe_filename, category, current_user["id"], file.filename)
            results["success"].append({
                "filename": file.filename,
                "document_id": data["document_id"],
                "file_size": file_size,
            })
            logger.info(f"批量上传成功: {file.filename}")

        except HTTPException as he:
            results["failed"].append({
                "filename": file.filename,
                "error": he.detail,
            })
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


@router.get("/supported-formats", summary="获取支持的文件格式列表")
async def get_supported_formats():
    format_groups = {
        "PDF文档": [".pdf"],
        "Word文档": [".docx"],
        "Excel表格": [".xlsx"],
        "PPT演示": [".pptx"],
        "文本文件": [".txt", ".md", ".csv", ".json", ".xml", ".log"],
        "图片文件": [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"],
    }
    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "formats": format_groups,
            "max_size_mb": settings.MAX_UPLOAD_SIZE // (1024 * 1024),
        }
    }


@router.get("/list", summary="获取文档列表")
async def list_documents(
    category: str = Query(default=None, description="按分类筛选"),
    status: str = Query(default=None, description="按状态筛选"),
    keyword: str = Query(default=None, description="按文件名搜索"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
):
    db = get_database()
    result = db.list_documents(page=page, page_size=page_size)

    documents = []
    for doc in result["documents"]:
        uploader_name = ""
        uploader_id = doc.get("uploader_id", "")
        if uploader_id:
            uploader = db.get_user_by_id(uploader_id)
            if uploader:
                uploader_name = uploader.get("username", uploader_id[:8])

        filename = doc["filename"]
        file_ext = get_file_extension(filename)

        documents.append({
            "document_id": doc["id"],
            "filename": filename,
            "file_type": file_ext,
            "file_size": doc.get("file_size", 0),
            "file_size_display": format_file_size(doc.get("file_size", 0)),
            "category": doc.get("category", "通用"),
            "description": doc.get("description", ""),
            "page_count": doc.get("page_count", 0),
            "chunk_count": doc.get("chunk_count", 0),
            "status": doc.get("status", "pending"),
            "uploader_id": doc.get("uploader_id", ""),
            "uploader_name": uploader_name,
            "reviewer_id": doc.get("reviewer_id", ""),
            "review_comment": doc.get("review_comment", ""),
            "reviewed_at": doc.get("reviewed_at", ""),
            "created_at": doc.get("upload_time", ""),
        })

    if status:
        documents = [d for d in documents if d["status"] == status]
    if keyword:
        documents = [d for d in documents if keyword.lower() in d["filename"].lower()]
    if category:
        documents = [d for d in documents if d.get("category", "通用") == category]

    total = len(documents) if (status or keyword or category) else result["total"]
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
    db = get_database()
    result = db.list_documents_by_uploader(uploader_id=current_user["id"], page=page, page_size=page_size)

    documents = []
    for doc in result["documents"]:
        filename = doc["filename"]
        file_ext = get_file_extension(filename)
        documents.append({
            "document_id": doc["id"],
            "filename": filename,
            "file_type": file_ext,
            "file_size": doc.get("file_size", 0),
            "file_size_display": format_file_size(doc.get("file_size", 0)),
            "category": doc.get("category", "通用"),
            "page_count": doc.get("page_count", 0),
            "chunk_count": doc.get("chunk_count", 0),
            "status": doc.get("status", "pending"),
            "uploader_name": current_user.get("username", ""),
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


@router.get("/my/stats", summary="获取当前用户上传统计")
async def my_upload_stats(current_user: dict = Depends(get_current_user)):
    db = get_database()
    result = db.list_documents_by_uploader(uploader_id=current_user["id"], page=1, page_size=1000)
    documents = result["documents"]

    stats = {
        "total": len(documents),
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "processing": 0,
        "completed": 0,
        "parsed": 0,
        "failed": 0,
    }
    for doc in documents:
        status = doc.get("status", "")
        if status in stats:
            stats[status] += 1

    return {
        "code": 200,
        "message": "查询成功",
        "data": stats,
    }


@router.get("/pending", summary="获取待审核文档列表")
async def list_pending_documents(
    admin: dict = Depends(require_admin),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
):
    db = get_database()
    result = db.list_documents(page=page, page_size=page_size, status="pending")

    documents = []
    for doc in result["documents"]:
        uploader_name = ""
        if doc.get("uploader_id"):
            uploader = db.get_user_by_id(doc["uploader_id"])
            if uploader:
                uploader_name = uploader.get("username", "")

        documents.append({
            "document_id": doc["id"],
            "filename": doc["filename"],
            "file_type": get_file_extension(doc["filename"]),
            "file_size": doc.get("file_size", 0),
            "file_size_display": format_file_size(doc.get("file_size", 0)),
            "category": doc.get("category", "通用"),
            "page_count": doc.get("page_count", 0),
            "chunk_count": doc.get("chunk_count", 0),
            "status": doc.get("status", "pending"),
            "uploader_id": doc.get("uploader_id", ""),
            "uploader_name": uploader_name,
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


@router.post("/{document_id}/approve", summary="审批通过文档")
async def approve_document(
    document_id: str,
    request: ReviewRequest,
    admin: dict = Depends(require_admin),
):
    db = get_database()

    doc = db.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if doc["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"文档当前状态为 '{doc['status']}'，无法审批")

    db.update_document_review(
        document_id=document_id,
        status="approved",
        reviewer_id=admin["id"],
        review_comment=request.comment,
    )

    db.save_log(
        user_id=admin["id"],
        action="审批通过文档",
        detail=f"document_id={document_id}, filename={doc['filename']}, comment={request.comment}",
    )

    file_path = doc["filepath"]
    filename = doc["filename"]
    if file_path and os.path.exists(file_path):
        category = "通用"
        thread = threading.Thread(
            target=_process_document_background,
            args=(document_id, filename, file_path, category),
            daemon=True,
        )
        thread.start()

    admin_name = admin.get("username", "管理员")
    notif_id = f"notif_{uuid.uuid4().hex[:12]}"
    db.save_notification(
        notification_id=notif_id,
        notification_type="upload_approved",
        title="✅ 文档审批通过",
        content=f"您上传的文档「{filename}」已通过「{admin_name}」的审批。",
        priority="normal",
        related_id=document_id,
        related_type="document",
        target_user_id=doc["uploader_id"],
        sender_name=admin_name
    )
    logger.info(f"已发送审批通过通知: document_id={document_id}, uploader={doc['uploader_id']}, admin={admin_name}")

    return {
        "code": 200,
        "message": "审批通过，文档已开始后台处理",
        "data": {
            "document_id": document_id,
            "status": "approved",
        }
    }


@router.post("/{document_id}/process", summary="处理文档为知识")
async def process_document_to_knowledge(
    document_id: str,
    admin: dict = Depends(require_admin),
):
    db = get_database()

    doc = db.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if doc["status"] not in ("approved", "completed", "parsed", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"文档当前状态为 '{doc['status']}'，仅已审核/已完成/已解析/失败的文档可重新处理"
        )

    file_path = doc["filepath"]
    filename = doc["filename"]
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="文档文件不存在，无法处理")

    category = doc.get("category", "通用")

    conn = db.get_connection()
    conn.execute(
        "UPDATE documents SET status = 'processing' WHERE id = ?",
        (document_id,),
    )
    conn.commit()

    thread = threading.Thread(
        target=_process_document_background,
        args=(document_id, filename, file_path, category),
        daemon=True,
    )
    thread.start()

    db.save_log(
        user_id=admin["id"],
        action="重新处理文档为知识",
        detail=f"document_id={document_id}, filename={filename}",
    )

    logger.info(f"文档重新处理: {document_id} ({filename})，已触发后台处理")

    return {
        "code": 200,
        "message": "文档已开始处理为知识",
        "data": {
            "document_id": document_id,
            "status": "processing",
        }
    }


@router.post("/{document_id}/complete", summary="标记文档为已完成")
async def complete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()

    doc = db.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if doc["status"] == "completed":
        raise HTTPException(status_code=400, detail="文档已标记为已完成")

    if doc["status"] not in ("approved", "parsed", "processing", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"文档当前状态为 '{doc['status']}'，仅已审核/已解析/处理中/失败的文档可标记为已完成"
        )

    db.update_document(document_id, status="completed")

    db.save_log(
        user_id=current_user["id"],
        action="标记文档为已完成",
        detail=f"document_id={document_id}, filename={doc['filename']}",
    )

    logger.info(f"文档标记为已完成: {document_id} ({doc['filename']})")

    return {
        "code": 200,
        "message": "文档已标记为已完成",
        "data": {
            "document_id": document_id,
            "status": "completed",
        }
    }


@router.post("/{document_id}/generate-descriptions", summary="生成文档图片AI描述")
async def generate_image_descriptions(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    doc = db.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    conn = db.get_connection()
    unanalyzed = conn.execute(
        "SELECT COUNT(*) FROM document_images WHERE document_id = ? AND ai_analyzed = 0",
        (document_id,),
    ).fetchone()[0]

    if unanalyzed == 0:
        return {"code": 200, "message": "所有图片已有AI描述", "data": {"pending": 0}}

    _start_image_description_process(document_id)

    return {
        "code": 200,
        "message": f"已开始生成 {unanalyzed} 张图片的AI描述",
        "data": {"pending": unanalyzed},
    }


@router.get("/{document_id}/description-progress", summary="查询图片描述生成进度")
async def get_description_progress(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    conn = db.get_connection()

    total = conn.execute(
        "SELECT COUNT(*) FROM document_images WHERE document_id = ?",
        (document_id,),
    ).fetchone()[0]

    analyzed = conn.execute(
        "SELECT COUNT(*) FROM document_images WHERE document_id = ? AND ai_analyzed = 1",
        (document_id,),
    ).fetchone()[0]

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "total": total,
            "analyzed": analyzed,
            "pending": total - analyzed,
            "progress": round(analyzed / total * 100, 1) if total > 0 else 100,
        },
    }


@router.post("/{document_id}/reject", summary="审批拒绝文档")
async def reject_document(
    document_id: str,
    request: ReviewRequest,
    admin: dict = Depends(require_admin),
):
    db = get_database()

    doc = db.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if doc["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"文档当前状态为 '{doc['status']}'，无法审批")

    db.update_document_review(
        document_id=document_id,
        status="rejected",
        reviewer_id=admin["id"],
        review_comment=request.comment,
    )

    db.save_log(
        user_id=admin["id"],
        action="审批拒绝文档",
        detail=f"document_id={document_id}, filename={doc['filename']}, comment={request.comment}",
    )

    admin_name = admin.get("username", "管理员")
    reason = request.comment or "不符合要求"
    notif_id = f"notif_{uuid.uuid4().hex[:12]}"
    db.save_notification(
        notification_id=notif_id,
        notification_type="upload_rejected",
        title="❌ 文档审批未通过",
        content=f"您上传的文档「{doc['filename']}」未通过审批。原因：{reason}",
        priority="high",
        related_id=document_id,
        related_type="document",
        target_user_id=doc["uploader_id"],
        sender_name=admin_name
    )
    logger.info(f"已发送审批拒绝通知: document_id={document_id}, uploader={doc['uploader_id']}, admin={admin_name}")

    return {
        "code": 200,
        "message": "文档已拒绝",
        "data": {
            "document_id": document_id,
            "status": "rejected",
        }
    }


@router.get("/{document_id}/preview", summary="预览文档文本内容")
async def preview_document(document_id: str):
    db = get_database()

    doc = db.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    file_path = doc.get("filepath", "")
    filename = doc.get("filename", "")
    doc_status = doc.get("status", "")
    chunk_count = doc.get("chunk_count", 0)

    if file_path and not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)

    try:
        validated_path = safe_path_join(settings.UPLOAD_DIR, file_path)
    except ValueError:
        raise HTTPException(status_code=403, detail="非法文件路径")

    if not file_path or not os.path.exists(validated_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        content = None
        page_count = 0

        if doc_status in ("approved", "completed", "parsed") and chunk_count > 0:
            try:
                from app.core.retriever import get_retriever
                retriever = get_retriever()
                if retriever and retriever._collection is not None:
                    results = retriever._collection.get(
                        where={"document_id": document_id},
                        include=["documents", "metadatas"]
                    )
                    if results and results.get("ids"):
                        chunks = []
                        for i, chunk_text in enumerate(results.get("documents", [])):
                            meta = results.get("metadatas", [{}])[i] if i < len(results.get("metadatas", [])) else {}
                            page = meta.get("page", i + 1)
                            chunks.append({"page": page, "content": chunk_text})
                        chunks.sort(key=lambda x: x["page"])
                        page_map = {}
                        for c in chunks:
                            p = c["page"]
                            if p not in page_map:
                                page_map[p] = []
                            page_map[p].append(c["content"])
                        page_contents = []
                        for p in sorted(page_map.keys()):
                            page_contents.append(f"第{p}页\n" + "\n".join(page_map[p]))
                        if page_contents:
                            content = "\n---\n".join(page_contents)
                            page_count = max(page_map.keys()) if page_map else 0
            except Exception as e:
                logger.warning(f"从ChromaDB读取预览内容失败，回退到实时解析: {e}")

        if content is None:
            from app.core.document_parser import parse_document
            parse_result = parse_document(validated_path, filename)
            page_count = parse_result.get("total_pages", 0)

            all_paragraphs = parse_result.get("paragraphs", [])
            page_contents = []
            current_page = 0
            page_text_parts = []

            for para in all_paragraphs:
                page = para.get("page", 1)
                if page != current_page:
                    if page_text_parts:
                        page_contents.append(f"第{current_page}页\n" + "\n".join(page_text_parts))
                    current_page = page
                    page_text_parts = []

                pcontent = para.get("content", "")
                if pcontent and pcontent.strip():
                    page_text_parts.append(pcontent.strip())

            if page_text_parts:
                page_contents.append(f"第{current_page}页\n" + "\n".join(page_text_parts))

            if not page_contents:
                page_contents.append("（文档无文本内容）")

            content = "\n---\n".join(page_contents)

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
        logger.error(f"文档预览失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="文档预览失败，请稍后重试")


@router.get("/pdf/{document_id}/preview", summary="预览PDF文档内容（兼容旧接口）")
async def preview_pdf(document_id: str):
    return await preview_document(document_id)


@public_router.get("/{document_id}/view", summary="在线预览原文档")
async def view_document(document_id: str):
    import traceback
    try:
        db = get_database()

        doc = db.get_document_by_id(document_id)

        logger.info(f"[文档预览] document_id={document_id}")

        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        file_path = doc.get("filepath", "")
        filename = doc.get("filename", "document")

        if file_path and not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)

        real_upload_dir = os.path.realpath(settings.UPLOAD_DIR)
        real_file_path = os.path.realpath(file_path)
        if not real_file_path.startswith(real_upload_dir + os.sep) and real_file_path != real_upload_dir:
            raise HTTPException(status_code=403, detail="非法文件路径")

        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        ext = get_file_extension(filename)
        mime_type = MIME_TYPE_MAP.get(ext, "application/octet-stream")

        if ext in ("jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp"):
            content_disposition = f"inline; filename*=UTF-8''{quote(filename, safe='')}"
        else:
            content_disposition = f"inline; filename*=UTF-8''{quote(filename, safe='')}"

        def iter_file():
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk

        encoded_filename = quote(filename, safe='')

        return StreamingResponse(
            iter_file(),
            media_type=mime_type,
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
        logger.error(f"[文档预览] 异常: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="文件读取失败，请稍后重试")


@public_router.get("/pdf/{document_id}/view", summary="在线预览PDF原文档（兼容旧接口）")
async def view_pdf(document_id: str):
    return await view_document(document_id)


@public_router.get("/{document_id}/download", summary="下载文档原文件")
async def download_document(document_id: str):
    """
    下载文档原文件

    Args:
        document_id: 文档ID

    Returns:
        StreamingResponse: 文件流，用于触发下载
    """
    import traceback
    try:
        db = get_database()
        doc = db.get_document_by_id(document_id)

        logger.info(f"[文档下载] document_id={document_id}")

        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        file_path = doc.get("filepath", "")
        filename = doc.get("filename", "document")

        if file_path and not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)

        real_upload_dir = os.path.realpath(settings.UPLOAD_DIR)
        real_file_path = os.path.realpath(file_path)
        if not real_file_path.startswith(real_upload_dir + os.sep) and real_file_path != real_upload_dir:
            raise HTTPException(status_code=403, detail="非法文件路径")

        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        ext = get_file_extension(filename)
        mime_type = MIME_TYPE_MAP.get(ext, "application/octet-stream")

        def iter_file():
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk

        encoded_filename = quote(filename, safe='')

        return StreamingResponse(
            iter_file(),
            media_type=mime_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[文档下载] 异常: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="文件下载失败，请稍后重试")


@router.delete("/{document_id}", summary="删除文档")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()

    conn = db.get_connection()
    cursor = conn.execute("SELECT filepath, filename, uploader_id FROM documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()

    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if current_user.get("role") != "admin" and doc["uploader_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="无权删除此文档")

    file_path = doc["filepath"]
    filename = doc["filename"]

    if file_path and not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)

    try:
        from app.core.retriever import get_retriever
        retriever = get_retriever()
        deleted_count = retriever.delete_by_document_id(document_id)
        logger.info(f"已从向量库删除 {deleted_count} 条记录 (文档: {document_id})")
    except Exception as e:
        logger.error(f"从向量库删除失败: {e}", exc_info=True)

    success = db.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=500, detail="文档删除失败")

    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"已删除物理文件: {file_path}")
        except Exception as e:
            logger.error(f"删除物理文件失败: {e}", exc_info=True)

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


@public_router.get("/images/{image_id}/file", summary="获取图片文件")
async def get_image_file(image_id: str):
    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute(
        "SELECT image_path, image_format FROM document_images WHERE id = ?",
        (image_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="图片不存在")

    image_path = row["image_path"]
    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="图片文件不存在")

    # 安全验证：确保图片路径在允许的目录内
    try:
        real_upload_dir = os.path.realpath(settings.IMAGE_DIR)
        real_image_path = os.path.realpath(image_path)
        if not real_image_path.startswith(real_upload_dir + os.sep):
            raise HTTPException(status_code=403, detail="非法文件路径")
    except Exception:
        raise HTTPException(status_code=403, detail="非法文件路径")

    ext = row["image_format"] or "png"
    mime_map = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "bmp": "image/bmp",
        "gif": "image/gif", "tiff": "image/tiff",
        "webp": "image/webp",
    }
    mime_type = mime_map.get(ext, "image/png")

    from fastapi.responses import FileResponse
    return FileResponse(
        image_path,
        media_type=mime_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/images/{image_id}/analyze", summary="重新用视觉AI分析图片")
async def analyze_image(image_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute(
        "SELECT id, document_id, image_path, image_format FROM document_images WHERE id = ?",
        (image_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="图片不存在")

    image_path = row["image_path"]
    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="图片文件不存在")

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    ext = row["image_format"] or "png"

    from app.services.vision_service import get_vision_service
    vision = get_vision_service()
    description = vision.describe_image(
        image_bytes,
        ext,
        prompt="请详细描述这张设备检修相关图片的内容，包括：1.设备名称和型号 2.部件和组件 3.操作步骤或故障现象 4.技术参数或标注信息",
    )

    if not description:
        raise HTTPException(status_code=503, detail="视觉AI服务不可用，无法分析图片")

    conn.execute(
        "UPDATE document_images SET ai_description = ?, ai_analyzed = 1 WHERE id = ?",
        (description, image_id),
    )
    conn.commit()

    return {
        "code": 200,
        "message": "图片分析完成",
        "data": {
            "image_id": image_id,
            "ai_description": description,
        }
    }


@router.get("/{document_id}/images", summary="获取文档中的图片列表及AI分析")
async def get_document_images(document_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute("SELECT id FROM documents WHERE id = ?", (document_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="文档不存在")

    cursor = conn.execute(
        "SELECT id, page_number, image_index, image_path, width, height, image_format, ai_description, ai_analyzed FROM document_images WHERE document_id = ? ORDER BY page_number, image_index",
        (document_id,),
    )
    images = []
    for row in cursor.fetchall():
        images.append({
            "id": row["id"],
            "page_number": row["page_number"],
            "image_index": row["image_index"],
            "image_url": f"/api/v1/upload/images/{row['id']}/file",
            "width": row["width"],
            "height": row["height"],
            "image_format": row["image_format"],
            "ai_description": row["ai_description"],
            "ai_analyzed": bool(row["ai_analyzed"]),
        })

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "document_id": document_id,
            "images": images,
            "total": len(images),
        }
    }


@router.post("/{document_id}/backfill-images", summary="回填文档图片信息（为已处理的文档补充图片数据）")
async def backfill_document_images(document_id: str, admin: dict = Depends(require_admin)):
    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute("SELECT id, filename, filepath, status FROM documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    file_path = doc["filepath"]
    filename = doc["filename"]
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文档文件不存在")

    existing = conn.execute(
        "SELECT COUNT(*) as cnt FROM document_images WHERE document_id = ?",
        (document_id,),
    ).fetchone()
    if existing["cnt"] > 0:
        return {
            "code": 200,
            "message": f"文档已有 {existing['cnt']} 张图片记录，无需回填",
            "data": {"document_id": document_id, "images_count": existing["cnt"]},
        }

    from app.core.document_parser import parse_document
    parse_result = parse_document(file_path, filename)
    _save_document_images(db, document_id, parse_result)

    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM document_images WHERE document_id = ?",
        (document_id,),
    ).fetchone()["cnt"]

    return {
        "code": 200,
        "message": f"图片信息回填完成，共 {count} 张图片",
        "data": {"document_id": document_id, "images_count": count},
    }
