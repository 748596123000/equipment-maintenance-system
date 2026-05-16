"""
RAG检索增强生成引擎模块

实现完整的RAG流程：
1. 接收用户问题
2. 从知识库检索相关文档片段
3. 构建包含上下文的Prompt
4. 调用大语言模型生成回答
5. 返回回答及引用来源

支持流式和非流式两种生成模式。
"""

import logging
from difflib import SequenceMatcher
from typing import Dict, Generator, List, Optional

from cachetools import LRUCache

from app.config import settings
from app.services.llm_service import get_llm_service
from app.core.retriever import get_retriever, KnowledgeRetriever

logger = logging.getLogger(__name__)

_last_results: LRUCache = LRUCache(maxsize=100)
SIMILARITY_THRESHOLD = 0.8


class RAGEngine:
    """
    RAG检索增强生成引擎

    整合检索引擎和大模型服务，实现端到端的知识问答。
    支持多轮对话上下文管理。

    Attributes:
        retriever: 知识检索引擎实例
        llm_service: 大语言模型服务实例
        max_context_length: 最大上下文长度（字符数）
        max_history_turns: 最大历史对话轮数
    """

    # 系统提示词模板
    SYSTEM_PROMPT = """你是一个设备检修知识库的AI教学助手。你的任务是：
1. 基于知识库中的设备检修手册和技术文档，准确回答用户的检修问题
2. 帮助零基础用户理解设备检修知识，用通俗易懂的语言解释专业术语
3. 提供详细的操作步骤和安全注意事项
4. 如果知识库中没有相关信息，请明确告知用户，并建议可能的相关检索方向

回答要求：
1. 仅基于提供的知识库内容回答，不要编造信息
2. 如果知识库中没有相关信息，请明确告知用户"知识库中未找到相关信息"
3. 回答要专业、准确、条理清晰
4. 如果涉及安全操作，务必强调安全注意事项
5. 引用知识来源时，标注来源文档名称和页码
6. 对于设备型号、参数等关键信息，确保准确引用
7. 用通俗易懂的语言解释专业术语，帮助零基础用户理解

当前提供的知识内容：
{context}
"""

    def __init__(
        self,
        retriever: Optional[KnowledgeRetriever] = None,
        max_context_length: int = 4096,
        max_history_turns: int = 5,
    ):
        """
        初始化RAG引擎

        Args:
            retriever: 知识检索引擎实例（不提供则使用全局单例）
            max_context_length: 最大上下文长度（字符数）
            max_history_turns: 最大历史对话轮数
        """
        self.retriever = retriever or get_retriever()
        self.llm_service = get_llm_service()
        self.max_context_length = max_context_length
        self.max_history_turns = max_history_turns

    def _similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（基于序列匹配）

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            float: 相似度分数 (0.0-1.0)
        """
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1, text2).ratio()

    def query(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        search_mode: str = "hybrid",
        top_k: Optional[int] = None,
    ) -> Dict:
        """
        主入口：接收用户问题，返回答案和来源

        完整的RAG问答流程：
        1. 检索相关文档（支持相似问题缓存复用）
        2. 构建上下文
        3. 生成回答
        4. 格式化来源引用

        Args:
            question: 用户问题
            chat_history: 对话历史
            search_mode: 检索模式 (semantic/keyword/hybrid)
            top_k: 检索结果数量

        Returns:
            dict: 包含 answer, confidence, sources 的字典
        """
        global _last_results

        cached_result = None
        for cached_query in _last_results:
            if self._similarity(question, cached_query) > SIMILARITY_THRESHOLD:
                cached_result = _last_results[cached_query]
                break

        if cached_result is not None:
            logger.info(f"问题相似度 > {SIMILARITY_THRESHOLD}，复用上次检索结果")
            search_results = cached_result
        else:
            search_results = self._retrieve(question, search_mode, top_k)
            _last_results[question] = search_results

        # 步骤2: 构建上下文
        context = self._build_context(search_results)

        # 步骤3: 构建消息
        messages = self._build_prompt(question, context, chat_history)

        # 步骤4: 调用LLM生成回答
        answer = self._generate(messages)

        # 步骤5: 计算置信度
        confidence = self._calculate_confidence(search_results, answer)

        # 步骤6: 格式化来源引用
        sources = self._format_sources(search_results)

        logger.info(f"RAG问答完成: question='{question[:30]}...', confidence={confidence:.2f}")

        return {
            "answer": answer,
            "confidence": confidence,
            "sources": sources,
        }

    def stream_query(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        search_mode: str = "hybrid",
        top_k: Optional[int] = None,
    ) -> Generator[Dict, None, None]:
        """
        流式RAG问答

        先检索文档，然后流式生成回答。
        首先yield来源信息，然后逐步yield回答内容。

        Args:
            question: 用户问题
            chat_history: 对话历史
            search_mode: 检索模式
            top_k: 检索结果数量

        Yields:
            dict: 包含 type 和 content 的字典
                type="sources": 来源信息
                type="answer": 回答内容片段
                type="done": 完成信号
        """
        # 检索相关文档
        search_results = self._retrieve(question, search_mode, top_k)

        # 构建上下文
        context = self._build_context(search_results)

        # 先yield来源信息
        sources = self._format_sources(search_results)
        yield {"type": "sources", "content": sources}

        # 构建消息
        messages = self._build_prompt(question, context, chat_history)

        # 流式生成回答
        try:
            for chunk in self.llm_service.stream_chat(messages):
                yield {"type": "answer", "content": chunk}
        except Exception as e:
            logger.error(f"流式生成失败: {e}", exc_info=True)
            yield {"type": "answer", "content": f"抱歉，生成回答时出现错误: {str(e)}"}

        yield {"type": "done", "content": ""}

    def _retrieve(
        self,
        question: str,
        search_mode: str = "hybrid",
        top_k: Optional[int] = None,
    ) -> List[Dict]:
        """
        检索相关文档

        Args:
            question: 用户问题
            search_mode: 检索模式
            top_k: 返回结果数量

        Returns:
            List[Dict]: 检索结果列表（字典格式）
        """
        top_k = top_k or settings.TOP_K_RESULTS  # 默认5，减少LLM上下文长度

        try:
            if search_mode == "semantic":
                results = self.retriever.search(question, top_k=top_k)
            elif search_mode == "keyword":
                # 从问题中提取关键词
                keywords = self.retriever._extract_keywords(question)
                results = self.retriever.keyword_search(keywords, top_k=top_k)
            elif search_mode == "hybrid":
                results = self.retriever.hybrid_search(question, top_k=top_k)
            else:
                logger.warning(f"不支持的检索模式: {search_mode}，使用hybrid")
                results = self.retriever.hybrid_search(question, top_k=top_k)

            # 转换为字典格式
            return [r.to_dict() for r in results]

        except Exception as e:
            logger.error(f"检索失败: {e}", exc_info=True)
            return []

    def _build_context(self, search_results: List[Dict]) -> str:
        """
        从检索结果构建上下文文本

        将检索到的文档片段格式化为LLM可理解的上下文。

        Args:
            search_results: 检索结果列表

        Returns:
            str: 格式化的上下文文本
        """
        if not search_results:
            return "（未找到相关知识）"

        context_parts = []
        total_length = 0

        for i, result in enumerate(search_results, 1):
            source = result.get("source", "未知来源")
            content = result.get("content", "")
            page = result.get("page_number", "")

            part = f"[{i}] 来源: {source}"
            if page:
                part += f" (第{page}页)"
            part += f"\n{content}\n"

            # 控制上下文总长度
            if total_length + len(part) > self.max_context_length:
                context_parts.append("\n... (更多内容已省略)")
                break

            context_parts.append(part)
            total_length += len(part)

        return "\n".join(context_parts)

    def _build_prompt(
        self,
        question: str,
        context: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        """
        构建RAG提示词

        组合系统提示、检索上下文、对话历史和用户问题。

        Args:
            question: 用户问题
            context: 知识库上下文
            chat_history: 对话历史

        Returns:
            List[Dict[str, str]]: 消息列表
        """
        messages = []

        # 系统提示词
        system_prompt = self.SYSTEM_PROMPT.format(context=context)
        messages.append({"role": "system", "content": system_prompt})

        # 对话历史（限制轮数）
        if chat_history:
            history = chat_history[-self.max_history_turns * 2:]
            messages.extend(history)

        # 用户问题
        messages.append({"role": "user", "content": question})

        return messages

    def _generate(self, messages: List[Dict[str, str]]) -> str:
        """
        调用LLM生成回答

        Args:
            messages: 消息列表

        Returns:
            str: 生成的回答文本
        """
        try:
            answer = self.llm_service.chat(messages)
            return answer
        except Exception as e:
            logger.error(f"LLM生成失败: {e}", exc_info=True)
            return f"抱歉，生成回答时出现错误: {str(e)}"

    def _calculate_confidence(
        self,
        search_results: List[Dict],
        answer: str,
    ) -> float:
        """
        计算回答的置信度分数

        基于检索结果的相关性和回答质量综合评估。

        Args:
            search_results: 检索结果
            answer: 生成的回答

        Returns:
            float: 置信度分数 (0.0-1.0)
        """
        if not search_results:
            return 0.1

        # 基于最高检索分数
        top_score = search_results[0].get("score", 0) if search_results else 0

        # 基于回答长度（过短可能表示无法回答）
        answer_length_factor = min(len(answer) / 200, 1.0)

        # 检查是否有"不知道"等表示
        unsure_keywords = ["不知道", "无法确定", "没有相关信息", "知识库中未找到", "无法回答"]
        unsure_penalty = 0.0
        for keyword in unsure_keywords:
            if keyword in answer:
                unsure_penalty = 0.3
                break

        # 综合计算置信度
        confidence = (top_score * 0.6 + answer_length_factor * 0.4) - unsure_penalty
        return max(0.0, min(1.0, confidence))

    def _format_sources(self, search_results: List[Dict]) -> List[Dict]:
        """
        格式化来源引用

        将检索结果格式化为可展示的来源信息。

        Args:
            search_results: 检索结果列表

        Returns:
            List[Dict]: 格式化的来源列表
        """
        sources = []
        seen_sources = set()

        for result in search_results[:5]:
            source = result.get("source", "")
            content = result.get("content", "")
            score = result.get("score", 0)
            page = result.get("page_number")

            # 去重
            source_key = f"{source}_p{page}"
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)

            sources.append({
                "source": source,
                "content": content[:200] + "..." if len(content) > 200 else content,
                "score": round(score, 4),
                "page_number": page,
            })

        return sources

    # ========== 兼容旧接口 ==========

    def _build_messages(
        self,
        question: str,
        context: str,
        chat_history: Optional[List[dict]] = None,
    ) -> List[dict]:
        """构建消息列表（兼容旧接口）"""
        return self._build_prompt(question, context, chat_history)

    def generate(
        self,
        question: str,
        context: str,
        chat_history: Optional[List[dict]] = None,
    ) -> tuple:
        """
        生成回答（兼容旧接口）

        Args:
            question: 用户问题
            context: 知识库上下文
            chat_history: 对话历史

        Returns:
            tuple: (回答文本, 置信度分数)
        """
        messages = self._build_prompt(question, context, chat_history)

        try:
            answer = self._generate(messages)
            confidence = self._calculate_confidence([], answer)
            return answer, confidence
        except Exception as e:
            logger.error(f"RAG生成失败: {e}", exc_info=True)
            return f"抱歉，生成回答时出现错误: {str(e)}", 0.0

    def stream_generate(
        self,
        question: str,
        context: str,
        chat_history: Optional[List[dict]] = None,
    ) -> Generator[str, None, None]:
        """
        流式生成回答（兼容旧接口）

        Args:
            question: 用户问题
            context: 知识库上下文
            chat_history: 对话历史

        Yields:
            str: 逐步生成的文本片段
        """
        messages = self._build_prompt(question, context, chat_history)

        try:
            for chunk in self.llm_service.stream_chat(messages):
                yield chunk
        except Exception as e:
            logger.error(f"RAG流式生成失败: {e}", exc_info=True)
            yield f"抱歉，生成回答时出现错误: {str(e)}"

    def chat(
        self,
        question: str,
        search_results: List[dict],
        chat_history: Optional[List[dict]] = None,
    ) -> dict:
        """
        完整的RAG问答流程（兼容旧接口）

        Args:
            question: 用户问题
            search_results: 检索结果
            chat_history: 对话历史

        Returns:
            dict: 包含answer, confidence, sources的字典
        """
        context = self._build_context(search_results)
        answer, confidence = self.generate(question, context, chat_history)

        return {
            "answer": answer,
            "confidence": confidence,
            "sources": [
                {
                    "source": r.get("source", ""),
                    "content": r.get("content", "")[:200],
                    "score": r.get("score", 0),
                    "page_number": r.get("page_number"),
                }
                for r in search_results[:3]
            ]
        }


# 全局RAG引擎单例
_rag_engine_instance: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """获取全局RAG引擎实例"""
    global _rag_engine_instance
    if _rag_engine_instance is None:
        _rag_engine_instance = RAGEngine()
    return _rag_engine_instance
