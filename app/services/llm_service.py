"""
大语言模型服务模块

封装多后端LLM调用，提供：
- DashScope API（通义千问）
- OpenAI兼容API（vLLM、LMStudio等）
- Ollama本地服务
- MiniMax API（Token Plan）
- DeepSeek API（深度求索）
- Zhipu AI（智谱AI）
- Baichuan（百川智能）
- SiliconFlow（硅基流动）
- Moonshot/Kimi（月之暗面）
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
import os
from typing import Any, Dict, Generator, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.utils.helpers import extract_json_from_text

logger = logging.getLogger(__name__)

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MINIMAX_BASE_URL = "https://api.minimax.chat/v1"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
BAICHUAN_BASE_URL = "https://api.baichuan-ai.com/v1"
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
OLLAMA_DEFAULT_URL = "http://localhost:11434"
LLAMA_CPP_DEFAULT_URL = "http://localhost:11434/v1"

LLM_PROVIDER_INFO = {
    "dashscope": {
        "name": "通义千问 (DashScope)",
        "url": DASHSCOPE_BASE_URL,
        "website": "https://dashscope.console.aliyun.com",
        "models": [
            {"id": "qwen-max", "name": "Qwen Max（最强）"},
            {"id": "qwen-plus", "name": "Qwen Plus（均衡）"},
            {"id": "qwen-turbo", "name": "Qwen Turbo（最快）"},
            {"id": "qwen-long", "name": "Qwen Long（长文本）"},
        ],
    },
    "minimax": {
        "name": "MiniMax（Token Plan）",
        "url": MINIMAX_BASE_URL,
        "website": "https://platform.minimaxi.com/user-center/payment/token-plan",
        "models": [
            {"id": "abab6.5s-chat", "name": "ABAB 6.5S Chat（推荐）"},
            {"id": "abab6.5g-chat", "name": "ABAB 6.5G Chat"},
            {"id": "abab5.5s-chat", "name": "ABAB 5.5S Chat"},
            {"id": "abab5.5g-chat", "name": "ABAB 5.5G Chat"},
        ],
    },
    "deepseek": {
        "name": "DeepSeek（深度求索）",
        "url": DEEPSEEK_BASE_URL,
        "website": "https://platform.deepseek.com",
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek Chat（推荐）"},
            {"id": "deepseek-coder", "name": "DeepSeek Coder（代码）"},
            {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner（推理）"},
        ],
    },
    "zhipu": {
        "name": "智谱AI (Zhipu)",
        "url": ZHIPU_BASE_URL,
        "website": "https://open.bigmodel.cn",
        "models": [
            {"id": "glm-4", "name": "GLM-4（最强）"},
            {"id": "glm-4-flash", "name": "GLM-4-Flash（快速）"},
            {"id": "glm-3-turbo", "name": "GLM-3-Turbo（均衡）"},
        ],
    },
    "baichuan": {
        "name": "百川智能 (Baichuan)",
        "url": BAICHUAN_BASE_URL,
        "website": "https://www.baichuan-ai.com",
        "models": [
            {"id": "Baichuan4", "name": "Baichuan4（推荐）"},
            {"id": "Baichuan3-Turbo", "name": "Baichuan3-Turbo"},
            {"id": "Baichuan2-Open", "name": "Baichuan2-Open"},
        ],
    },
    "moonshot": {
        "name": "月之暗面 (Moonshot/Kimi)",
        "url": MOONSHOT_BASE_URL,
        "website": "https://platform.moonshot.cn",
        "models": [
            {"id": "moonshot-v1-128k", "name": "Moonshot V1 128K（长文本）"},
            {"id": "moonshot-v1-32k", "name": "Moonshot V1 32K（推荐）"},
            {"id": "moonshot-v1-8k", "name": "Moonshot V1 8K"},
        ],
    },
    "siliconflow": {
        "name": "硅基流动 (SiliconFlow)",
        "url": SILICONFLOW_BASE_URL,
        "website": "https://www.siliconflow.cn",
        "models": [
            {"id": "Qwen/Qwen2.5-72B-Instruct", "name": "Qwen2.5-72B（推荐）"},
            {"id": "deepseek-ai/DeepSeek-V2.5", "name": "DeepSeek V2.5"},
            {"id": "THUDM/GLM-4-9B-Chat", "name": "GLM-4-9B"},
            {"id": "Qwen/Qwen2-VL-72B-Instruct", "name": "Qwen2-VL-72B"},
        ],
    },
    "ollama": {
        "name": "Ollama（本地模型）",
        "url": OLLAMA_DEFAULT_URL,
        "website": "https://ollama.com",
        "models": [],
    },
    "llama_cpp": {
        "name": "llama.cpp（本地模型）",
        "url": LLAMA_CPP_DEFAULT_URL,
        "website": "https://github.com/ggerganov/llama.cpp",
        "models": [],
    },
    "openai_compatible": {
        "name": "OpenAI 兼容 API",
        "url": "",
        "website": "",
        "models": [],
    },
}


class LLMService:
    """
    大语言模型服务

    支持多种后端：
    - dashscope: 通义千问API
    - minimax: MiniMax API (Token Plan)
    - deepseek: DeepSeek API (深度求索)
    - zhipu: 智谱AI
    - baichuan: 百川智能
    - moonshot: 月之暗面 (Kimi)
    - siliconflow: 硅基流动
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
            self.base_url = settings.LLM_API_BASE_URL or DASHSCOPE_BASE_URL
        elif self.backend == "ollama":
            raw_url = settings.LLM_API_BASE_URL or OLLAMA_DEFAULT_URL
            if not raw_url.rstrip("/").endswith("/v1"):
                raw_url = raw_url.rstrip("/") + "/v1"
            self.base_url = raw_url
        elif self.backend == "llama_cpp":
            raw_url = settings.LLM_API_BASE_URL or LLAMA_CPP_DEFAULT_URL
            if not raw_url.rstrip("/").endswith("/v1"):
                raw_url = raw_url.rstrip("/") + "/v1"
            self.base_url = raw_url
        elif self.backend == "minimax":
            self.base_url = settings.LLM_API_BASE_URL or MINIMAX_BASE_URL
        elif self.backend == "deepseek":
            self.base_url = settings.LLM_API_BASE_URL or DEEPSEEK_BASE_URL
        elif self.backend == "zhipu":
            self.base_url = settings.LLM_API_BASE_URL or ZHIPU_BASE_URL
        elif self.backend == "baichuan":
            self.base_url = settings.LLM_API_BASE_URL or BAICHUAN_BASE_URL
        elif self.backend == "moonshot":
            self.base_url = settings.LLM_API_BASE_URL or MOONSHOT_BASE_URL
        elif self.backend == "siliconflow":
            self.base_url = settings.LLM_API_BASE_URL or SILICONFLOW_BASE_URL
        elif self.backend == "openai_compatible":
            self.base_url = settings.LLM_API_BASE_URL
        else:
            self.base_url = settings.LLM_API_BASE_URL or DASHSCOPE_BASE_URL

        # 按 backend 类型选择正确的厂商 API Key
        _vendor_key_map = {
            "dashscope": settings.DASHSCOPE_API_KEY,
            "minimax": settings.MINIMAX_API_KEY,
            "deepseek": settings.DEEPSEEK_API_KEY,
            "zhipu": settings.ZHIPU_API_KEY,
            "baichuan": settings.BAICHUAN_API_KEY,
            "moonshot": settings.MOONSHOT_API_KEY,
            "siliconflow": settings.SILICONFLOW_API_KEY,
            "ollama": "ollama",
            "llama_cpp": "no-key",
            "openai_compatible": settings.OPENAI_COMPATIBLE_API_KEY,
        }
        _fallback_key = _vendor_key_map.get(self.backend, settings.DASHSCOPE_API_KEY) or settings.LLM_API_KEY
        self.api_key = api_key or _fallback_key

    def _get_client(self):
        if self._client is None:
            import httpx
            from openai import OpenAI

            client_kwargs = {
                "api_key": self.api_key or "unused",
                "base_url": self.base_url,
            }

            http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy") or ""
            https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
            proxy = https_proxy or http_proxy
            if proxy:
                logger.info(f"使用代理: {proxy}")
                client_kwargs["http_client"] = httpx.Client(proxy=proxy, timeout=300.0)

            self._client = OpenAI(**client_kwargs)
        return self._client

    def _reset_client(self):
        self._client = None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def _chat_with_timeout(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """带超时和重试的聊天调用"""
        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=300,
            )
            return response.choices[0].message.content
        except Exception as e:
            err_str = str(e)
            if "connect" in err_str.lower() or "timeout" in err_str.lower() or "resolve" in err_str.lower() or "eof" in err_str.lower():
                logger.error(f"LLM API 网络连接失败: {err_str[:200]}")
                logger.error("检查网络连接，如需代理请设置 HTTP_PROXY 环境变量")
            raise

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens or self.max_tokens

        try:
            answer = self._chat_with_timeout(messages, temp, tokens)
            logger.debug(f"LLM回复生成成功")
            return answer

        except RuntimeError:
            raise
        except Exception as e:
            err_str = str(e)
            logger.error(f"LLM API调用失败: {err_str[:300]}", exc_info=False)
            if "connect" in err_str.lower() or "timeout" in err_str.lower() or "resolve" in err_str.lower() or "eof" in err_str.lower():
                msg = ("大模型API网络连接失败。请检查网络配置：\n"
                       "1. 确认虚拟机可访问外网\n"
                       "2. 如需代理，执行: export HTTP_PROXY=http://代理地址:端口\n"
                       "3. 确认 DASHSCOPE_API_KEY 已正确配置")
                raise RuntimeError(msg)
            raise RuntimeError(f"大模型API调用失败: {err_str[:200]}")

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
        modified_messages = [m.copy() for m in messages]
        modified_messages[-1]["content"] += json_instruction

        response_text = self.chat(modified_messages, temperature=temperature)

        try:
            result = extract_json_from_text(response_text)
            return result
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"JSON解析失败: {e}, 原始内容: {response_text[:500]}")
            raise ValueError(f"模型返回的JSON格式无效: {e}")

    def is_available(self) -> bool:
        if self.backend == "ollama":
            try:
                import requests
                ollama_url = settings.LLM_API_BASE_URL or OLLAMA_DEFAULT_URL
                api_url = ollama_url.rstrip("/")
                if api_url.endswith("/v1"):
                    api_url = api_url[:-3]
                resp = requests.get(f"{api_url}/api/tags", timeout=3)
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    if models:
                        return True
                return False
            except Exception:
                return False
        elif self.backend == "llama_cpp":
            try:
                import requests
                url = settings.LLM_API_BASE_URL or LLAMA_CPP_DEFAULT_URL
                resp = requests.get(f"{url.rstrip('/')}/models", timeout=3)
                return resp.status_code == 200
            except Exception:
                return False
        elif self.backend in ("openai_compatible", "deepseek", "zhipu", "baichuan", "moonshot", "siliconflow"):
            return bool(self.api_key and self.api_key != "your_api_key_here")
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
    def list_llama_cpp_models() -> List[Dict[str, str]]:
        """获取 llama-server 上已加载的模型列表"""
        try:
            import requests
            url = settings.LLM_API_BASE_URL or LLAMA_CPP_DEFAULT_URL
            resp = requests.get(f"{url.rstrip('/')}/models", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("data", []):
                    models.append({
                        "name": m.get("id", ""),
                        "size": "",
                        "modified_at": "",
                    })
                return models
        except Exception as e:
            logger.debug(f"llama.cpp模型列表获取失败: {e}")
        return []

    @staticmethod
    def check_llama_cpp_available() -> bool:
        """检查 llama-server 是否在运行"""
        try:
            import requests
            url = settings.LLM_API_BASE_URL or LLAMA_CPP_DEFAULT_URL
            resp = requests.get(f"{url.rstrip('/')}/models", timeout=3)
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
