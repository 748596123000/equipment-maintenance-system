"""
知识检索引擎模块（无 ChromaDB 依赖版）

基于 SQLite FTS5 + numpy 实现：
- 语义检索：使用 numpy 计算余弦相似度（embedding 通过 EmbeddingService 生成）
- 关键词检索：使用 SQLite FTS5 全文搜索
- 混合检索：融合语义和关键词结果（加权倒数排名融合）
- 设备型号检索：针对设备型号的精确匹配（metadata 过滤）

无需 chromadb / onnxruntime / hnswlib 等重型 C 扩展依赖。
设计目标：在 LoongArch 等无 ChromaDB 预编译 wheel 的平台上正常运行。
"""

import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import struct
import threading
import time
from array import array
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# 使用 array('f') 做向量运算（单精度浮点，numpy-free）
Float32Array = array  # alias


def _vec_from_bytes(b: bytes) -> array:
    """bytes -> array('f')"""
    if not b or len(b) % 4 != 0:
        return array('f')
    try:
        return array('f', b)
    except Exception:
        return array('f')


def _vec_to_bytes(v) -> bytes:
    """array('f')/list -> bytes"""
    if isinstance(v, array):
        return v.tobytes()
    return array('f', (float(x) for x in v)).tobytes()


def _vec_norm(v) -> float:
    """||v||_2"""
    s = 0.0
    for x in v:
        s += float(x) * float(x)
    return math.sqrt(s)


def _vec_dot(a, b) -> float:
    """a·b"""
    n = min(len(a), len(b))
    s = 0.0
    for i in range(n):
        s += float(a[i]) * float(b[i])
    return s


def _vec_cosine(query, doc) -> float:
    """cosine similarity"""
    qn = _vec_norm(query)
    dn = _vec_norm(doc)
    if qn == 0.0 or dn == 0.0:
        return 0.0
    return _vec_dot(query, doc) / (qn * dn)


_query_cache = {}
CACHE_TTL = 300


class SearchResult:
    """检索结果数据结构"""

    def __init__(
        self,
        chunk_id: str,
        content: str,
        source: str,
        score: float,
        page_number: Optional[int] = None,
        category: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        self.chunk_id = chunk_id
        self.content = content
        self.source = source
        self.score = score
        self.page_number = page_number
        self.category = category
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "source": self.source,
            "score": self.score,
            "page_number": self.page_number,
            "category": self.category,
            "metadata": self.metadata,
        }


