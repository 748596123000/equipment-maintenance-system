"""
检索引擎模块测试

测试Retriever类的各项功能：
- 初始化和集合创建
- 语义检索
- 关键词检索
- 混合检索
- 文档添加和删除
- 关键词提取
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.core.retriever import Retriever, SearchResult


class TestSearchResult:
    """SearchResult测试类"""

    def test_search_result_creation(self):
        """测试SearchResult创建"""
        result = SearchResult(
            chunk_id="chunk_001",
            content="变压器绕组绝缘电阻测量方法",
            source="变压器检修手册.pdf",
            score=0.95,
            page_number=12,
            category="变压器",
        )
        assert result.chunk_id == "chunk_001"
        assert result.score == 0.95
        assert result.page_number == 12

    def test_search_result_to_dict(self):
        """测试SearchResult转字典"""
        result = SearchResult(
            chunk_id="chunk_001",
            content="测试内容",
            source="测试来源",
            score=0.85,
        )
        d = result.to_dict()
        assert d["chunk_id"] == "chunk_001"
        assert d["content"] == "测试内容"
        assert d["score"] == 0.85
        assert "source" in d


class TestRetriever:
    """检索引擎测试类"""

    @pytest.fixture
    def retriever(self):
        """创建检索器实例"""
        return Retriever(
            persist_dir="./test_chroma_db",
            collection_name="test_collection",
        )

    def test_retriever_init(self, retriever):
        """测试检索器初始化"""
        assert retriever.persist_dir == "./test_chroma_db"
        assert retriever.collection_name == "test_collection"
        assert retriever._collection is None

    def test_extract_keywords(self, retriever):
        """测试关键词提取"""
        text = "变压器绕组绝缘电阻测量"
        keywords = retriever._extract_keywords(text)
        assert isinstance(keywords, list)
        assert len(keywords) > 0

    def test_extract_keywords_empty(self, retriever):
        """测试空文本关键词提取"""
        keywords = retriever._extract_keywords("")
        assert keywords == []

    def test_reciprocal_rank_fusion(self, retriever):
        """测试倒数排名融合算法"""
        results_a = [
            SearchResult("id1", "内容1", "来源1", 0.9),
            SearchResult("id2", "内容2", "来源2", 0.8),
            SearchResult("id3", "内容3", "来源3", 0.7),
        ]
        results_b = [
            SearchResult("id2", "内容2", "来源2", 0.85),
            SearchResult("id3", "内容3", "来源3", 0.75),
            SearchResult("id4", "内容4", "来源4", 0.65),
        ]

        fused = retriever._reciprocal_rank_fusion(
            results_a, results_b,
            weight_a=0.7, weight_b=0.3,
        )

        assert isinstance(fused, list)
        # id2和id3在两个列表中都出现，应该排在前面
        fused_ids = [r.chunk_id for r in fused]
        assert "id2" in fused_ids
        assert "id3" in fused_ids

    def test_reciprocal_rank_fusion_empty(self, retriever):
        """测试空结果的倒数排名融合"""
        fused = retriever._reciprocal_rank_fusion([], [], 0.7, 0.3)
        assert fused == []

    @pytest.mark.asyncio
    async def test_semantic_search(self, retriever):
        """测试语义检索"""
        # Mock ChromaDB集合
        retriever._collection = MagicMock()

        results = await retriever.semantic_search("变压器检修", top_k=5)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_keyword_search(self, retriever):
        """测试关键词检索"""
        retriever._collection = MagicMock()

        results = await retriever.keyword_search(["变压器", "绝缘"], top_k=5)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_hybrid_search(self, retriever):
        """测试混合检索"""
        retriever._collection = MagicMock()

        results = await retriever.hybrid_search(
            query="变压器检修方法",
            top_k=5,
        )
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_model_search(self, retriever):
        """测试设备型号检索"""
        retriever._collection = MagicMock()

        results = await retriever.model_search(
            model_number="S11-630/10",
            top_k=5,
        )
        assert isinstance(results, list)

    def test_delete_by_document_id(self, retriever):
        """测试按文档ID删除"""
        retriever._collection = MagicMock()

        count = retriever.delete_by_document_id("doc_001")
        assert count == 0


class TestRetrieverSingleton:
    """检索引擎单例测试"""

    def test_get_retriever(self):
        """测试获取全局检索引擎实例"""
        from app.core.retriever import get_retriever, _retriever_instance

        retriever = get_retriever()
        assert retriever is not None
        assert isinstance(retriever, Retriever)
