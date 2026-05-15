"""
大语言模型服务模块

封装通义千问（Qwen）API调用，提供：
- 同步对话生成
- 流式输出（SSE）
- 多轮对话管理
- 带系统提示词的对话
- JSON格式输出
- 模型参数配置

通过OpenAI兼容接口调用通义千问API。
"""

import json
import logging
from typing import Any, Dict, Generator, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    大语言模型服务

    封装通义千问API，提供统一的对话生成接口。
    使用OpenAI兼容的调用方式。

    Attributes:
        api_key: API密钥
        model: 模型名称
        temperature: 生成温度
        max_tokens: 最大输出token数
        base_url: API基础URL
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        初始化大模型服务

        Args:
            api_key: 通义千问API密钥
            model: 模型名称
            temperature: 生成温度
            max_tokens: 最大输出token数
        """
        self.api_key = api_key or settings.DASHSCOPE_API_KEY
        self.model = model or settings.LLM_MODEL
        self.temperature = temperature or settings.LLM_TEMPERATURE
        self.max_tokens = max_tokens or settings.LLM_MAX_TOKENS
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self._client = None

    def _get_client(self):
        """
        获取OpenAI兼容客户端（延迟初始化）

        Returns:
            OpenAI: 客户端实例
        """
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        同步发送对话请求并获取完整回复

        注意：使用同步调用，因为Streamlit等前端框架是同步的。

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 生成温度（可选，覆盖默认值）
            max_tokens: 最大输出token数（可选）

        Returns:
            str: 模型生成的回复文本

        Raises:
            RuntimeError: API调用失败时抛出
        """
        client = self._get_client()
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens or self.max_tokens

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temp,
                max_tokens=tokens,
            )
            answer = response.choices[0].message.content
            logger.debug(f"LLM回复生成成功，token使用: {response.usage}")
            return answer

        except Exception as e:
            logger.error(f"LLM API调用失败: {e}", exc_info=True)
            raise RuntimeError(f"大模型API调用失败: {str(e)}")

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """
        流式对话生成，逐步返回生成内容

        使用同步生成器，逐个yield文本片段，适用于Streamlit等同步框架。

        Args:
            messages: 消息列表
            temperature: 生成温度
            max_tokens: 最大输出token数

        Yields:
            str: 逐步生成的文本片段
        """
        client = self._get_client()
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens or self.max_tokens

        try:
            stream = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temp,
                max_tokens=tokens,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"LLM流式调用失败: {e}", exc_info=True)
            raise RuntimeError(f"大模型流式调用失败: {str(e)}")

    def chat_with_system(
        self,
        system_prompt: str,
        user_message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        带系统提示词的对话

        自动构建包含系统提示词、对话历史和用户消息的完整消息列表。

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            chat_history: 对话历史（可选）
            temperature: 生成温度

        Returns:
            str: 模型回复
        """
        messages = [{"role": "system", "content": system_prompt}]

        if chat_history:
            messages.extend(chat_history)

        messages.append({"role": "user", "content": user_message})

        return self.chat(messages, temperature)

    def generate_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        生成JSON格式输出

        通过在Prompt中指定JSON格式要求，并解析模型返回的JSON内容。
        支持解析 ```json``` 代码块格式。

        Args:
            messages: 消息列表
            temperature: 生成温度（建议较低值以保证格式正确）

        Returns:
            dict: 解析后的JSON对象

        Raises:
            ValueError: JSON解析失败时抛出
        """
        # 添加JSON输出指令
        json_instruction = "\n\n请严格按照JSON格式输出，不要添加任何其他文字说明。"
        messages[-1]["content"] += json_instruction

        response_text = self.chat(messages, temperature=temperature)

        # 解析JSON：支持 ```json``` 代码块和纯JSON
        json_str = response_text.strip()

        # 尝试提取 ```json``` 代码块
        if "```json" in json_str:
            start = json_str.index("```json") + 7
            end = json_str.index("```", start)
            json_str = json_str[start:end].strip()
        elif "```" in json_str:
            # 尝试提取普通代码块
            start = json_str.index("```") + 3
            end = json_str.index("```", start)
            json_str = json_str[start:end].strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 原始内容: {response_text[:500]}")
            raise ValueError(f"模型返回的JSON格式无效: {e}")

    def is_available(self) -> bool:
        """
        检查服务是否可用

        Returns:
            bool: API密钥是否已配置且不为默认占位值
        """
        return bool(self.api_key and self.api_key != "your_api_key_here")


# 全局LLM服务单例
_llm_service_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    获取全局LLM服务单例

    Returns:
        LLMService: 全局LLM服务实例
    """
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance
