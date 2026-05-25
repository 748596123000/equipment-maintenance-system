"""
知识检索引擎模块

基于ChromaDB实现多种检索模式：
- 语义检索：通过Embedding向量进行相似度匹配
- 关键词检索：基于ChromaDB的where_document过滤
- 混合检索：融合语义和关键词检索结果（加权倒数排名融合）
- 设备型号检索：针对设备型号的精确匹配（metadata过滤）

使用 app.services.embedding_service.py 中的 EmbeddingService 进行向量化。
ChromaDB使用持久化存储（persist_directory从config读取）。
"""

import hashlib
import logging
import os
import re
import time
from typing import List, Optional

from cachetools import LRUCache

logger = logging.getLogger(__name__)

_query_cache: LRUCache = LRUCache(maxsize=1000)
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
        """转换为字典格式"""
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
    知识检索引擎

    封装ChromaDB向量数据库，提供多种检索模式。
    支持文档的增删改查和相似度检索。

    Attributes:
        persist_dir: ChromaDB持久化目录
        collection_name: 集合名称
    """

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        """
        初始化检索引擎

        Args:
            persist_dir: ChromaDB持久化目录
            collection_name: 集合名称
        """
        self.persist_dir = persist_dir
        self.collection_name = collection_name or "knowledge_base"
        self._client = None
        self._collection = None

    def init_collection(self) -> None:
        """初始化ChromaDB集合"""
        try:
            import chromadb
            from app.config import settings
            from app.services.embedding_service import get_embedding_service

            # 使用传入的值或从配置获取
            persist_dir = self.persist_dir or getattr(settings, 'CHROMA_PERSIST_DIR', './data/chroma_db')
            collection_name = self.collection_name

            os.makedirs(persist_dir, exist_ok=True)

            # ChromaDB 1.x 最新API（兼容所有版本）
            self._client = chromadb.PersistentClient(path=persist_dir)

            # 尝试获取或创建集合
            try:
                self._collection = self._client.get_or_create_collection(name=collection_name)
            except Exception:
                # 如果集合已存在，直接获取
                self._collection = self._client.get_collection(name=collection_name)

            logger.info(f"ChromaDB集合初始化完成: {collection_name}")

        except ImportError as e:
            logger.warning(f"ChromaDB未安装，跳过初始化: {e}")
            self._client = None
            self._collection = None
        except Exception as e:
            logger.error(f"ChromaDB初始化失败: {e}", exc_info=True)
            # 不抛出异常，允许系统继续运行
            self._client = None
            self._collection = None

    def _ensure_collection(self):
        """确保集合已初始化（懒加载）"""
        if self._collection is None:
            self.init_collection()

    def _get_cache_key(self, query: str, top_k: int, **kwargs) -> str:
        """生成缓存key"""
        key_str = f"{query}_{top_k}_{sorted(kwargs.items())}"
        return hashlib.md5(key_str.encode()).hexdigest()

    @staticmethod
    def clear_query_cache():
        """清空查询缓存"""
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
        批量添加文档到向量数据库

        Args:
            documents: 文档内容列表
            embeddings: 文档向量列表
            metadatas: 文档元数据列表
            ids: 文档ID列表（可选，不传则自动生成）

        Returns:
            bool: 是否添加成功
        """
        self._ensure_collection()

        if not documents or not embeddings:
            logger.warning("文档或向量为空，跳过添加")
            return False

        if len(documents) != len(embeddings) or len(documents) != len(metadatas):
            logger.error("文档、向量和元数据长度不一致")
            return False

        # 生成文档ID
        if ids is None:
            ids = [f"chunk_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}" for i in range(len(documents))]

        try:
            if self._collection is None:
                logger.error("ChromaDB集合未初始化")
                return False

            # 分批添加，避免单次请求过大
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch_end = min(i + batch_size, len(documents))
                self._collection.add(
                    ids=ids[i:batch_end],
                    documents=documents[i:batch_end],
                    embeddings=embeddings[i:batch_end],
                    metadatas=metadatas[i:batch_end],
                )
                logger.debug(f"已添加批次 {i//batch_size + 1}: {batch_end - i} 条记录")

            logger.info(f"成功添加 {len(documents)} 条文档到向量数据库")
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
        语义检索：通过查询向量进行相似度匹配

        Args:
            query: 查询文本
            top_k: 返回结果数量
            category: 类别过滤（可选）
            threshold: 相似度阈值（可选，0-1之间）

        Returns:
            List[SearchResult]: 检索结果列表
        """
        self._ensure_collection()

        if self._collection is None:
            logger.warning("ChromaDB未初始化，返回空结果")
            return []

        # 检查缓存
        cache_key = self._get_cache_key(query, top_k, category=category, threshold=threshold)
        cached_result = _query_cache.get(cache_key)
        if cached_result:
            logger.debug(f"缓存命中: {query[:30]}...")
            return cached_result

        # 生成查询向量
        try:
            from app.services.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            query_embedding = embedding_service.embed_text(query)
        except Exception as e:
            logger.error(f"生成查询向量失败: {e}", exc_info=True)
            return []

        # 执行检索
        try:
            count = self._collection.count()
            if count == 0:
                logger.warning("向量数据库为空，无法检索")
                return []

            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, max(count, 1)),
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            logger.error(f"向量检索失败: {e}", exc_info=True)
            return []

        # 转换为SearchResult
        search_results = []
        if results and results.get("ids"):
            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                document = results["documents"][0][i] if results.get("documents") else ""
                distance = results["distances"][0][i] if results.get("distances") else 1.0
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}

                # 距离转换为相似度分数 (0-1)
                score = 1.0 - distance

                # 应用阈值过滤
                if threshold is not None and score < threshold:
                    continue

                search_results.append(SearchResult(
                    chunk_id=doc_id,
                    content=document,
                    source=meta.get("source", ""),
                    score=score,
                    page_number=meta.get("page_number"),
                    category=meta.get("category"),
                    metadata=meta,
                ))

        # 缓存结果
        _query_cache[cache_key] = search_results

        logger.info(f"语义检索完成: query='{query[:30]}...', 返回 {len(search_results)} 条结果")
        return search_results

    def keyword_search(
        self,
        keywords: List[str],
        top_k: int = 5,
        match_mode: str = "any",
    ) -> List[SearchResult]:
        """
        关键词检索：基于ChromaDB的where_document过滤

        Args:
            keywords: 关键词列表
            top_k: 返回结果数量
            match_mode: 匹配模式 (any: 任一匹配 / all: 全部匹配)

        Returns:
            List[SearchResult]: 检索结果列表
        """
        self._ensure_collection()

        if self._collection is None:
            return []

        if not keywords:
            logger.warning("关键词列表为空")
            return []

        try:
            all_ids = set()
            all_documents = {}
            all_metadatas = {}

            for keyword in keywords:
                results = self._collection.get(
                    where_document={"$contains": keyword},
                    include=["documents", "metadatas"]
                )
                if results and results.get("ids"):
                    for j, doc_id in enumerate(results["ids"]):
                        if doc_id not in all_ids:
                            all_ids.add(doc_id)
                            all_documents[doc_id] = results["documents"][j] if results.get("documents") else ""
                            all_metadatas[doc_id] = results["metadatas"][j] if results.get("metadatas") else {}

            if not all_ids:
                return []

            # 转换为SearchResult
            search_results = []
            result_count = min(len(all_ids), top_k)
            ids_list = list(all_ids)

            for i in range(result_count):
                doc_id = ids_list[i]
                document = all_documents.get(doc_id, "")
                meta = all_metadatas.get(doc_id, {})

                matched_count = sum(1 for kw in keywords if kw in document)
                score = matched_count / len(keywords) if keywords else 0.0

                search_results.append(SearchResult(
                    chunk_id=doc_id,
                    content=document,
                    source=meta.get("source", ""),
                    score=score,
                    page_number=meta.get("page_number"),
                    category=meta.get("category"),
                    metadata=meta,
                ))

            search_results.sort(key=lambda x: x.score, reverse=True)
            logger.info(f"关键词检索完成: keywords={keywords}, 返回 {len(search_results)} 条结果")
            return search_results

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
        """
        混合检索：融合语义检索和关键词检索结果
        """
        semantic_results = self.search(query, top_k=top_k * 2)
        keyword_results = []

        if keywords:
            keyword_results = self.keyword_search(keywords, top_k=top_k * 2)
        else:
            extracted_keywords = self._extract_keywords(query)
            if extracted_keywords:
                keyword_results = self.keyword_search(extracted_keywords, top_k=top_k * 2)

        # RRF融合
        return self._reciprocal_rank_fusion(semantic_results, keyword_results, semantic_weight, keyword_weight)[:top_k]

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
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
        """倒数排名融合算法"""
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
        """设备型号检索"""
        return self.search(f"{model_number} {query or ''}", top_k=top_k)

    def delete_collection(self) -> bool:
        """删除当前集合"""
        try:
            if self._client is not None and self.collection_name:
                self._client.delete_collection(name=self.collection_name)
                self._collection = None
                logger.info(f"已删除集合: {self.collection_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除集合失败: {e}", exc_info=True)
            return False

    def delete_by_document_id(self, document_id: str) -> int:
        """删除指定文档的所有向量数据"""
        self._ensure_collection()
        if self._collection is None:
            return 0

        try:
            existing = self._collection.get(where={"document_id": document_id}, include=[])
            count = len(existing.get("ids", [])) if existing else 0

            if count > 0:
                self._collection.delete(where={"document_id": document_id})
                logger.info(f"已删除文档 {document_id} 的 {count} 条向量数据")

            return count
        except Exception as e:
            logger.error(f"删除文档向量数据失败: {e}", exc_info=True)
            return 0

    def get_collection_stats(self) -> dict:
        """获取集合统计信息"""
        self._ensure_collection()

        try:
            if self._collection is None:
                return {"collection_name": self.collection_name, "total_chunks": 0, "status": "inactive"}

            count = self._collection.count()
            return {
                "collection_name": self.collection_name,
                "total_chunks": count,
                "persist_dir": self.persist_dir,
                "status": "active",
            }
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {e}", exc_info=True)
            return {"collection_name": self.collection_name, "total_chunks": 0, "status": "error"}

    def rebuild_index(self) -> dict:
        """重建向量索引"""
        try:
            self._ensure_collection()
            if self._collection is None:
                return {"status": "failed", "message": "ChromaDB未初始化"}

            existing = self._collection.get(include=["documents", "metadatas"])

            if not existing or not existing.get("ids"):
                return {"status": "completed", "total_chunks": 0, "message": "集合为空"}

            old_ids = existing["ids"]
            old_documents = existing.get("documents", [])
            old_metadatas = existing.get("metadatas", [])

            self._collection.delete(ids=old_ids)

            from app.services.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            new_embeddings = embedding_service.embed_texts(old_documents)

            self._collection.add(ids=old_ids, documents=old_documents, embeddings=new_embeddings, metadatas=old_metadatas)

            return {"status": "completed", "total_chunks": len(old_ids)}
        except Exception as e:
            logger.error(f"索引重建失败: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}


# ========== 兼容旧接口 ==========

class Retriever(KnowledgeRetriever):
    """知识检索引擎（兼容旧接口）"""

    def semantic_search(self, query: str, top_k: int = 5, category: Optional[str] = None, threshold: Optional[float] = None) -> List[SearchResult]:
        """语义检索（兼容旧接口）"""
        return self.search(query, top_k, category, threshold)


# 全局检索引擎单例
_retriever_instance: Optional[KnowledgeRetriever] = None


def get_retriever() -> KnowledgeRetriever:
    """获取全局检索引擎实例"""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = KnowledgeRetriever()
    return _retriever_instance
