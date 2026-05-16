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
import time
from typing import List, Optional

import chromadb
from cachetools import LRUCache
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.services.embedding_service import get_embedding_service

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
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self._client: Optional[chromadb.ClientAPI] = None
        self._collection: Optional[chromadb.Collection] = None

    def init_collection(self) -> None:
        """
        初始化ChromaDB集合

        创建或加载已有的向量数据库集合。
        使用余弦相似度作为距离度量。
        """
        try:
            # 确保持久化目录存在
            os.makedirs(self.persist_dir, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )

            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "description": "设备检修知识库"
                }
            )

            logger.info(f"ChromaDB集合初始化完成: {self.collection_name}")

        except Exception as e:
            logger.error(f"ChromaDB初始化失败: {e}", exc_info=True)
            raise RuntimeError(f"ChromaDB初始化失败: {e}")

    def _ensure_collection(self):
        """确保集合已初始化"""
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
        chunks: list,
        embeddings: Optional[List[List[float]]] = None,
        document_id: str = "",
        source_name: str = "",
        category: Optional[str] = None,
    ) -> int:
        """
        将文档分块和对应的向量添加到数据库

        如果未提供embeddings，则自动调用EmbeddingService生成。

        Args:
            chunks: 文本块列表（TextChunk对象或包含chunk_id/content等属性的对象）
            embeddings: 对应的向量列表（可选，不提供则自动生成）
            document_id: 文档ID
            source_name: 来源文档名
            category: 文档分类

        Returns:
            int: 成功添加的数量
        """
        self._ensure_collection()

        if not chunks:
            logger.warning("没有文本块需要添加")
            return 0

        # 提取文档内容和元数据
        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            chunk_id = getattr(chunk, "chunk_id", None) or f"chunk_{len(ids)}"
            content = getattr(chunk, "content", "")

            if not content or not content.strip():
                continue

            ids.append(chunk_id)
            documents.append(content)

            # 构建元数据
            metadata = {
                "document_id": document_id,
                "source": source_name,
                "page_number": getattr(chunk, "page_number", None),
                "category": category or "",
                "section_title": getattr(chunk, "section_title", "") or "",
                "chunk_type": getattr(chunk, "chunk_type", "text"),
            }

            # 合并chunk自带的metadata
            chunk_metadata = getattr(chunk, "metadata", None)
            if chunk_metadata and isinstance(chunk_metadata, dict):
                for key, value in chunk_metadata.items():
                    if value is not None and key not in metadata:
                        metadata[key] = value

            # ChromaDB的metadata值必须是str/int/float/bool类型
            cleaned_metadata = {}
            for k, v in metadata.items():
                if v is None:
                    continue
                if isinstance(v, (str, int, float, bool)):
                    cleaned_metadata[k] = v
                else:
                    cleaned_metadata[k] = str(v)

            metadatas.append(cleaned_metadata)

        if not documents:
            logger.warning("没有有效文本块需要添加")
            return 0

        # 生成embeddings（如果未提供）
        if embeddings is None:
            try:
                embedding_service = get_embedding_service()
                embeddings = embedding_service.embed_texts(documents)
                logger.info(f"已生成 {len(embeddings)} 个文本向量")
            except Exception as e:
                logger.error(f"生成Embedding失败: {e}", exc_info=True)
                raise RuntimeError(f"生成文本向量失败: {e}")

        # 批量添加到ChromaDB（每次最多500条，优化批量写入性能）
        batch_size = 500
        total_added = 0

        for i in range(0, len(documents), batch_size):
            batch_end = min(i + batch_size, len(documents))
            batch_ids = ids[i:batch_end]
            batch_docs = documents[i:batch_end]
            batch_embs = embeddings[i:batch_end]
            batch_metas = metadatas[i:batch_end]

            try:
                self._collection.add(
                    ids=batch_ids,
                    documents=batch_docs,
                    embeddings=batch_embs,
                    metadatas=batch_metas,
                )
                total_added += len(batch_ids)
                # 减少日志输出频率，仅在每批次或最后一批时输出
                if total_added == len(batch_ids) or batch_end >= len(documents):
                    logger.info(f"已添加文档块: 进度 {total_added}/{len(documents)}")
            except Exception as e:
                logger.error(f"添加批次 {i // batch_size + 1} 失败: {e}", exc_info=True)
                # 尝试逐条添加，跳过冲突的ID
                for j in range(len(batch_ids)):
                    try:
                        self._collection.add(
                            ids=[batch_ids[j]],
                            documents=[batch_docs[j]],
                            embeddings=[batch_embs[j]],
                            metadatas=[batch_metas[j]],
                        )
                        total_added += 1
                    except Exception as inner_e:
                        logger.warning(f"跳过重复或无效的chunk {batch_ids[j]}: {inner_e}")

        logger.info(f"已添加 {total_added} 个文档块到向量数据库")
        return total_added

    def search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        """
        语义检索：将查询文本转为向量，在数据库中查找相似内容

        支持查询结果缓存，相同查询在5分钟内直接返回缓存结果。

        Args:
            query: 查询文本
            top_k: 返回结果数量
            category: 分类筛选
            threshold: 相似度阈值

        Returns:
            List[SearchResult]: 检索结果列表
        """
        self._ensure_collection()
        threshold = threshold or settings.RETRIEVER_SCORE_THRESHOLD

        # 检查查询缓存
        cache_key = self._get_cache_key(query, top_k, category=category, threshold=threshold)
        if cache_key in _query_cache:
            cached_results, cached_time = _query_cache[cache_key]
            if time.time() - cached_time < CACHE_TTL:
                logger.info(f"命中查询缓存: query='{query[:30]}...'")
                return cached_results
            else:
                # 缓存过期，删除
                del _query_cache[cache_key]

        # 检查集合是否为空
        try:
            count = self._collection.count()
            if count == 0:
                logger.warning("向量数据库为空，无法检索")
                return []
        except Exception:
            pass

        # 生成查询向量
        try:
            embedding_service = get_embedding_service()
            query_embedding = embedding_service.embed_text(query)
        except Exception as e:
            logger.error(f"生成查询向量失败: {e}", exc_info=True)
            return []

        # 构建过滤条件
        where_filter = None
        if category:
            where_filter = {"category": category}

        # 在ChromaDB中检索
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self._collection.count()),
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            logger.error(f"ChromaDB查询失败: {e}", exc_info=True)
            return []

        # 转换为SearchResult列表
        search_results = []
        if results and results.get("ids"):
            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                document = results["documents"][0][i] if results.get("documents") else ""
                distance = results["distances"][0][i] if results.get("distances") else 1.0
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}

                # ChromaDB cosine距离转相似度分数：score = 1 - distance
                score = 1.0 - distance

                # 过滤低于阈值的结果
                if score < threshold:
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

        # 存入缓存
        _query_cache[cache_key] = (search_results, time.time())

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

        if not keywords:
            logger.warning("关键词列表为空")
            return []

        # 检查集合是否为空
        try:
            count = self._collection.count()
            if count == 0:
                logger.warning("向量数据库为空，无法检索")
                return []
        except Exception:
            pass

        try:
            if match_mode == "all":
                # 全部匹配：使用AND条件
                # ChromaDB的where_document只支持$contains操作
                # 对于all模式，需要获取所有文档后自行过滤
                all_results = []
                for keyword in keywords:
                    results = self._collection.get(
                        where_document={"$contains": keyword},
                        include=["documents", "metadatas"]
                    )
                    if results and results.get("ids"):
                        all_results.append(set(results["ids"]))

                # 取交集
                if all_results:
                    common_ids = set.intersection(*all_results)
                else:
                    common_ids = set()

                if not common_ids:
                    return []

                # 获取交集文档的完整信息
                final_results = self._collection.get(
                    ids=list(common_ids),
                    include=["documents", "metadatas"]
                )
            else:
                # 任一匹配：使用$contains操作
                # ChromaDB的where_document只支持单个关键词
                # 需要逐个查询后合并去重
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

                final_results = {
                    "ids": list(all_ids),
                    "documents": [all_documents[doc_id] for doc_id in all_ids],
                    "metadatas": [all_metadatas[doc_id] for doc_id in all_ids],
                }

            # 转换为SearchResult
            search_results = []
            if final_results and final_results.get("ids"):
                # 限制返回数量
                result_count = min(len(final_results["ids"]), top_k)
                for i in range(result_count):
                    doc_id = final_results["ids"][i]
                    document = final_results["documents"][i] if final_results.get("documents") else ""
                    meta = final_results["metadatas"][i] if final_results.get("metadatas") else {}

                    # 关键词匹配的分数基于匹配的关键词数量
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

            # 按匹配分数排序
            search_results.sort(key=lambda x: x.score, reverse=True)
            search_results = search_results[:top_k]

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

        使用加权倒数排名融合（Reciprocal Rank Fusion）算法
        合并两种检索的结果。

        Args:
            query: 查询文本
            keywords: 附加关键词（不提供则从query自动提取）
            top_k: 返回结果数量
            semantic_weight: 语义检索权重
            keyword_weight: 关键词检索权重

        Returns:
            List[SearchResult]: 融合后的检索结果
        """
        # 步骤1: 执行语义检索
        semantic_results = self.search(query, top_k=top_k * 2)

        # 步骤2: 执行关键词检索
        keyword_results = []
        if keywords:
            keyword_results = self.keyword_search(keywords, top_k=top_k * 2)
        else:
            # 从query中提取关键词
            extracted_keywords = self._extract_keywords(query)
            if extracted_keywords:
                keyword_results = self.keyword_search(extracted_keywords, top_k=top_k * 2)

        # 步骤3: 使用倒数排名融合算法合并结果
        fused_results = self._reciprocal_rank_fusion(
            semantic_results,
            keyword_results,
            semantic_weight,
            keyword_weight,
        )

        logger.info(f"混合检索完成: query='{query[:30]}...', 返回 {len(fused_results)} 条结果")
        return fused_results[:top_k]

    def _extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词

        使用简单的分词和停用词过滤策略。

        Args:
            text: 输入文本

        Returns:
            List[str]: 关键词列表
        """
        # 中文停用词
        stop_words = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
            "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
            "会", "着", "没有", "看", "好", "自己", "这", "他", "她", "它",
            "吗", "什么", "怎么", "如何", "为什么", "哪", "哪里", "哪些",
            "可以", "能", "应该", "需要", "请", "问", "求", "帮", "帮忙",
            "设备", "检修", "维护", "故障", "问题", "方法", "步骤", "操作",
        }

        # 简单分词：按空格和标点分割，过滤停用词和短词
        import re
        words = re.split(r'[\s,，。！？、；：“”‘’（）\[\]{}]+', text)
        keywords = []

        for word in words:
            word = word.strip()
            if not word:
                continue
            # 过滤停用词和过短的词
            if word in stop_words:
                continue
            if len(word) < 2:
                continue
            keywords.append(word)

        # 如果没有提取到关键词，返回整个查询
        if not keywords:
            # 取查询中最长的几个词
            words = text.split()
            keywords = [w for w in words if len(w) >= 2][:5]

        return keywords[:5]

    def _reciprocal_rank_fusion(
        self,
        results_a: List[SearchResult],
        results_b: List[SearchResult],
        weight_a: float,
        weight_b: float,
        k: int = 60,
    ) -> List[SearchResult]:
        """
        倒数排名融合算法（Reciprocal Rank Fusion）

        将两组检索结果按照排名进行加权融合，生成统一的排序结果。

        Args:
            results_a: 第一组检索结果（通常是语义检索）
            results_b: 第二组检索结果（通常是关键词检索）
            weight_a: 第一组权重
            weight_b: 第二组权重
            k: 平滑常数（默认60，防止高排名结果权重过大）

        Returns:
            List[SearchResult]: 融合后的结果（按融合分数降序排列）
        """
        if not results_a and not results_b:
            return []

        if not results_a:
            return results_b

        if not results_b:
            return results_a

        scores = {}

        # 计算第一组结果的RRF分数
        for rank, result in enumerate(results_a):
            doc_id = result.chunk_id
            rrf_score = weight_a / (k + rank + 1)
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score

        # 计算第二组结果的RRF分数
        for rank, result in enumerate(results_b):
            doc_id = result.chunk_id
            rrf_score = weight_b / (k + rank + 1)
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score

        # 构建去重后的结果映射
        all_results = {}
        for result in results_a:
            all_results[result.chunk_id] = result
        for result in results_b:
            if result.chunk_id not in all_results:
                all_results[result.chunk_id] = result

        # 按融合分数排序
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # 更新结果的分数为融合分数
        fused_results = []
        for doc_id in sorted_ids:
            result = all_results[doc_id]
            # 创建新的SearchResult，使用融合分数
            fused_result = SearchResult(
                chunk_id=result.chunk_id,
                content=result.content,
                source=result.source,
                score=scores[doc_id],
                page_number=result.page_number,
                category=result.category,
                metadata=result.metadata,
            )
            fused_results.append(fused_result)

        return fused_results

    def model_search(
        self,
        model_number: str,
        query: Optional[str] = None,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """
        设备型号检索：精确匹配设备型号，结合语义检索

        先通过metadata中的device_model字段精确过滤，
        再结合语义检索进行相关性排序。

        Args:
            model_number: 设备型号
            query: 附加查询条件
            top_k: 返回结果数量

        Returns:
            List[SearchResult]: 检索结果
        """
        self._ensure_collection()

        try:
            count = self._collection.count()
            if count == 0:
                logger.warning("向量数据库为空，无法检索")
                return []
        except Exception:
            pass

        # 构建查询文本
        if query:
            search_query = f"{model_number} {query}"
        else:
            search_query = model_number

        # 生成查询向量
        try:
            embedding_service = get_embedding_service()
            query_embedding = embedding_service.embed_text(search_query)
        except Exception as e:
            logger.error(f"生成查询向量失败: {e}", exc_info=True)
            return []

        # 使用metadata过滤设备型号
        # 尝试在metadata的多个字段中匹配设备型号
        where_filter = {
            "$or": [
                {"device_model": model_number},
                {"chapter": model_number},
                {"source": {"$contains": model_number}},
            ]
        }

        try:
            # 先尝试带metadata过滤的语义检索
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, max(count, 1)),
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            logger.debug(f"metadata过滤检索失败，降级为纯语义检索: {e}")
            # 降级：不带过滤的语义检索
            try:
                results = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k * 2, max(count, 1)),
                    include=["documents", "metadatas", "distances"]
                )
            except Exception as inner_e:
                logger.error(f"语义检索也失败: {inner_e}", exc_info=True)
                return []

        # 转换为SearchResult
        search_results = []
        if results and results.get("ids"):
            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                document = results["documents"][0][i] if results.get("documents") else ""
                distance = results["distances"][0][i] if results.get("distances") else 1.0
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}

                score = 1.0 - distance

                # 如果是降级检索，额外检查文档中是否包含设备型号
                if model_number not in document and model_number not in str(meta):
                    score *= 0.5  # 降低不相关结果的分数

                search_results.append(SearchResult(
                    chunk_id=doc_id,
                    content=document,
                    source=meta.get("source", ""),
                    score=score,
                    page_number=meta.get("page_number"),
                    category=meta.get("category"),
                    metadata=meta,
                ))

        # 按分数排序
        search_results.sort(key=lambda x: x.score, reverse=True)
        search_results = search_results[:top_k]

        logger.info(f"设备型号检索完成: model={model_number}, 返回 {len(search_results)} 条结果")
        return search_results

    def delete_collection(self) -> bool:
        """
        删除当前集合

        Returns:
            bool: 是否删除成功
        """
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
        """
        删除指定文档的所有向量数据

        Args:
            document_id: 文档ID

        Returns:
            int: 删除的记录数
        """
        self._ensure_collection()

        try:
            # 先查询该文档的所有记录数量
            existing = self._collection.get(
                where={"document_id": document_id},
                include=[]
            )
            count = len(existing.get("ids", [])) if existing else 0

            if count == 0:
                logger.info(f"文档 {document_id} 没有找到关联的向量数据")
                return 0

            # 删除该文档的所有记录
            self._collection.delete(
                where={"document_id": document_id}
            )

            logger.info(f"已删除文档 {document_id} 的 {count} 条向量数据")
            return count

        except Exception as e:
            logger.error(f"删除文档向量数据失败: {e}", exc_info=True)
            return 0

    def get_collection_stats(self) -> dict:
        """
        获取集合统计信息

        Returns:
            dict: 包含集合名称、文档数量等统计信息
        """
        self._ensure_collection()

        try:
            count = self._collection.count()
            return {
                "collection_name": self.collection_name,
                "total_chunks": count,
                "persist_dir": self.persist_dir,
                "status": "active",
            }
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {e}", exc_info=True)
            return {
                "collection_name": self.collection_name,
                "total_chunks": 0,
                "persist_dir": self.persist_dir,
                "status": "error",
                "error": str(e),
            }

    def rebuild_index(self) -> dict:
        """
        重建向量索引

        从数据库读取所有文档，重新解析和分块，
        重新生成Embedding，重新写入ChromaDB。

        Returns:
            dict: 重建进度信息
        """
        try:
            # 获取当前集合中的所有数据
            self._ensure_collection()
            existing = self._collection.get(include=["documents", "metadatas"])

            if not existing or not existing.get("ids"):
                return {"status": "completed", "total_chunks": 0, "message": "集合为空，无需重建"}

            # 删除旧集合并重新创建
            old_ids = existing["ids"]
            old_documents = existing.get("documents", [])
            old_metadatas = existing.get("metadatas", [])

            # 删除旧数据
            self._collection.delete(ids=old_ids)

            # 重新生成Embedding
            embedding_service = get_embedding_service()
            new_embeddings = embedding_service.embed_texts(old_documents)

            # 重新添加
            self._collection.add(
                ids=old_ids,
                documents=old_documents,
                embeddings=new_embeddings,
                metadatas=old_metadatas,
            )

            return {
                "status": "completed",
                "total_chunks": len(old_ids),
                "message": f"索引重建完成，共处理 {len(old_ids)} 个文本块",
            }

        except Exception as e:
            logger.error(f"索引重建失败: {e}", exc_info=True)
            return {
                "status": "failed",
                "total_chunks": 0,
                "error": str(e),
            }


# ========== 兼容旧接口 ==========

class Retriever(KnowledgeRetriever):
    """
    知识检索引擎（兼容旧接口）

    继承自KnowledgeRetriever，保持向后兼容。
    """

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        super().__init__(persist_dir, collection_name)

    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        threshold: Optional[float] = None,
    ) -> List[SearchResult]:
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
