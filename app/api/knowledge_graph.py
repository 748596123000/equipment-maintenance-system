import json
import logging
import os
import threading
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.api.auth import get_current_user, require_admin
from app.config import settings
from app.models.database import get_database
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])

VALID_NODE_TYPES = {"device", "fault", "solution", "person", "procedure", "standard"}
VALID_RELATION_TYPES = {"has_fault", "solved_by", "related_to", "requires", "complies_with"}

_extraction_progress: dict = {}
_extraction_lock = threading.Lock()


def _save_task_to_db(task_id: str, data: dict):
    try:
        db = get_database()
        conn = db.get_connection()
        now = datetime.now().isoformat()
        existing = conn.execute("SELECT task_id FROM extraction_tasks WHERE task_id = ?", (task_id,)).fetchone()
        if existing:
            conn.execute(
                """UPDATE extraction_tasks
                   SET status=?, source=?, total=?, current=?, progress=?,
                       success_count=?, fail_count=?, results=?, error=?, updated_at=?
                   WHERE task_id=?""",
                (
                    data.get("status", "pending"),
                    data.get("source", ""),
                    data.get("total", 0),
                    data.get("current", 0),
                    data.get("progress", 0),
                    data.get("success_count", 0),
                    data.get("fail_count", 0),
                    json.dumps(data.get("results", []), ensure_ascii=False),
                    data.get("error", ""),
                    now,
                    task_id,
                ),
            )
        else:
            conn.execute(
                """INSERT INTO extraction_tasks
                   (task_id, status, source, total, current, progress,
                    success_count, fail_count, results, error, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task_id,
                    data.get("status", "pending"),
                    data.get("source", ""),
                    data.get("total", 0),
                    data.get("current", 0),
                    data.get("progress", 0),
                    data.get("success_count", 0),
                    data.get("fail_count", 0),
                    json.dumps(data.get("results", []), ensure_ascii=False),
                    data.get("error", ""),
                    now,
                    now,
                ),
            )
        conn.commit()
    except Exception as e:
        logger.warning(f"保存抽取任务进度到数据库失败: {e}")


def _load_task_from_db(task_id: str) -> Optional[dict]:
    try:
        db = get_database()
        conn = db.get_connection()
        row = conn.execute("SELECT * FROM extraction_tasks WHERE task_id = ?", (task_id,)).fetchone()
        if not row:
            return None
        r = dict(row)
        results = []
        try:
            results = json.loads(r.get("results", "[]"))
        except json.JSONDecodeError:
            pass
        return {
            "status": r["status"],
            "source": r.get("source", ""),
            "total": r.get("total", 0),
            "current": r.get("current", 0),
            "progress": r.get("progress", 0),
            "success_count": r.get("success_count", 0),
            "fail_count": r.get("fail_count", 0),
            "results": results,
            "error": r.get("error", ""),
        }
    except Exception as e:
        logger.warning(f"从数据库加载抽取任务进度失败: {e}")
        return None


def _generate_node_id(name: str, node_type: str) -> str:
    import hashlib
    raw = f"{node_type}:{name}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def _extract_entities_from_case(case: dict) -> dict:
    llm = get_llm_service()
    if not llm.is_available():
        raise HTTPException(status_code=503, detail="LLM服务不可用，请检查Ollama服务是否启动或API Key是否配置")

    case_content = f"标题：{case.get('title', '')}\n"
    case_content += f"描述：{case.get('description', '')}\n"
    case_content += f"设备型号：{case.get('device_model', '')}\n"
    case_content += f"故障类型：{case.get('fault_type', '')}\n"
    case_content += f"解决方案：{case.get('solution', '')}\n"
    if case.get("fault_analysis"):
        case_content += f"故障分析：{case['fault_analysis']}\n"
    if case.get("repair_process"):
        case_content += f"维修过程：{case['repair_process']}\n"
    if case.get("lessons_learned"):
        case_content += f"经验教训：{case['lessons_learned']}\n"

    prompt = f"""请从以下检修案例中抽取实体和关系，以JSON格式输出：

实体类型：device（设备）、fault（故障）、solution（解决方案）
关系类型：has_fault（设备出现故障）、solved_by（故障被解决方案修复）

案例：{case_content}

输出格式：
{{
  "nodes": [{{"name": "xxx", "type": "device"}}, ...],
  "edges": [{{"source": "xxx", "target": "xxx", "relation": "has_fault"}}, ...]
}}"""

    messages = [{"role": "user", "content": prompt}]
    try:
        result = llm.generate_json(messages, temperature=0.3)
        if not isinstance(result, dict):
            result = {"nodes": [], "edges": []}
        if "nodes" not in result:
            result["nodes"] = []
        if "edges" not in result:
            result["edges"] = []
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"LLM返回JSON解析失败: {e}")
        raise HTTPException(status_code=500, detail=f"LLM返回格式异常，请尝试使用更强大的模型（如qwen2.5:7b）: {str(e)}")
    except Exception as e:
        error_msg = str(e)
        if "Connection" in error_msg or "connect" in error_msg.lower() or "refused" in error_msg.lower():
            raise HTTPException(status_code=503, detail="LLM服务连接失败，请检查Ollama服务是否正在运行")
        logger.error(f"LLM实体抽取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"实体抽取失败: {error_msg}")


def _save_extracted_data(extracted: dict, source_id: str, source_type: str = "case") -> dict:
    db = get_database()
    conn = db.get_connection()
    now = datetime.now().isoformat()

    nodes_saved = 0
    edges_saved = 0

    node_name_to_id = {}

    source_key = f"{source_type}_ids" if source_type != "case" else "case_ids"

    for node in extracted.get("nodes", []):
        name = node.get("name", "").strip()
        node_type = node.get("type", "").strip()
        if not name or not node_type:
            continue
        if node_type not in VALID_NODE_TYPES:
            continue

        node_id = _generate_node_id(name, node_type)
        node_name_to_id[name] = node_id

        existing = conn.execute(
            "SELECT id, properties FROM knowledge_graph_nodes WHERE id = ?",
            (node_id,),
        ).fetchone()

        if existing:
            try:
                existing_props = json.loads(existing["properties"]) if existing["properties"] else {}
            except json.JSONDecodeError:
                existing_props = {}
            ids_list = existing_props.get(source_key, [])
            if source_id not in ids_list:
                ids_list.append(source_id)
            existing_props[source_key] = ids_list
            conn.execute(
                "UPDATE knowledge_graph_nodes SET properties = ? WHERE id = ?",
                (json.dumps(existing_props, ensure_ascii=False), node_id),
            )
        else:
            props = {source_key: [source_id]}
            conn.execute(
                "INSERT INTO knowledge_graph_nodes (id, name, type, properties, created_at) VALUES (?, ?, ?, ?, ?)",
                (node_id, name, node_type, json.dumps(props, ensure_ascii=False), now),
            )
            nodes_saved += 1

    for edge in extracted.get("edges", []):
        source_name = edge.get("source", "").strip()
        target_name = edge.get("target", "").strip()
        relation = edge.get("relation", "").strip()
        if not source_name or not target_name or not relation:
            continue
        if relation not in VALID_RELATION_TYPES:
            continue

        source_id_node = node_name_to_id.get(source_name)
        target_id_node = node_name_to_id.get(target_name)
        if not source_id_node or not target_id_node:
            continue

        existing_edge = conn.execute(
            "SELECT id, weight FROM knowledge_graph_edges WHERE source_id = ? AND target_id = ? AND relation = ?",
            (source_id_node, target_id_node, relation),
        ).fetchone()

        if existing_edge:
            new_weight = existing_edge["weight"] + 1.0
            conn.execute(
                "UPDATE knowledge_graph_edges SET weight = ? WHERE id = ?",
                (new_weight, existing_edge["id"]),
            )
        else:
            edge_id = str(uuid.uuid4())
            edge_props = json.dumps({source_key: [source_id]}, ensure_ascii=False)
            conn.execute(
                "INSERT INTO knowledge_graph_edges (id, source_id, target_id, relation, weight, properties, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (edge_id, source_id_node, target_id_node, relation, 1.0, edge_props, now),
            )
            edges_saved += 1

    conn.commit()
    return {"nodes_saved": nodes_saved, "edges_saved": edges_saved}


def _extract_entities_from_document(doc: dict, text_content: str) -> dict:
    llm = get_llm_service()
    if not llm.is_available():
        raise HTTPException(status_code=503, detail="LLM服务不可用，请检查Ollama服务是否启动或API Key是否配置")

    CHUNK_SIZE = 4000
    MAX_CHUNKS = 3
    text_chunks = []
    for i in range(0, len(text_content), CHUNK_SIZE):
        text_chunks.append(text_content[i:i + CHUNK_SIZE])
        if len(text_chunks) >= MAX_CHUNKS:
            break

    all_nodes = []
    all_edges = []
    last_error = None

    for idx, chunk_text in enumerate(text_chunks):
        doc_content = f"文档名称：{doc.get('filename', '')}\n"
        doc_content += f"文档分类：{doc.get('category', '通用')}\n"
        if len(text_chunks) > 1:
            doc_content += f"（第{idx + 1}/{len(text_chunks)}段）\n"
        doc_content += f"文档内容：\n{chunk_text}\n"

        prompt = f"""请从以下设备检修相关文档中抽取实体和关系，以JSON格式输出：

实体类型：
- device（设备/部件）
- fault（故障/异常）
- solution（解决方案/维修方法）
- procedure（操作步骤/检修流程）
- standard（标准/规范/要求）

关系类型：
- has_fault（设备出现故障）
- solved_by（故障被解决方案修复）
- requires（操作需要特定设备或条件）
- related_to（相关关联）
- complies_with（符合某标准/规范）

文档内容：
{doc_content}

输出格式：
{{
  "nodes": [{{"name": "xxx", "type": "device"}}, ...],
  "edges": [{{"source": "xxx", "target": "xxx", "relation": "has_fault"}}, ...]
}}

注意：
1. 实体名称要具体明确，如"10kV开关柜"而非"设备"
2. 关系中的source和target必须与nodes中的name对应
3. 只抽取最重要的实体和关系，不超过15个实体和15个关系"""

        messages = [{"role": "user", "content": prompt}]
        try:
            result = llm.generate_json(messages, temperature=0.3)
            if not isinstance(result, dict):
                continue
            nodes = result.get("nodes", [])
            edges = result.get("edges", [])
            all_nodes.extend(nodes)
            all_edges.extend(edges)
        except ValueError as e:
            last_error = f"JSON解析失败: {e}"
            logger.warning(f"文档第{idx + 1}段实体抽取JSON解析失败: {e}")
            continue
        except Exception as e:
            error_msg = str(e)
            if "Connection" in error_msg or "connect" in error_msg.lower() or "refused" in error_msg.lower():
                raise HTTPException(status_code=503, detail="LLM服务连接失败，请检查Ollama服务是否正在运行")
            last_error = error_msg
            logger.warning(f"文档第{idx + 1}段实体抽取失败: {e}")
            continue

    if not all_nodes and not all_edges and last_error:
        raise HTTPException(status_code=500, detail=f"实体抽取失败: {last_error}。请检查LLM模型是否支持JSON输出（推荐使用qwen2.5:7b或更大模型）")

    seen_names = set()
    unique_nodes = []
    for n in all_nodes:
        name = n.get("name", "").strip()
        ntype = n.get("type", "").strip()
        key = (name, ntype)
        if name and ntype and key not in seen_names:
            seen_names.add(key)
            unique_nodes.append(n)

    return {"nodes": unique_nodes, "edges": all_edges}


def _get_document_text(doc: dict) -> str:
    doc_id = doc.get("id", "")
    file_path = doc.get("filepath", "")
    filename = doc.get("filename", "")

    if doc_id:
        try:
            from app.core.retriever import get_retriever
            retriever = get_retriever()
            retriever._ensure_collection()
            if retriever._collection is not None:
                results = retriever._collection.get(
                    where={"document_id": doc_id},
                    include=["documents"],
                )
                documents = results.get("documents", [])
                if documents:
                    logger.info(f"从ChromaDB缓存获取文档文本: {filename}, 分块数={len(documents)}")
                    return "\n".join(documents)
                else:
                    logger.info(f"ChromaDB中未找到文档 {filename} (id={doc_id}) 的分块数据")
        except Exception as e:
            logger.warning(f"从ChromaDB获取文档文本失败，回退到重新解析: {e}")

    if not file_path or not os.path.exists(file_path):
        return ""

    file_size = doc.get("file_size", 0)
    max_pages = None
    if file_size and file_size > 50 * 1024 * 1024:
        max_pages = 30
        logger.warning(f"文档 {filename} 过大({file_size / 1024 / 1024:.1f}MB)，仅解析前{max_pages}页")

    try:
        from app.core.document_parser import parse_document
        logger.info(f"开始重新解析文档: {filename}" + (f"（前{max_pages}页）" if max_pages else ""))
        parse_result = parse_document(file_path, filename, max_pages=max_pages)
        paragraphs = parse_result.get("paragraphs", [])
        text_parts = []
        for para in paragraphs:
            content = para.get("content", "")
            if content and content.strip():
                text_parts.append(content.strip())
        text_content = "\n".join(text_parts)
        logger.info(f"文档 {filename} 解析完成，文本长度={len(text_content)}")

        if text_content.strip() and doc_id:
            _backfill_chromadb(doc, text_content)

        return text_content
    except Exception as e:
        logger.error(f"文档解析失败 {filename}: {e}")
        return ""


def _backfill_chromadb(doc: dict, text_content: str):
    doc_id = doc.get("id", "")
    filename = doc.get("filename", "")
    category = doc.get("category", "通用")
    if not doc_id or not text_content.strip():
        return
    try:
        from app.core.chunker import TextChunker
        chunker = TextChunker()
        chunks = chunker.chunk(text_content, document_id=doc_id, strategy="structure")
        if not chunks:
            return

        from app.services.embedding_service import get_embedding_service
        embedding_service = get_embedding_service()

        chunk_texts = [c.content for c in chunks]
        chunk_ids = [c.chunk_id for c in chunks]
        chunk_metadatas = []
        for c in chunks:
            meta = {
                "document_id": doc_id,
                "source": filename,
                "category": category,
                "page": c.page_number or 0,
                "chunk_type": c.chunk_type,
            }
            if c.section_title:
                meta["section_title"] = c.section_title
            chunk_metadatas.append(meta)

        embeddings = embedding_service.embed_texts(chunk_texts)

        from app.core.retriever import get_retriever
        retriever = get_retriever()
        retriever.add_documents(
            documents=chunk_texts,
            embeddings=embeddings,
            metadatas=chunk_metadatas,
            ids=chunk_ids,
        )

        db = get_database()
        conn = db.get_connection()
        conn.execute(
            "UPDATE documents SET chunk_count = ?, status = 'completed' WHERE id = ?",
            (len(chunks), doc_id),
        )
        conn.commit()
        logger.info(f"文档 {filename} 回填ChromaDB完成，分块数={len(chunks)}")
    except Exception as e:
        logger.warning(f"文档 {filename} 回填ChromaDB失败（不影响当前抽取）: {e}")


def _run_background_extraction(task_id: str, doc_ids: list, user_id: str):
    try:
        _run_background_extraction_inner(task_id, doc_ids, user_id)
    except Exception as e:
        logger.error(f"后台抽取线程异常退出: {e}", exc_info=True)
        with _extraction_lock:
            if task_id in _extraction_progress:
                _extraction_progress[task_id]["status"] = "completed"
                _extraction_progress[task_id]["error"] = f"抽取过程发生异常: {str(e)[:200]}"
        _save_task_to_db(task_id, _extraction_progress.get(task_id, {}))


def _run_background_extraction_inner(task_id: str, doc_ids: list, user_id: str):
    with _extraction_lock:
        _extraction_progress[task_id]["status"] = "running"
    _save_task_to_db(task_id, _extraction_progress[task_id])

    db = get_database()
    conn = db.get_connection()

    total = len(doc_ids)
    success_count = 0
    fail_count = 0
    results = []

    for i, doc_id in enumerate(doc_ids):
        with _extraction_lock:
            _extraction_progress[task_id]["current"] = i + 1
            _extraction_progress[task_id]["progress"] = int((i + 0.5) / total * 100)
            _extraction_progress[task_id]["current_doc"] = f"正在处理第 {i + 1}/{total} 个文档..."
        _save_task_to_db(task_id, _extraction_progress[task_id])

        try:
            doc_row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
            if not doc_row:
                results.append({"document_id": doc_id, "status": "skipped", "error": "文档不存在"})
                continue

            doc = dict(doc_row)
            with _extraction_lock:
                _extraction_progress[task_id]["current_doc"] = f"正在获取文档文本: {doc.get('filename', '')}"
            _save_task_to_db(task_id, _extraction_progress[task_id])

            text_content = _get_document_text(doc)
            if not text_content.strip():
                results.append({"document_id": doc_id, "filename": doc["filename"], "status": "skipped", "error": "文档内容为空或解析失败，请尝试重新处理文档"})
                continue

            with _extraction_lock:
                _extraction_progress[task_id]["current_doc"] = f"正在抽取实体: {doc.get('filename', '')}"
            _save_task_to_db(task_id, _extraction_progress[task_id])

            extracted = _extract_entities_from_document(doc, text_content)
            saved = _save_extracted_data(extracted, doc_id, source_type="document")
            results.append({
                "document_id": doc_id,
                "filename": doc["filename"],
                "status": "success",
                "saved": saved,
            })
            success_count += 1
        except Exception as e:
            logger.error(f"文档 {doc_id} 抽取失败: {e}")
            results.append({
                "document_id": doc_id,
                "status": "failed",
                "error": str(e)[:200],
            })
            fail_count += 1

        with _extraction_lock:
            _extraction_progress[task_id]["current"] = i + 1
            _extraction_progress[task_id]["progress"] = int((i + 1) / total * 100)
            _extraction_progress[task_id]["results"] = results
            _extraction_progress[task_id].pop("current_doc", None)
        _save_task_to_db(task_id, _extraction_progress[task_id])

    with _extraction_lock:
        _extraction_progress[task_id]["status"] = "completed"
        _extraction_progress[task_id]["success_count"] = success_count
        _extraction_progress[task_id]["fail_count"] = fail_count
    _save_task_to_db(task_id, _extraction_progress[task_id])

    db.save_log(
        user_id=user_id,
        action="知识图谱文档批量抽取",
        detail=f"total={total}, success={success_count}, fail={fail_count}",
    )


def _run_background_case_extraction(task_id: str, user_id: str):
    try:
        _run_background_case_extraction_inner(task_id, user_id)
    except Exception as e:
        logger.error(f"后台案例抽取线程异常退出: {e}", exc_info=True)
        with _extraction_lock:
            if task_id in _extraction_progress:
                _extraction_progress[task_id]["status"] = "completed"
                _extraction_progress[task_id]["error"] = f"抽取过程发生异常: {str(e)[:200]}"
        _save_task_to_db(task_id, _extraction_progress.get(task_id, {}))


def _run_background_case_extraction_inner(task_id: str, user_id: str):
    with _extraction_lock:
        _extraction_progress[task_id]["status"] = "running"
    _save_task_to_db(task_id, _extraction_progress[task_id])

    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute("SELECT * FROM cases WHERE status = 'approved'")
    cases = cursor.fetchall()

    if not cases:
        with _extraction_lock:
            _extraction_progress[task_id]["status"] = "completed"
            _extraction_progress[task_id]["progress"] = 100
            _extraction_progress[task_id]["success_count"] = 0
            _extraction_progress[task_id]["fail_count"] = 0
        _save_task_to_db(task_id, _extraction_progress[task_id])
        return

    total = len(cases)
    success_count = 0
    fail_count = 0
    results = []

    for i, case in enumerate(cases):
        case_dict = dict(case)
        with _extraction_lock:
            _extraction_progress[task_id]["current"] = i + 1
            _extraction_progress[task_id]["progress"] = int((i + 0.5) / total * 100)
            _extraction_progress[task_id]["current_doc"] = f"正在抽取实体: {case_dict.get('title', '')}"
        _save_task_to_db(task_id, _extraction_progress[task_id])

        try:
            extracted = _extract_entities_from_case(case_dict)
            saved = _save_extracted_data(extracted, case_dict["id"])
            results.append({
                "case_id": case_dict["id"],
                "title": case_dict["title"],
                "status": "success",
                "saved": saved,
            })
            success_count += 1
        except Exception as e:
            logger.error(f"案例 {case_dict['id']} 抽取失败: {e}")
            results.append({
                "case_id": case_dict["id"],
                "title": case_dict["title"],
                "status": "failed",
                "error": str(e)[:200],
            })
            fail_count += 1

        with _extraction_lock:
            _extraction_progress[task_id]["current"] = i + 1
            _extraction_progress[task_id]["progress"] = int((i + 1) / total * 100)
            _extraction_progress[task_id]["results"] = results
            _extraction_progress[task_id].pop("current_doc", None)
        _save_task_to_db(task_id, _extraction_progress[task_id])

    with _extraction_lock:
        _extraction_progress[task_id]["status"] = "completed"
        _extraction_progress[task_id]["success_count"] = success_count
        _extraction_progress[task_id]["fail_count"] = fail_count
    _save_task_to_db(task_id, _extraction_progress[task_id])

    db.save_log(
        user_id=user_id,
        action="知识图谱批量抽取",
        detail=f"total={total}, success={success_count}, fail={fail_count}",
    )


def _run_background_selected_case_extraction(task_id: str, case_ids: list, user_id: str):
    try:
        _run_background_selected_case_extraction_inner(task_id, case_ids, user_id)
    except Exception as e:
        logger.error(f"后台选中案例抽取线程异常退出: {e}", exc_info=True)
        with _extraction_lock:
            if task_id in _extraction_progress:
                _extraction_progress[task_id]["status"] = "completed"
                _extraction_progress[task_id]["error"] = f"抽取过程发生异常: {str(e)[:200]}"
        _save_task_to_db(task_id, _extraction_progress.get(task_id, {}))


def _run_background_selected_case_extraction_inner(task_id: str, case_ids: list, user_id: str):
    with _extraction_lock:
        _extraction_progress[task_id]["status"] = "running"
    _save_task_to_db(task_id, _extraction_progress[task_id])

    db = get_database()
    conn = db.get_connection()

    total = len(case_ids)
    success_count = 0
    fail_count = 0
    results = []

    for i, case_id in enumerate(case_ids):
        with _extraction_lock:
            _extraction_progress[task_id]["current"] = i + 1
            _extraction_progress[task_id]["progress"] = int((i + 0.5) / total * 100)
            _extraction_progress[task_id]["current_doc"] = f"正在处理第 {i + 1}/{total} 个案例..."
        _save_task_to_db(task_id, _extraction_progress[task_id])

        try:
            case_row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
            if not case_row:
                results.append({"case_id": case_id, "status": "skipped", "error": "案例不存在"})
                continue

            case_dict = dict(case_row)
            with _extraction_lock:
                _extraction_progress[task_id]["current_doc"] = f"正在抽取实体: {case_dict.get('title', '')}"
            _save_task_to_db(task_id, _extraction_progress[task_id])

            extracted = _extract_entities_from_case(case_dict)
            saved = _save_extracted_data(extracted, case_id)
            results.append({
                "case_id": case_id,
                "title": case_dict["title"],
                "status": "success",
                "saved": saved,
            })
            success_count += 1
        except Exception as e:
            logger.error(f"案例 {case_id} 抽取失败: {e}")
            results.append({
                "case_id": case_id,
                "status": "failed",
                "error": str(e)[:200],
            })
            fail_count += 1

        with _extraction_lock:
            _extraction_progress[task_id]["current"] = i + 1
            _extraction_progress[task_id]["progress"] = int((i + 1) / total * 100)
            _extraction_progress[task_id]["results"] = results
            _extraction_progress[task_id].pop("current_doc", None)
        _save_task_to_db(task_id, _extraction_progress[task_id])

    with _extraction_lock:
        _extraction_progress[task_id]["status"] = "completed"
        _extraction_progress[task_id]["success_count"] = success_count
        _extraction_progress[task_id]["fail_count"] = fail_count
    _save_task_to_db(task_id, _extraction_progress[task_id])

    db.save_log(
        user_id=user_id,
        action="知识图谱选中案例批量抽取",
        detail=f"total={total}, success={success_count}, fail={fail_count}",
    )


@router.get("/graph", summary="获取完整图谱数据")
async def get_graph():
    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute("SELECT id, name, type, properties, created_at FROM knowledge_graph_nodes")
    nodes = []
    for row in cursor.fetchall():
        props = {}
        try:
            props = json.loads(row["properties"]) if row["properties"] else {}
        except json.JSONDecodeError:
            pass
        nodes.append({
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "properties": props,
            "created_at": row["created_at"],
        })

    cursor = conn.execute("SELECT id, source_id, target_id, relation, weight, properties, created_at FROM knowledge_graph_edges")
    edges = []
    for row in cursor.fetchall():
        props = {}
        try:
            props = json.loads(row["properties"]) if row["properties"] else {}
        except json.JSONDecodeError:
            pass
        edges.append({
            "id": row["id"],
            "source": row["source_id"],
            "target": row["target_id"],
            "relation": row["relation"],
            "weight": row["weight"],
            "properties": props,
            "created_at": row["created_at"],
        })

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "node_types": {t: sum(1 for n in nodes if n["type"] == t) for t in VALID_NODE_TYPES},
            },
        }
    }

@router.delete("/graph", summary="清空知识图谱（删除所有节点和边）")
async def clear_graph():
    db = get_database()
    conn = db.get_connection()

    node_count = conn.execute("SELECT COUNT(*) FROM knowledge_graph_nodes").fetchone()[0]
    edge_count = conn.execute("SELECT COUNT(*) FROM knowledge_graph_edges").fetchone()[0]

    conn.execute("DELETE FROM knowledge_graph_edges")
    conn.execute("DELETE FROM knowledge_graph_nodes")
    conn.commit()

    logger.info(
        f"清空图谱: 删除 {node_count} 个节点, {edge_count} 条边"
    )

    return {
        "code": 200,
        "message": "图谱已清空",
        "data": {
            "deleted_nodes": node_count,
            "deleted_edges": edge_count,
        },
    }

@router.get("/stats", summary="获取图谱统计信息")
async def get_stats():
    db = get_database()
    conn = db.get_connection()

    total_nodes = conn.execute("SELECT COUNT(*) FROM knowledge_graph_nodes").fetchone()[0]
    total_edges = conn.execute("SELECT COUNT(*) FROM knowledge_graph_edges").fetchone()[0]

    type_cursor = conn.execute("SELECT type, COUNT(*) as count FROM knowledge_graph_nodes GROUP BY type")
    nodes_by_type = {row["type"]: row["count"] for row in type_cursor.fetchall()}

    relation_cursor = conn.execute("SELECT relation, COUNT(*) as count FROM knowledge_graph_edges GROUP BY relation")
    edges_by_relation = {row["relation"]: row["count"] for row in relation_cursor.fetchall()}

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "node_types": nodes_by_type,
            "edge_types": edges_by_relation,
        }
    }


@router.get("/available-cases", summary="获取可抽取实体的案例列表")
async def get_available_cases():
    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute(
        "SELECT id, title, fault_type, device_model, status, created_at FROM cases WHERE status = 'approved' ORDER BY created_at DESC"
    )
    cases = []
    for row in cursor.fetchall():
        node_count = 0
        edge_count = 0
        try:
            all_nodes = conn.execute("SELECT properties FROM knowledge_graph_nodes").fetchall()
            for n in all_nodes:
                try:
                    p = json.loads(n["properties"]) if n["properties"] else {}
                except json.JSONDecodeError:
                    p = {}
                if row["id"] in p.get("case_ids", []):
                    node_count += 1
            all_edges = conn.execute("SELECT properties FROM knowledge_graph_edges").fetchall()
            for e in all_edges:
                try:
                    p = json.loads(e["properties"]) if e["properties"] else {}
                except json.JSONDecodeError:
                    p = {}
                if row["id"] in p.get("case_ids", []):
                    edge_count += 1
        except Exception:
            pass
        cases.append({
            "id": row["id"],
            "title": row["title"],
            "fault_type": row["fault_type"],
            "device_model": row["device_model"],
            "status": row["status"],
            "created_at": row["created_at"],
            "extracted": node_count > 0 or edge_count > 0,
            "node_count": node_count,
            "edge_count": edge_count,
        })

    return {
        "code": 200,
        "message": "查询成功",
        "data": cases,
    }


@router.get("/available-documents", summary="获取可抽取实体的文档列表")
async def get_available_documents():
    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute(
        "SELECT id, filename, category, status, upload_time, file_size, chunk_count FROM documents WHERE status IN ('approved', 'completed', 'parsed') ORDER BY upload_time DESC"
    )
    documents = []
    for row in cursor.fetchall():
        node_count = 0
        edge_count = 0
        try:
            all_nodes = conn.execute("SELECT properties FROM knowledge_graph_nodes").fetchall()
            for n in all_nodes:
                try:
                    p = json.loads(n["properties"]) if n["properties"] else {}
                except json.JSONDecodeError:
                    p = {}
                if row["id"] in p.get("document_ids", []):
                    node_count += 1
            all_edges = conn.execute("SELECT properties FROM knowledge_graph_edges").fetchall()
            for e in all_edges:
                try:
                    p = json.loads(e["properties"]) if e["properties"] else {}
                except json.JSONDecodeError:
                    p = {}
                if row["id"] in p.get("document_ids", []):
                    edge_count += 1
        except Exception:
            pass
        documents.append({
            "id": row["id"],
            "filename": row["filename"],
            "category": row["category"],
            "status": row["status"],
            "created_at": row["upload_time"],
            "file_size": row["file_size"] or 0,
            "chunk_count": row["chunk_count"] or 0,
            "extracted": node_count > 0 or edge_count > 0,
            "node_count": node_count,
            "edge_count": edge_count,
        })

    return {
        "code": 200,
        "message": "查询成功",
        "data": documents,
    }


@router.post("/extract/{case_id}", summary="从指定案例抽取实体和关系")
async def extract_from_case(case_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    case = cursor.fetchone()
    if not case:
        raise HTTPException(status_code=404, detail="案例不存在")

    case_dict = dict(case)
    extracted = _extract_entities_from_case(case_dict)
    result = _save_extracted_data(extracted, case_id)

    db.save_log(
        user_id=current_user["id"],
        action="知识图谱抽取",
        detail=f"case_id={case_id}, nodes={result['nodes_saved']}, edges={result['edges_saved']}",
    )

    return {
        "code": 200,
        "message": "实体抽取完成",
        "data": {
            "case_id": case_id,
            "extracted": extracted,
            "saved": result,
        }
    }


@router.post("/extract-document/{document_id}", summary="从指定文档抽取实体和关系")
async def extract_from_document(document_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    doc = db.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if doc["status"] not in ("approved", "completed", "parsed"):
        raise HTTPException(status_code=400, detail=f"文档状态为 '{doc['status']}'，仅已审核/已完成的文档可抽取")

    text_content = _get_document_text(doc)
    if not text_content.strip():
        raise HTTPException(status_code=400, detail="文档内容为空，无法抽取实体")

    extracted = _extract_entities_from_document(doc, text_content)
    result = _save_extracted_data(extracted, document_id, source_type="document")

    db.save_log(
        user_id=current_user["id"],
        action="知识图谱文档抽取",
        detail=f"document_id={document_id}, filename={doc['filename']}, nodes={result['nodes_saved']}, edges={result['edges_saved']}",
    )

    return {
        "code": 200,
        "message": "文档实体抽取完成",
        "data": {
            "document_id": document_id,
            "filename": doc["filename"],
            "extracted": extracted,
            "saved": result,
        }
    }


@router.post("/extract-all", summary="从所有已审核案例批量抽取（后台异步）")
async def extract_from_all_cases(admin: dict = Depends(require_admin)):
    llm = get_llm_service()
    if not llm.is_available():
        raise HTTPException(status_code=503, detail="LLM服务不可用，请检查Ollama服务是否启动或API Key是否配置")

    task_id = str(uuid.uuid4())[:8]
    init_data = {
        "status": "pending",
        "source": "cases",
        "total": 0,
        "current": 0,
        "progress": 0,
        "success_count": 0,
        "fail_count": 0,
        "results": [],
    }
    with _extraction_lock:
        _extraction_progress[task_id] = init_data
    _save_task_to_db(task_id, init_data)

    thread = threading.Thread(
        target=_run_background_case_extraction,
        args=(task_id, admin["id"]),
        daemon=True,
    )
    thread.start()

    return {
        "code": 200,
        "message": "已开始后台抽取案例实体",
        "data": {"task_id": task_id},
    }


@router.post("/extract-documents", summary="从所有已审核文档批量抽取（后台异步）")
async def extract_from_all_documents(admin: dict = Depends(require_admin)):
    llm = get_llm_service()
    if not llm.is_available():
        raise HTTPException(status_code=503, detail="LLM服务不可用，请检查Ollama服务是否启动或API Key是否配置")

    db = get_database()
    conn = db.get_connection()
    cursor = conn.execute(
        "SELECT id FROM documents WHERE status IN ('approved', 'completed', 'parsed')"
    )
    doc_ids = [row["id"] for row in cursor.fetchall()]

    if not doc_ids:
        return {
            "code": 200,
            "message": "没有已审核的文档",
            "data": {"task_id": None, "total": 0},
        }

    task_id = str(uuid.uuid4())[:8]
    init_data = {
        "status": "pending",
        "source": "documents",
        "total": len(doc_ids),
        "current": 0,
        "progress": 0,
        "success_count": 0,
        "fail_count": 0,
        "results": [],
    }
    with _extraction_lock:
        _extraction_progress[task_id] = init_data
    _save_task_to_db(task_id, init_data)

    thread = threading.Thread(
        target=_run_background_extraction,
        args=(task_id, doc_ids, admin["id"]),
        daemon=True,
    )
    thread.start()

    return {
        "code": 200,
        "message": f"已开始后台抽取 {len(doc_ids)} 个文档的实体",
        "data": {"task_id": task_id, "total": len(doc_ids)},
    }


@router.post("/extract-selected", summary="从选中文档批量抽取（后台异步）")
async def extract_from_selected_documents(
    body: dict,
    admin: dict = Depends(require_admin),
):
    document_ids = body.get("document_ids", body.get("ids", []))
    if isinstance(document_ids, str):
        document_ids = [document_ids]

    llm = get_llm_service()
    if not llm.is_available():
        raise HTTPException(status_code=503, detail="LLM服务不可用，请检查Ollama服务是否启动或API Key是否配置")

    if not document_ids:
        raise HTTPException(status_code=400, detail="请至少选择一个文档")

    task_id = str(uuid.uuid4())[:8]
    init_data = {
        "status": "pending",
        "source": "documents",
        "total": len(document_ids),
        "current": 0,
        "progress": 0,
        "success_count": 0,
        "fail_count": 0,
        "results": [],
    }
    with _extraction_lock:
        _extraction_progress[task_id] = init_data
    _save_task_to_db(task_id, init_data)

    thread = threading.Thread(
        target=_run_background_extraction,
        args=(task_id, document_ids, admin["id"]),
        daemon=True,
    )
    thread.start()

    return {
        "code": 200,
        "message": f"已开始后台抽取 {len(document_ids)} 个选中文档的实体",
        "data": {"task_id": task_id, "total": len(document_ids)},
    }


@router.post("/extract-selected-cases", summary="从选中案例批量抽取（后台异步）")
async def extract_from_selected_cases(
    body: dict,
    admin: dict = Depends(require_admin),
):
    case_ids = body.get("case_ids", body.get("ids", []))
    if isinstance(case_ids, str):
        case_ids = [case_ids]

    llm = get_llm_service()
    if not llm.is_available():
        raise HTTPException(status_code=503, detail="LLM服务不可用，请检查Ollama服务是否启动或API Key是否配置")

    if not case_ids:
        raise HTTPException(status_code=400, detail="请至少选择一个案例")

    task_id = str(uuid.uuid4())[:8]
    init_data = {
        "status": "pending",
        "source": "cases",
        "total": len(case_ids),
        "current": 0,
        "progress": 0,
        "success_count": 0,
        "fail_count": 0,
        "results": [],
    }
    with _extraction_lock:
        _extraction_progress[task_id] = init_data
    _save_task_to_db(task_id, init_data)

    thread = threading.Thread(
        target=_run_background_selected_case_extraction,
        args=(task_id, case_ids, admin["id"]),
        daemon=True,
    )
    thread.start()

    return {
        "code": 200,
        "message": f"已开始后台抽取 {len(case_ids)} 个选中案例的实体",
        "data": {"task_id": task_id, "total": len(case_ids)},
    }


def _run_background_reprocess(task_id: str, doc_ids: list, user_id: str):
    try:
        _run_background_reprocess_inner(task_id, doc_ids, user_id)
    except Exception as e:
        logger.error(f"后台重新处理线程异常退出: {e}", exc_info=True)
        with _extraction_lock:
            if task_id in _extraction_progress:
                _extraction_progress[task_id]["status"] = "completed"
                _extraction_progress[task_id]["error"] = f"重新处理过程发生异常: {str(e)[:200]}"
        _save_task_to_db(task_id, _extraction_progress.get(task_id, {}))


def _run_background_reprocess_inner(task_id: str, doc_ids: list, user_id: str):
    with _extraction_lock:
        _extraction_progress[task_id]["status"] = "running"
    _save_task_to_db(task_id, _extraction_progress[task_id])

    db = get_database()
    conn = db.get_connection()

    total = len(doc_ids)
    success_count = 0
    fail_count = 0
    results = []

    for i, doc_id in enumerate(doc_ids):
        with _extraction_lock:
            _extraction_progress[task_id]["current"] = i + 1
            _extraction_progress[task_id]["progress"] = int((i + 0.5) / total * 100)
            _extraction_progress[task_id]["current_doc"] = f"正在重新处理第 {i + 1}/{total} 个文档..."
        _save_task_to_db(task_id, _extraction_progress[task_id])

        try:
            doc_row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
            if not doc_row:
                results.append({"document_id": doc_id, "status": "skipped", "error": "文档不存在"})
                continue

            doc = dict(doc_row)
            file_path = doc.get("filepath", "")
            filename = doc.get("filename", "")

            if not file_path or not os.path.exists(file_path):
                results.append({"document_id": doc_id, "filename": filename, "status": "skipped", "error": "文件不存在"})
                continue

            with _extraction_lock:
                _extraction_progress[task_id]["current_doc"] = f"正在解析文档: {filename}"
            _save_task_to_db(task_id, _extraction_progress[task_id])

            from app.core.document_parser import parse_document
            parse_result = parse_document(file_path, filename)
            paragraphs = parse_result.get("paragraphs", [])
            text_parts = []
            for para in paragraphs:
                content = para.get("content", "")
                if content and content.strip():
                    text_parts.append(content.strip())
            text_content = "\n".join(text_parts)

            if not text_content.strip():
                results.append({"document_id": doc_id, "filename": filename, "status": "skipped", "error": "文档内容为空"})
                continue

            with _extraction_lock:
                _extraction_progress[task_id]["current_doc"] = f"正在向量化入库: {filename}"
            _save_task_to_db(task_id, _extraction_progress[task_id])

            _backfill_chromadb(doc, text_content)

            results.append({
                "document_id": doc_id,
                "filename": filename,
                "status": "success",
            })
            success_count += 1
        except Exception as e:
            logger.error(f"文档 {doc_id} 重新处理失败: {e}")
            results.append({
                "document_id": doc_id,
                "status": "failed",
                "error": str(e)[:200],
            })
            fail_count += 1

        with _extraction_lock:
            _extraction_progress[task_id]["current"] = i + 1
            _extraction_progress[task_id]["progress"] = int((i + 1) / total * 100)
            _extraction_progress[task_id]["results"] = results
            _extraction_progress[task_id].pop("current_doc", None)
        _save_task_to_db(task_id, _extraction_progress[task_id])

    with _extraction_lock:
        _extraction_progress[task_id]["status"] = "completed"
        _extraction_progress[task_id]["success_count"] = success_count
        _extraction_progress[task_id]["fail_count"] = fail_count
    _save_task_to_db(task_id, _extraction_progress[task_id])

    db.save_log(
        user_id=user_id,
        action="知识图谱文档重新处理",
        detail=f"total={total}, success={success_count}, fail={fail_count}",
    )


@router.post("/reprocess-documents", summary="重新处理选中文档（解析+向量化入库）")
async def reprocess_documents(
    body: dict,
    admin: dict = Depends(require_admin),
):
    document_ids = body.get("document_ids", body.get("ids", []))
    if isinstance(document_ids, str):
        document_ids = [document_ids]

    if not document_ids:
        raise HTTPException(status_code=400, detail="请至少选择一个文档")

    task_id = str(uuid.uuid4())[:8]
    init_data = {
        "status": "pending",
        "source": "reprocess",
        "total": len(document_ids),
        "current": 0,
        "progress": 0,
        "success_count": 0,
        "fail_count": 0,
        "results": [],
    }
    with _extraction_lock:
        _extraction_progress[task_id] = init_data
    _save_task_to_db(task_id, init_data)

    thread = threading.Thread(
        target=_run_background_reprocess,
        args=(task_id, document_ids, admin["id"]),
        daemon=True,
    )
    thread.start()

    return {
        "code": 200,
        "message": f"已开始后台重新处理 {len(document_ids)} 个文档",
        "data": {"task_id": task_id, "total": len(document_ids)},
    }


@router.get("/sources", summary="获取图谱中所有来源信息")
async def get_graph_sources():
    db = get_database()
    conn = db.get_connection()

    sources = []
    seen_ids = set()

    all_nodes = conn.execute("SELECT properties FROM knowledge_graph_nodes").fetchall()
    all_edges = conn.execute("SELECT properties FROM knowledge_graph_edges").fetchall()

    case_ids = set()
    document_ids = set()
    for row in all_nodes + all_edges:
        try:
            p = json.loads(row["properties"]) if row["properties"] else {}
        except json.JSONDecodeError:
            p = {}
        for cid in p.get("case_ids", []):
            case_ids.add(cid)
        for did in p.get("document_ids", []):
            document_ids.add(did)

    for cid in case_ids:
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        case_row = conn.execute("SELECT id, title, fault_type, device_model FROM cases WHERE id = ?", (cid,)).fetchone()
        if case_row:
            node_count = 0
            edge_count = 0
            for row in all_nodes:
                try:
                    p = json.loads(row["properties"]) if row["properties"] else {}
                except json.JSONDecodeError:
                    p = {}
                if cid in p.get("case_ids", []):
                    node_count += 1
            for row in all_edges:
                try:
                    p = json.loads(row["properties"]) if row["properties"] else {}
                except json.JSONDecodeError:
                    p = {}
                if cid in p.get("case_ids", []):
                    edge_count += 1
            sources.append({
                "id": cid,
                "type": "case",
                "name": case_row["title"],
                "detail": f"{case_row['fault_type'] or ''} - {case_row['device_model'] or ''}".strip(" -"),
                "node_count": node_count,
                "edge_count": edge_count,
            })

    for did in document_ids:
        if did in seen_ids:
            continue
        seen_ids.add(did)
        doc_row = conn.execute("SELECT id, filename, category FROM documents WHERE id = ?", (did,)).fetchone()
        if doc_row:
            node_count = 0
            edge_count = 0
            for row in all_nodes:
                try:
                    p = json.loads(row["properties"]) if row["properties"] else {}
                except json.JSONDecodeError:
                    p = {}
                if did in p.get("document_ids", []):
                    node_count += 1
            for row in all_edges:
                try:
                    p = json.loads(row["properties"]) if row["properties"] else {}
                except json.JSONDecodeError:
                    p = {}
                if did in p.get("document_ids", []):
                    edge_count += 1
            sources.append({
                "id": did,
                "type": "document",
                "name": doc_row["filename"],
                "detail": doc_row["category"] or "",
                "node_count": node_count,
                "edge_count": edge_count,
            })

    return {
        "code": 200,
        "message": "查询成功",
        "data": sources,
    }


@router.get("/graph-by-source", summary="按来源筛选图谱数据")
async def get_graph_by_source(
    source_id: str = Query(..., description="来源ID"),
    source_type: str = Query(default="case", description="来源类型: case 或 document"),
):
    db = get_database()
    conn = db.get_connection()

    source_key = "case_ids" if source_type == "case" else "document_ids"

    all_nodes = conn.execute("SELECT id, name, type, properties, created_at FROM knowledge_graph_nodes").fetchall()
    filtered_node_ids = set()
    nodes = []
    for row in all_nodes:
        try:
            p = json.loads(row["properties"]) if row["properties"] else {}
        except json.JSONDecodeError:
            p = {}
        if source_id in p.get(source_key, []):
            filtered_node_ids.add(row["id"])
            nodes.append({
                "id": row["id"],
                "name": row["name"],
                "type": row["type"],
                "properties": p,
                "created_at": row["created_at"],
            })

    all_edges = conn.execute("SELECT id, source_id, target_id, relation, weight, properties, created_at FROM knowledge_graph_edges").fetchall()
    edges = []
    for row in all_edges:
        if row["source_id"] in filtered_node_ids and row["target_id"] in filtered_node_ids:
            try:
                p = json.loads(row["properties"]) if row["properties"] else {}
            except json.JSONDecodeError:
                p = {}
            edges.append({
                "id": row["id"],
                "source": row["source_id"],
                "target": row["target_id"],
                "relation": row["relation"],
                "weight": row["weight"],
                "properties": p,
                "created_at": row["created_at"],
            })

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "nodes": nodes,
            "edges": edges,
            "source_id": source_id,
            "source_type": source_type,
        }
    }


@router.get("/extraction-progress/{task_id}", summary="查询抽取任务进度")
async def get_extraction_progress(task_id: str):
    with _extraction_lock:
        progress = _extraction_progress.get(task_id)

    if not progress:
        progress = _load_task_from_db(task_id)
        if progress:
            with _extraction_lock:
                _extraction_progress[task_id] = progress

    if not progress:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    return {
        "code": 200,
        "message": "查询成功",
        "data": progress,
    }


@router.post("/node", summary="手动添加节点")
async def create_node(payload: dict = Body(...)):
    name = (payload.get("name") or "").strip()
    node_type = (payload.get("type") or "").strip()
    description = (payload.get("description") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="节点名称不能为空")
    if not node_type:
        raise HTTPException(status_code=400, detail="节点类型不能为空")
    if node_type not in VALID_NODE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"无效的节点类型，可选值: {', '.join(sorted(VALID_NODE_TYPES))}",
        )

    db = get_database()
    conn = db.get_connection()
    node_id = _generate_node_id(name, node_type)

    existing = conn.execute(
        "SELECT id FROM knowledge_graph_nodes WHERE id = ?", (node_id,)
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail=f"节点已存在（同名同类型）: {name}")

    now = datetime.now().isoformat()
    properties = {"manual": True, "description": description, "case_ids": [], "document_ids": []}
    conn.execute(
        "INSERT INTO knowledge_graph_nodes (id, name, type, properties, created_at) VALUES (?, ?, ?, ?, ?)",
        (node_id, name, node_type, json.dumps(properties, ensure_ascii=False), now),
    )
    conn.commit()
    logger.info(f"手动添加节点: id={node_id}, name={name}, type={node_type}")

    return {
        "code": 200,
        "message": "添加成功",
        "data": {
            "id": node_id,
            "name": name,
            "type": node_type,
            "description": description,
            "properties": properties,
            "created_at": now,
        },
    }


@router.put("/node/{node_id}", summary="更新节点")
async def update_node(node_id: str, payload: dict = Body(...)):
    name = (payload.get("name") or "").strip()
    node_type = (payload.get("type") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="节点名称不能为空")
    if not node_type:
        raise HTTPException(status_code=400, detail="节点类型不能为空")
    if node_type not in VALID_NODE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"无效的节点类型，可选值: {', '.join(sorted(VALID_NODE_TYPES))}",
        )

    db = get_database()
    conn = db.get_connection()
    existing = conn.execute(
        "SELECT id, properties FROM knowledge_graph_nodes WHERE id = ?", (node_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="节点不存在")

    try:
        existing_props = json.loads(existing["properties"]) if existing["properties"] else {}
    except json.JSONDecodeError:
        existing_props = {}

    conn.execute(
        "UPDATE knowledge_graph_nodes SET name = ?, type = ? WHERE id = ?",
        (name, node_type, node_id),
    )
    conn.commit()

    return {
        "code": 200,
        "message": "更新成功",
        "data": {
            "id": node_id,
            "name": name,
            "type": node_type,
            "properties": existing_props,
        },
    }


@router.delete("/node/{node_id}", summary="删除节点（级联删除关联边）")
async def delete_node(node_id: str):
    db = get_database()
    conn = db.get_connection()
    existing = conn.execute(
        "SELECT id, name, type FROM knowledge_graph_nodes WHERE id = ?", (node_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="节点不存在")

    # 级联删除以该节点为 source 或 target 的边
    edge_cursor = conn.execute(
        "SELECT id FROM knowledge_graph_edges WHERE source_id = ? OR target_id = ?",
        (node_id, node_id),
    )
    edge_ids = [row["id"] for row in edge_cursor.fetchall()]

    if edge_ids:
        placeholders = ",".join("?" * len(edge_ids))
        conn.execute(
            f"DELETE FROM knowledge_graph_edges WHERE id IN ({placeholders})",
            edge_ids,
        )

    conn.execute("DELETE FROM knowledge_graph_nodes WHERE id = ?", (node_id,))
    conn.commit()

    logger.info(
        f"删除节点: id={node_id}, name={existing['name']}, type={existing['type']}, "
        f"cascade_edges={len(edge_ids)}"
    )

    return {
        "code": 200,
        "message": "删除成功",
        "data": {
            "node_id": node_id,
            "deleted_edges": len(edge_ids),
        },
    }


@router.get("/node/{node_id}", summary="获取节点详情")
async def get_node_detail(node_id: str):
    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute("SELECT * FROM knowledge_graph_nodes WHERE id = ?", (node_id,))
    node = cursor.fetchone()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    props = {}
    try:
        props = json.loads(node["properties"]) if node["properties"] else {}
    except json.JSONDecodeError:
        pass

    outgoing_cursor = conn.execute(
        "SELECT e.id, e.target_id, e.relation, e.weight, n.name as target_name, n.type as target_type FROM knowledge_graph_edges e JOIN knowledge_graph_nodes n ON e.target_id = n.id WHERE e.source_id = ?",
        (node_id,),
    )
    outgoing = []
    for row in outgoing_cursor.fetchall():
        outgoing.append({
            "edge_id": row["id"],
            "target_id": row["target_id"],
            "target_name": row["target_name"],
            "target_type": row["target_type"],
            "relation": row["relation"],
            "weight": row["weight"],
        })

    incoming_cursor = conn.execute(
        "SELECT e.id, e.source_id, e.relation, e.weight, n.name as source_name, n.type as source_type FROM knowledge_graph_edges e JOIN knowledge_graph_nodes n ON e.source_id = n.id WHERE e.target_id = ?",
        (node_id,),
    )
    incoming = []
    for row in incoming_cursor.fetchall():
        incoming.append({
            "edge_id": row["id"],
            "source_id": row["source_id"],
            "source_name": row["source_name"],
            "source_type": row["source_type"],
            "relation": row["relation"],
            "weight": row["weight"],
        })

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "node": {
                "id": node["id"],
                "name": node["name"],
                "type": node["type"],
                "properties": props,
                "created_at": node["created_at"],
            },
            "outgoing_edges": outgoing,
            "incoming_edges": incoming,
        }
    }


@router.get("/search", summary="在图谱中搜索节点")
async def search_nodes(
    query: str = Query(..., min_length=1, description="搜索关键词"),
    node_type: Optional[str] = Query(default=None, description="节点类型筛选"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    db = get_database()
    conn = db.get_connection()

    conditions = ["name LIKE ?"]
    escaped_query = query.replace("%", "\\%").replace("_", "\\_")
    params: list = [f"%{escaped_query}%"]

    if node_type:
        if node_type not in VALID_NODE_TYPES:
            raise HTTPException(status_code=400, detail=f"无效的节点类型，可选值: {', '.join(VALID_NODE_TYPES)}")
        conditions.append("type = ?")
        params.append(node_type)

    where_clause = "WHERE " + " AND ".join(conditions)

    count_result = conn.execute(
        f"SELECT COUNT(*) FROM knowledge_graph_nodes {where_clause}", params
    ).fetchone()
    total = count_result[0]

    offset = (page - 1) * page_size
    cursor = conn.execute(
        f"SELECT id, name, type, properties, created_at FROM knowledge_graph_nodes {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    )

    nodes = []
    for row in cursor.fetchall():
        props = {}
        try:
            props = json.loads(row["properties"]) if row["properties"] else {}
        except json.JSONDecodeError:
            pass
        nodes.append({
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "properties": props,
            "created_at": row["created_at"],
        })

    return {
        "code": 200,
        "message": "搜索成功",
        "data": {
            "query": query,
            "nodes": nodes,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    }
