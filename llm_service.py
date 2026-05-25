"""
大语言模型服务模块

封装多后端LLM调用，提供：
- DashScope API（通义千问）
- OpenAI兼容API（vLLM、LMStudio、DeepSeek等）
- Ollama本地服务
- 同步对话生成
- 流式输出（SSE）
- 多轮对话管理
- 带系统提示词的对话
- JSON格式输出
- 模型参数配置

通过OpenAI兼容接口统一调用不同后端。
"""

import json
import logging
from typing import Any, Dict, Generator, List, Optional

from app.config import settings
from app.utils.helpers import extract_json_from_text

logger = logging.getLogger(__name__)

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
OLLAMA_DEFAULT_URL = "http://localhost:11434"


class LLMService:
    """
    大语言模型服务

    支持三种后端：
    - dashscope: 通义千问API
    - openai_compatible: 任意OpenAI兼容API
    - ollama: Ollama本地服务

    Attributes:
        backend: 后端类型
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
        backend: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.backend = backend or settings.LLM_BACKEND
        self.model = model or settings.LLM_MODEL
        self.temperature = temperature or settings.LLM_TEMPERATURE
        self.max_tokens = max_tokens or settings.LLM_MAX_TOKENS
        self._client = None

        if base_url:
            self.base_url = base_url
        elif self.backend == "dashscope":
            self.base_url = DASHSCOPE_BASE_URL
            self.api_key = api_key or settings.DASHSCOPE_API_KEY
        elif self.backend == "ollama":
            self.base_url = settings.LLM_API_BASE_URL or f"{OLLAMA_DEFAULT_URL}/v1"
            self.api_key = api_key or settings.LLM_API_KEY or "ollama"
        elif self.backend == "openai_compatible":
            self.base_url = settings.LLM_API_BASE_URL
            self.api_key = api_key or settings.LLM_API_KEY
        else:
            self.base_url = DASHSCOPE_BASE_URL
            self.api_key = api_key or settings.DASHSCOPE_API_KEY

        if not hasattr(self, "api_key"):
            self.api_key = api_key or settings.DASHSCOPE_API_KEY

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key or "unused",
                base_url=self.base_url,
            )
        return self._client

    def _reset_client(self):
        self._client = None

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
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
        json_instruction = "\n\n请严格按照JSON格式输出，不要添加任何其他文字说明。"
        messages[-1]["content"] += json_instruction

        response_text = self.chat(messages, temperature=temperature)

        try:
            result = extract_json_from_text(response_text)
            return result
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"JSON解析失败: {e}, 原始内容: {response_text[:500]}")
            raise ValueError(f"模型返回的JSON格式无效: {e}")

    def is_available(self) -> bool:
        if self.backend == "ollama":
            return True
        elif self.backend == "openai_compatible":
            return bool(self.base_url)
        else:
            return bool(self.api_key and self.api_key != "your_api_key_here")

    @staticmethod
    def list_ollama_models() -> List[Dict[str, str]]:
        try:
            import requests
            ollama_url = settings.LLM_API_BASE_URL or OLLAMA_DEFAULT_URL
            api_url = ollama_url.rstrip("/")
            if api_url.endswith("/v1"):
                api_url = api_url[:-3]
            resp = requests.get(f"{api_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("models", []):
                    models.append({
                        "name": m.get("name", ""),
                        "size": f"{m.get('size', 0) / (1024**9):.1f}GB" if m.get("size") else "",
                        "modified_at": m.get("modified_at", ""),
                    })
                return models
        except Exception as e:
            logger.debug(f"Ollama模型列表获取失败: {e}")
        return []

    @staticmethod
    def check_ollama_available() -> bool:
        try:
            import requests
            ollama_url = settings.LLM_API_BASE_URL or OLLAMA_DEFAULT_URL
            api_url = ollama_url.rstrip("/")
            if api_url.endswith("/v1"):
                api_url = api_url[:-3]
            resp = requests.get(f"{api_url}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def check_api_available(base_url: str, api_key: str = "") -> bool:
        try:
            import requests
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            url = base_url.rstrip("/") + "/models"
            resp = requests.get(url, headers=headers, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False


_llm_service_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance


def reset_llm_service():
    global _llm_service_instance
    _llm_service_instance = None