class KnowledgeRetriever:
    """
    知识检索引擎（SQLite FTS5 + numpy 实现）

    Attributes:
        db_path: SQLite 数据库文件路径
        collection_name: 集合名称（用作表名后缀）
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        self.collection_name = collection_name or "knowledge_base"
        default_db_path = "./data/app.db"
        self.db_path = db_path or default_db_path
        self._chunks_table = f"chunks_{self.collection_name}"
        self._fts_table = f"fts_{self.collection_name}"
        self._init_lock = threading.Lock()
        self._initialized = False
        self._embeddings_cache: dict = {}  # chunk_id -> np.ndarray
        self._embeddings_cache_loaded = False

    def init_collection(self) -> None:
        """初始化 SQLite 表 + FTS5 虚拟表"""
        with self._init_lock:
            if self._initialized:
                return

            try:
                os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")

                # 1. 主表（存储 chunk + embedding BLOB + metadata）
                conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self._chunks_table} (
                        chunk_id TEXT PRIMARY KEY,
                        document_id TEXT,
                        content TEXT NOT NULL,
                        embedding BLOB,
                        page_number INTEGER,
                        category TEXT,
                        source TEXT,
                        metadata_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 索引（加速过滤查询）
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{self._chunks_table}_doc ON {self._chunks_table}(document_id)")
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{self._chunks_table}_cat ON {self._chunks_table}(category)")

                # 2. FTS5 虚拟表（全文检索）
                try:
                    conn.execute(f"""
                        CREATE VIRTUAL TABLE IF NOT EXISTS {self._fts_table} USING fts5(
                            chunk_id UNINDEXED,
                            content,
                            source,
                            category,
                            tokenize='unicode61'
                        )
                    """)
                    logger.info(f"FTS5 虚拟表创建完成: {self._fts_table}")
                except sqlite3.OperationalError as e:
                    if "no such module" in str(e).lower() or "fts5" in str(e).lower():
                        logger.warning(f"SQLite FTS5 不可用: {e}，关键词检索将降级为 LIKE 查询")
                    else:
                        raise

                conn.commit()
                conn.close()
                self._initialized = True
                logger.info(f"SQLite 检索引擎初始化完成: {self.db_path} / {self._chunks_table}")

            except Exception as e:
                logger.error(f"SQLite 检索引擎初始化失败: {e}", exc_info=True)
                raise

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _load_embeddings_cache(self) -> None:
        """一次性把所有 embedding 加载到内存（小项目场景，<10万条没问题）"""
        if self._embeddings_cache_loaded:
            return
        try:
            conn = self._get_conn()
            cur = conn.execute(f"SELECT chunk_id, embedding FROM {self._chunks_table} WHERE embedding IS NOT NULL")
            loaded = 0
            for row in cur:
                if row["embedding"]:
                    try:
                        arr = _vec_from_bytes(row["embedding"])
                        self._embeddings_cache[row["chunk_id"]] = arr
                        loaded += 1
                    except Exception:
                        continue
            conn.close()
            self._embeddings_cache_loaded = True
            logger.info(f"已加载 {loaded} 个 embedding 到内存")
        except Exception as e:
            logger.warning(f"加载 embedding 缓存失败: {e}")

    def _invalidate_cache(self) -> None:
        self._embeddings_cache_loaded = False
        self._embeddings_cache.clear()
        global _query_cache
        _query_cache.clear()

    def _get_cache_key(self, query: str, top_k: int, **kwargs) -> str:
        key_str = f"{query}_{top_k}_{sorted(kwargs.items())}"
        return hashlib.md5(key_str.encode()).hexdigest()

    @staticmethod
    def clear_query_cache():
        global _query_cache
        _query_cache.clear()
        logger.info("查询缓存已清空")

    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict],
        ids: Optional[List[str]] = None,
    ) -> bool:
        """
        批量添加文档到检索引擎
        """
        if not self._initialized:
            self.init_collection()

        if not documents or not embeddings:
            logger.warning("文档或向量为空，跳过添加")
            return False

        if len(documents) != len(embeddings) or len(documents) != len(metadatas):
            logger.error("文档、向量和元数据长度不一致")
            return False

        if ids is None:
            ids = [f"chunk_{int(time.time() * 1000)}_{i}_{hashlib.md5(d.encode()).hexdigest()[:8]}" for i, d in enumerate(documents)]

        try:
            conn = self._get_conn()
            now_iso = time.strftime("%Y-%m-%d %H:%M:%S")

            for i, (doc_id, content, embedding, meta) in enumerate(zip(ids, documents, embeddings, metadatas)):
                emb_bytes = _vec_to_bytes(embedding)
                meta_json = json.dumps(meta or {}, ensure_ascii=False)

                # 写入主表（REPLACE 策略）
                conn.execute(
                    f"""INSERT OR REPLACE INTO {self._chunks_table}
                       (chunk_id, document_id, content, embedding, page_number, category, source, metadata_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        doc_id,
                        meta.get("document_id", ""),
                        content,
                        emb_bytes,
                        meta.get("page_number"),
                        meta.get("category", ""),
                        meta.get("source", ""),
                        meta_json,
                        now_iso,
                    ),
                )

                # 写入 FTS5
                try:
                    conn.execute(
                        f"DELETE FROM {self._fts_table} WHERE chunk_id = ?",
                        (doc_id,),
                    )
                    conn.execute(
                        f"INSERT INTO {self._fts_table} (chunk_id, content, source, category) VALUES (?, ?, ?, ?)",
                        (doc_id, content, meta.get("source", ""), meta.get("category", "")),
                    )
                except sqlite3.OperationalError:
                    pass  # FTS5 不可用时跳过

            conn.commit()
            conn.close()

            # 更新内存 embedding 缓存
            for doc_id, embedding in zip(ids, embeddings):
                self._embeddings_cache[doc_id] = _vec_to_bytes(embedding)
                if isinstance(self._embeddings_cache[doc_id], bytes):
                    self._embeddings_cache[doc_id] = _vec_from_bytes(self._embeddings_cache[doc_id])

            logger.info(f"成功添加 {len(documents)} 条文档到 SQLite 检索引擎")
            return True

        except Exception as e:
            logger.error(f"添加文档失败: {e}", exc_info=True)
            return False

    def search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        """
        语义检索：通过 embedding 余弦相似度匹配
        """
        if not self._initialized:
            self.init_collection()

        # 检查缓存
        cache_key = self._get_cache_key(query, top_k, category=category, threshold=threshold)
        cached = _query_cache.get(cache_key)
        if cached:
            return cached

        # 生成查询向量
        try:
            from app.services.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            query_embedding = embedding_service.embed_text(query)
        except Exception as e:
            logger.error(f"生成查询向量失败: {e}", exc_info=True)
            return []

        # 计算余弦相似度
        try:
            self._load_embeddings_cache()
            conn = self._get_conn()

            if category:
                cur = conn.execute(
                    f"SELECT chunk_id, content, source, page_number, category, metadata_json FROM {self._chunks_table} WHERE category = ? AND embedding IS NOT NULL",
                    (category,),
                )
            else:
                cur = conn.execute(
                    f"SELECT chunk_id, content, source, page_number, category, metadata_json FROM {self._chunks_table} WHERE embedding IS NOT NULL"
                )

            query_vec = array('f', (float(x) for x in query_embedding))
            query_norm = _vec_norm(query_vec)
            if query_norm == 0.0:
                query_norm = 1.0

            scored: List[Tuple[float, sqlite3.Row]] = []
            for row in cur:
                emb = self._embeddings_cache.get(row["chunk_id"])
                if emb is None:
                    # 缓存未命中（重启后冷启动），跳过
                    continue
                score = _vec_cosine(query_vec, emb)
                scored.append((score, row))

            conn.close()

            # 按分数降序
            scored.sort(key=lambda x: x[0], reverse=True)

            # 应用阈值
            if threshold is not None:
                scored = [(s, r) for s, r in scored if s >= threshold]

            # top_k
            scored = scored[:top_k]

            search_results = []
            for score, row in scored:
                meta = {}
                try:
                    meta = json.loads(row["metadata_json"] or "{}")
                except Exception:
                    pass

                search_results.append(SearchResult(
                    chunk_id=row["chunk_id"],
                    content=row["content"],
                    source=row["source"] or "",
                    score=float(score),
                    page_number=row["page_number"],
                    category=row["category"] or "",
                    metadata=meta,
                ))

            _query_cache[cache_key] = search_results
            logger.info(f"语义检索完成: query='{query[:30]}...', 返回 {len(search_results)} 条结果")
            return search_results

        except Exception as e:
            logger.error(f"向量检索失败: {e}", exc_info=True)
            return []

    def keyword_search(
        self,
        keywords: List[str],
        top_k: int = 5,
        match_mode: str = "any",
    ) -> List[SearchResult]:
        """
        关键词检索：优先 FTS5，降级为 LIKE
        """
        if not self._initialized:
            self.init_collection()

        if not keywords:
            return []

        try:
            conn = self._get_conn()
            search_results: List[SearchResult] = []
            seen_ids = set()

            # 尝试 FTS5
            try:
                for keyword in keywords:
                    # FTS5 用双引号包裹短语，支持 AND/OR
                    if match_mode == "all":
                        pattern = " AND ".join(f'"{k}"' for k in keywords)
                    else:
                        pattern = " OR ".join(f'"{k}"' for k in keywords)

                    cur = conn.execute(
                        f"SELECT chunk_id FROM {self._fts_table} WHERE {self._fts_table} MATCH ? LIMIT ?",
                        (pattern, top_k * 2),
                    )
                    for row in cur:
                        cid = row["chunk_id"]
                        if cid in seen_ids:
                            continue
                        seen_ids.add(cid)

                        # 回主表取完整数据
                        cur2 = conn.execute(
                            f"SELECT chunk_id, content, source, page_number, category, metadata_json FROM {self._chunks_table} WHERE chunk_id = ?",
                            (cid,),
                        )
                        r = cur2.fetchone()
                        if not r:
                            continue
                        # 算匹配分：命中的关键词数 / 总关键词数
                        matched = sum(1 for kw in keywords if kw.lower() in r["content"].lower())
                        score = matched / len(keywords) if keywords else 0.0
                        meta = {}
                        try:
                            meta = json.loads(r["metadata_json"] or "{}")
                        except Exception:
                            pass
                        search_results.append(SearchResult(
                            chunk_id=r["chunk_id"],
                            content=r["content"],
                            source=r["source"] or "",
                            score=score,
                            page_number=r["page_number"],
                            category=r["category"] or "",
                            metadata=meta,
                        ))

                        if len(search_results) >= top_k:
                            break
                    if len(search_results) >= top_k:
                        break
            except sqlite3.OperationalError as e:
                # FTS5 不可用，降级 LIKE
                logger.debug(f"FTS5 不可用，降级 LIKE: {e}")
                search_results = []
                seen_ids = set()
                like_clauses = " OR ".join(["(content LIKE ? OR source LIKE ? OR category LIKE ?)"] * len(keywords))
                params = []
                for kw in keywords:
                    pat = f"%{kw}%"
                    params.extend([pat, pat, pat])

                cur = conn.execute(
                    f"SELECT chunk_id, content, source, page_number, category, metadata_json FROM {self._chunks_table} WHERE {like_clauses} LIMIT ?",
                    params + [top_k * 2],
                )
                for r in cur:
                    if r["chunk_id"] in seen_ids:
                        continue
                    seen_ids.add(r["chunk_id"])
                    matched = sum(1 for kw in keywords if kw.lower() in r["content"].lower())
                    score = matched / len(keywords) if keywords else 0.0
                    meta = {}
                    try:
                        meta = json.loads(r["metadata_json"] or "{}")
                    except Exception:
                        pass
                    search_results.append(SearchResult(
                        chunk_id=r["chunk_id"],
                        content=r["content"],
                        source=r["source"] or "",
                        score=score,
                        page_number=r["page_number"],
                        category=r["category"] or "",
                        metadata=meta,
                    ))

            conn.close()
            search_results.sort(key=lambda x: x.score, reverse=True)
            return search_results[:top_k]

        except Exception as e:
            logger.error(f"关键词检索失败: {e}", exc_info=True)
            return []

    def hybrid_search(
        self,
        query: str,
        keywords: Optional[List[str]] = None,
        top_k: int = 5,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> List[SearchResult]:
        """混合检索：融合语义和关键词结果"""
        semantic_results = self.search(query, top_k=top_k * 2)
        keyword_results = []

        if keywords:
            keyword_results = self.keyword_search(keywords, top_k=top_k * 2)
        else:
            extracted = self._extract_keywords(query)
            if extracted:
                keyword_results = self.keyword_search(extracted, top_k=top_k * 2)

        return self._reciprocal_rank_fusion(semantic_results, keyword_results, semantic_weight, keyword_weight)[:top_k]

    def _extract_keywords(self, text: str) -> List[str]:
        stop_words = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
            "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
            "会", "着", "没有", "看", "好", "自己", "这", "他", "她", "它",
            "可以", "能", "应该", "需要", "请", "问",
            "设备", "检修", "维护", "故障", "问题", "方法", "步骤", "操作",
        }
        words = re.split(r'[\s,，。！？、；：""''（）]+', text)
        keywords = []
        for word in words:
            word = word.strip()
            if not word or word in stop_words or len(word) < 2:
                continue
            keywords.append(word)
        return keywords[:5]

    def _reciprocal_rank_fusion(
        self,
        results_a: List[SearchResult],
        results_b: List[SearchResult],
        weight_a: float,
        weight_b: float,
        k: int = 60,
    ) -> List[SearchResult]:
        if not results_a:
            return results_b
        if not results_b:
            return results_a
        scores = {}
        all_results = {}
        for rank, result in enumerate(results_a):
            doc_id = result.chunk_id
            scores[doc_id] = scores.get(doc_id, 0) + weight_a / (k + rank + 1)
            all_results[doc_id] = result
        for rank, result in enumerate(results_b):
            doc_id = result.chunk_id
            scores[doc_id] = scores.get(doc_id, 0) + weight_b / (k + rank + 1)
            if doc_id not in all_results:
                all_results[doc_id] = result
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [
            SearchResult(
                chunk_id=all_results[doc_id].chunk_id,
                content=all_results[doc_id].content,
                source=all_results[doc_id].source,
                score=scores[doc_id],
                page_number=all_results[doc_id].page_number,
                category=all_results[doc_id].category,
                metadata=all_results[doc_id].metadata,
            )
            for doc_id in sorted_ids
        ]

    def model_search(
        self,
        model_number: str,
        query: Optional[str] = None,
        top_k: int = 5,
    ) -> List[SearchResult]:
        return self.search(f"{model_number} {query or ''}", top_k=top_k)

    def delete_collection(self) -> bool:
        try:
            if not self._initialized:
                self.init_collection()
            conn = self._get_conn()
            conn.execute(f"DROP TABLE IF EXISTS {self._chunks_table}")
            try:
                conn.execute(f"DROP TABLE IF EXISTS {self._fts_table}")
            except Exception:
                pass
            conn.commit()
            conn.close()
            self._invalidate_cache()
            logger.info(f"已删除集合: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"删除集合失败: {e}", exc_info=True)
            return False

    def delete_by_document_id(self, document_id: str) -> int:
        if not self._initialized:
            self.init_collection()
        try:
            conn = self._get_conn()
            cur = conn.execute(
                f"SELECT chunk_id FROM {self._chunks_table} WHERE document_id = ?",
                (document_id,),
            )
            ids = [r["chunk_id"] for r in cur]
            if not ids:
                conn.close()
                return 0

            for cid in ids:
                conn.execute(f"DELETE FROM {self._chunks_table} WHERE chunk_id = ?", (cid,))
                try:
                    conn.execute(f"DELETE FROM {self._fts_table} WHERE chunk_id = ?", (cid,))
                except Exception:
                    pass
                self._embeddings_cache.pop(cid, None)

            conn.commit()
            conn.close()
            logger.info(f"已删除文档 {document_id} 的 {len(ids)} 条向量数据")
            return len(ids)
        except Exception as e:
            logger.error(f"删除文档向量数据失败: {e}", exc_info=True)
            return 0

    def get_collection_stats(self) -> dict:
        try:
            if not self._initialized:
                self.init_collection()
            conn = self._get_conn()
            cur = conn.execute(f"SELECT COUNT(*) AS c FROM {self._chunks_table}")
            count = cur.fetchone()["c"]
            conn.close()
            return {
                "collection_name": self.collection_name,
                "total_chunks": count,
                "persist_dir": self.db_path,
                "status": "active",
            }
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {e}", exc_info=True)
            return {"collection_name": self.collection_name, "total_chunks": 0, "status": "error"}

    def rebuild_index(self) -> dict:
        try:
            if not self._initialized:
                self.init_collection()
            conn = self._get_conn()
            cur = conn.execute(f"SELECT chunk_id, content, embedding, metadata_json FROM {self._chunks_table}")
            rows = cur.fetchall()
            conn.close()

            if not rows:
                return {"status": "completed", "total_chunks": 0, "message": "集合为空"}

            # 这里 embedding 已经存了，无需重新生成
            # 仅刷新 FTS5 索引
            conn = self._get_conn()
            try:
                conn.execute(f"DELETE FROM {self._fts_table}")
                for r in rows:
                    meta = {}
                    try:
                        meta = json.loads(r["metadata_json"] or "{}")
                    except Exception:
                        pass
                    conn.execute(
                        f"INSERT INTO {self._fts_table} (chunk_id, content, source, category) VALUES (?, ?, ?, ?)",
                        (r["chunk_id"], r["content"], meta.get("source", ""), meta.get("category", "")),
                    )
                conn.commit()
            except sqlite3.OperationalError:
                pass
            conn.close()

            self._invalidate_cache()
            return {"status": "completed", "total_chunks": len(rows)}
        except Exception as e:
            logger.error(f"索引重建失败: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}


# ========== 兼容旧接口 ==========

class Retriever(KnowledgeRetriever):
    """知识检索引擎（兼容旧接口）"""

    def semantic_search(self, query: str, top_k: int = 5, category: Optional[str] = None, threshold: Optional[float] = None) -> List[SearchResult]:
        return self.search(query, top_k, category, threshold)


# 全局检索引擎单例
_retriever_instance: Optional[KnowledgeRetriever] = None


def get_retriever() -> KnowledgeRetriever:
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = KnowledgeRetriever()
    return _retriever_instance
