"""
数据初始化模块

在系统首次启动时，自动扫描samples/目录下的文档文件，
将其复制到data/pdfs/并导入知识库（跳过已导入的文件）。
通过data/.data_initialized标记文件避免重复导入。
"""

import datetime
import logging
import os
import shutil
import uuid

logger = logging.getLogger(__name__)

INITIALIZED_FLAG = "data/.data_initialized"
SAMPLE_DIRS = ["samples", os.path.join("data", "pdfs")]
SUPPORTED_EXTENSIONS = {
    "pdf", "docx", "xlsx", "pptx",
    "txt", "md", "csv", "json", "xml", "log",
    "jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp",
}


def init_sample_data():
    """
    初始化示例数据

    扫描samples/和data/pdfs/目录下的文档文件，
    将未导入的文件自动导入知识库。
    通过data/.data_initialized标记文件避免重复导入。
    """
    if os.path.exists(INITIALIZED_FLAG):
        logger.info("示例数据已初始化，跳过")
        return

    doc_files = []
    for scan_dir in SAMPLE_DIRS:
        if os.path.isdir(scan_dir):
            for f in os.listdir(scan_dir):
                ext = f.rsplit(".", 1)[-1].lower() if "." in f else ""
                if ext in SUPPORTED_EXTENSIONS:
                    src = os.path.join(scan_dir, f)
                    if src not in [p[0] for p in doc_files]:
                        doc_files.append((src, f))

    if not doc_files:
        logger.info("未找到文档文件，跳过数据初始化")
        return

    from app.models.database import get_database
    db = get_database()

    admin_user = db.get_user_by_username("admin")
    uploader_id = admin_user["id"] if admin_user else "system"

    upload_dir = os.path.join("data", "pdfs")
    os.makedirs(upload_dir, exist_ok=True)

    imported_count = 0
    for src_path, filename in doc_files:
        existing = db.get_connection().execute(
            "SELECT id FROM documents WHERE filename = ?",
            (filename,),
        ).fetchone()
        if existing:
            logger.info(f"文档已存在，跳过: {filename}")
            continue

        dest_path = os.path.join(upload_dir, filename)
        if not os.path.exists(dest_path):
            shutil.copy2(src_path, dest_path)

        file_size = os.path.getsize(dest_path)
        document_id = str(uuid.uuid4())
        db.get_connection().execute(
            """INSERT INTO documents (id, filename, filepath, file_size, upload_time, status, chunk_count, uploader_id, category)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (document_id, filename, dest_path, file_size,
             datetime.datetime.now().isoformat(),
             "approved", 0, uploader_id, "通用"),
        )
        db.get_connection().commit()
        logger.info(f"已注册文档: {filename} (ID: {document_id})")

        try:
            _process_document_direct(document_id, filename, dest_path, "通用")
            imported_count += 1
        except Exception as e:
            logger.error(f"文档处理失败: {filename}, 错误: {e}")

    if imported_count > 0:
        with open(INITIALIZED_FLAG, "w", encoding="utf-8") as f:
            f.write(datetime.datetime.now().isoformat())
        logger.info(f"示例数据初始化完成，共导入 {imported_count} 个文档")
    else:
        logger.info("无新文档需要导入")


def _process_document_direct(document_id: str, filename: str, file_path: str, category: str):
    """直接处理文档：解析文档 -> 分块 -> 向量化 -> 存入向量库"""
    from app.models.database import get_database
    db = get_database()
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
        status = "parsed"

    conn = db.get_connection()
    conn.execute(
        "UPDATE documents SET status = ?, page_count = ?, chunk_count = ? WHERE id = ?",
        (status, page_count, chunk_count, document_id),
    )
    conn.commit()

    logger.info(f"文档处理完成: {filename}, 状态={status}, 页数={page_count}, 分块数={chunk_count}")
