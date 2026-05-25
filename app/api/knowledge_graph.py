import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import get_current_user, require_admin
from app.config import settings
from app.models.database import get_database
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])

VALID_NODE_TYPES = {"device", "fault", "solution", "person", "procedure", "standard"}
VALID_RELATION_TYPES = {"has_fault", "solved_by", "related_to", "requires", "complies_with"}


def _generate_node_id(name: str, node_type: str) -> str:
    import hashlib
    raw = f"{node_type}:{name}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def _extract_entities_from_case(case: dict) -> dict:
    llm = get_llm_service()
    if not llm.is_available():
        raise HTTPException(status_code=503, detail="LLM服务不可用，无法抽取实体")

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
    except Exception as e:
        logger.error(f"LLM实体抽取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"实体抽取失败: {str(e)}")


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
        raise HTTPException(status_code=503, detail="LLM服务不可用，无法抽取实体")

    CHUNK_SIZE = 4000
    MAX_CHUNKS = 3
    text_chunks = []
    for i in range(0, len(text_content), CHUNK_SIZE):
        text_chunks.append(text_content[i:i + CHUNK_SIZE])
        if len(text_chunks) >= MAX_CHUNKS:
            break

    all_nodes = []
    all_edges = []

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
        except Exception as e:
            logger.warning(f"文档第{idx + 1}段实体抽取失败: {e}")
            continue

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

    try:
        from app.core.document_parser import parse_document
        parse_result = parse_document(file_path, filename)
        paragraphs = parse_result.get("paragraphs", [])
        text_parts = []
        for para in paragraphs:
            content = para.get("content", "")
            if content and content.strip():
                text_parts.append(content.strip())
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"文档解析失败 {filename}: {e}")
        return ""


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
        }
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


@router.post("/extract-all", summary="从所有已审核案例批量抽取")
async def extract_from_all_cases(admin: dict = Depends(require_admin)):
    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute("SELECT * FROM cases WHERE status = 'approved'")
    cases = cursor.fetchall()

    if not cases:
        return {
            "code": 200,
            "message": "没有已审核的案例",
            "data": {"total_cases": 0, "success_count": 0, "fail_count": 0, "results": []}
        }

    results = []
    success_count = 0
    fail_count = 0

    for case in cases:
        case_dict = dict(case)
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
                "error": str(e),
            })
            fail_count += 1

    db.save_log(
        user_id=admin["id"],
        action="知识图谱批量抽取",
        detail=f"total={len(cases)}, success={success_count}, fail={fail_count}",
    )

    return {
        "code": 200,
        "message": f"批量抽取完成，成功{success_count}个，失败{fail_count}个",
        "data": {
            "total_cases": len(cases),
            "success_count": success_count,
            "fail_count": fail_count,
            "results": results,
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


@router.post("/extract-documents", summary="从所有已审核文档批量抽取")
async def extract_from_all_documents(admin: dict = Depends(require_admin)):
    db = get_database()
    conn = db.get_connection()

    cursor = conn.execute(
        "SELECT * FROM documents WHERE status IN ('approved', 'completed', 'parsed')"
    )
    documents = cursor.fetchall()

    if not documents:
        return {
            "code": 200,
            "message": "没有已审核的文档",
            "data": {"total_documents": 0, "success_count": 0, "fail_count": 0, "results": []}
        }

    results = []
    success_count = 0
    fail_count = 0

    for doc_row in documents:
        doc = dict(doc_row)
        try:
            text_content = _get_document_text(doc)
            if not text_content.strip():
                results.append({
                    "document_id": doc["id"],
                    "filename": doc["filename"],
                    "status": "skipped",
                    "error": "文档内容为空",
                })
                continue

            extracted = _extract_entities_from_document(doc, text_content)
            saved = _save_extracted_data(extracted, doc["id"], source_type="document")
            results.append({
                "document_id": doc["id"],
                "filename": doc["filename"],
                "status": "success",
                "saved": saved,
            })
            success_count += 1
        except Exception as e:
            logger.error(f"文档 {doc['id']} 抽取失败: {e}")
            results.append({
                "document_id": doc["id"],
                "filename": doc["filename"],
                "status": "failed",
                "error": str(e),
            })
            fail_count += 1

    db.save_log(
        user_id=admin["id"],
        action="知识图谱文档批量抽取",
        detail=f"total={len(documents)}, success={success_count}, fail={fail_count}",
    )

    return {
        "code": 200,
        "message": f"文档批量抽取完成，成功{success_count}个，失败{fail_count}个",
        "data": {
            "total_documents": len(documents),
            "success_count": success_count,
            "fail_count": fail_count,
            "results": results,
        }
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
    params: list = [f"%{query.replace('%', '\\%').replace('_', '\\_')}%"]

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
