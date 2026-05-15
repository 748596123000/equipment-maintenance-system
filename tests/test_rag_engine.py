"""
RAG引擎模块测试

测试RAGEngine类的各项功能：
- 上下文构建
- 消息列表构建
- 置信度计算
- 回答生成
- 流式生成
- 完整RAG流程
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.core.rag_engine import RAGEngine


class TestRAGEngine:
    """RAG引擎测试类"""

    @pytest.fixture
    def rag_engine(self):
        """创建RAG引擎实例"""
        return RAGEngine(
            max_context_length=2048,
            max_history_turns=3,
        )

    def test_rag_engine_init(self, rag_engine):
        """测试RAG引擎初始化"""
        assert rag_engine.max_context_length == 2048
        assert rag_engine.max_history_turns == 3

    def test_build_context_empty(self, rag_engine):
        """测试空检索结果的上下文构建"""
        context = rag_engine._build_context([])
        assert "未找到相关知识" in context

    def test_build_context_with_results(self, rag_engine):
        """测试有检索结果的上下文构建"""
        search_results = [
            {
                "source": "变压器检修手册.pdf",
                "content": "变压器绕组绝缘电阻测量方法...",
                "page_number": 12,
                "score": 0.95,
            },
            {
                "source": "电气安全规程.pdf",
                "content": "高压设备操作安全注意事项...",
                "page_number": 5,
                "score": 0.85,
            },
        ]

        context = rag_engine._build_context(search_results)
        assert "变压器检修手册.pdf" in context
        assert "电气安全规程.pdf" in context
        assert "第12页" in context

    def test_build_context_truncation(self, rag_engine):
        """测试上下文截断"""
        # 创建超长的检索结果
        long_results = [
            {
                "source": f"文档{i}.pdf",
                "content": "内容" * 1000,
                "page_number": i,
                "score": 0.9,
            }
            for i in range(100)
        ]

        context = rag_engine._build_context(long_results)
        # 上下文应该被截断
        assert len(context) <= rag_engine.max_context_length * 1.5  # 允许一些余量

    def test_build_messages_without_history(self, rag_engine):
        """测试无历史对话的消息构建"""
        messages = rag_engine._build_messages(
            question="变压器检修方法",
            context="变压器检修知识上下文",
        )

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "变压器检修知识上下文" in messages[0]["content"]

    def test_build_messages_with_history(self, rag_engine):
        """测试有历史对话的消息构建"""
        history = [
            {"role": "user", "content": "什么是变压器？"},
            {"role": "assistant", "content": "变压器是..."},
            {"role": "user", "content": "它有哪些类型？"},
            {"role": "assistant", "content": "主要有..."},
            {"role": "user", "content": "多余的会被截断"},
            {"role": "assistant", "content": "是的"},
        ]

        messages = rag_engine._build_messages(
            question="变压器检修方法",
            context="上下文",
            chat_history=history,
        )

        # max_history_turns=3，所以最多保留6条历史消息
        # system + 6条历史 + 1条用户 = 8条
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "变压器检修方法"

    def test_calculate_confidence_no_results(self, rag_engine):
        """测试无检索结果时的置信度"""
        confidence = rag_engine._calculate_confidence([], "这是一个回答")
        assert confidence < 0.5

    def test_calculate_confidence_with_results(self, rag_engine):
        """测试有检索结果时的置信度"""
        results = [
            {"score": 0.95},
        ]
        confidence = rag_engine._calculate_confidence(results, "这是一个详细的回答内容" * 20)
        assert confidence > 0.5

    def test_calculate_confidence_unsure_response(self, rag_engine):
        """测试不确定回答的置信度"""
        results = [
            {"score": 0.8},
        ]
        confidence = rag_engine._calculate_confidence(results, "抱歉，知识库中没有相关信息")
        assert confidence < 0.5

    @pytest.mark.asyncio
    async def test_generate(self, rag_engine):
        """测试回答生成"""
        answer, confidence = await rag_engine.generate(
            question="变压器检修方法",
            context="测试上下文",
        )
        assert isinstance(answer, str)
        assert isinstance(confidence, float)

    @pytest.mark.asyncio
    async def test_stream_generate(self, rag_engine):
        """测试流式生成"""
        chunks = []
        async for chunk in rag_engine.stream_generate(
            question="变压器检修方法",
            context="测试上下文",
        ):
            chunks.append(chunk)

        assert isinstance(chunks, list)

    @pytest.mark.asyncio
    async def test_chat(self, rag_engine):
        """测试完整RAG流程"""
        search_results = [
            {
                "source": "测试文档.pdf",
                "content": "测试内容" * 50,
                "score": 0.9,
                "page_number": 1,
            }
        ]

        result = await rag_engine.chat(
            question="测试问题",
            search_results=search_results,
        )

        assert "answer" in result
        assert "confidence" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)


class TestRAGEngineSingleton:
    """RAG引擎单例测试"""

    def test_get_rag_engine(self):
        """测试获取全局RAG引擎实例"""
        from app.core.rag_engine import get_rag_engine

        engine = get_rag_engine()
        assert engine is not None
        assert isinstance(engine, RAGEngine)

    def test_get_rag_engine_singleton(self):
        """测试单例模式"""
        from app.core.rag_engine import get_rag_engine

        engine1 = get_rag_engine()
        engine2 = get_rag_engine()
        assert engine1 is engine2
