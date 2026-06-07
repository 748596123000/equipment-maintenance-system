"""
Embedding向量化服务模块

提供文本和图片的向量化（Embedding）功能：
- 文本向量化：支持DashScope API和Ollama本地模型
- 批量文本向量化：支持批量处理
- 图片向量化：使用多模态Embedding模型
- 内存缓存机制：基于MD5哈希避免重复计算

支持后端：
- dashscope: 通义千问text-embedding API
- ollama: Ollama本地模型embedding接口（x86_64/aarch64）
- llama_cpp: llama.cpp本地GGUF模型（LoongArch替代方案）
"""

import base64
import hashlib
import logging
import platform
import threading
import time
from typing import List, Optional

from cachetools import LRUCache

from app.config import settings

logger = logging.getLogger(__name__)

# 架构检测
_ARCH = platform.machine().lower()
_IS_LOONGARCH = "loongarch" in _ARCH or "loong64" in _ARCH


_DEFAULT_BASE_URLS = {
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "openai_compatible": "",
    "llama_cpp": "http://127.0.0.1:8080/v1",
    "ollama": "http://localhost:11434/v1",
}


class EmbeddingService:

    def __init__(self):
        # 运行时状态字段（缓存 / 限流 / 内部锁）必须在 __init__ 中初始化
        # 业务配置字段（api_key / vendor / base_url / model）改为 property，实时读 settings
        self._cache: LRUCache = LRUCache(maxsize=5000)
        self.batch_size = 25
        self.max_retries = 3
        self.request_timeout = 30.0
        self._client_lock = threading.Lock()
        self._last_request_time = 0
        self._min_request_interval = 0.05
        # 后端选择：vendor 直接覆盖 _backend
        self._backend = self.vendor if self.vendor in ("dashscope", "ollama", "llama_cpp", "openai_compatible") else self._detect_backend()
        logger.info(
            f"EmbeddingService 初始化: vendor={self.vendor}, model={self.model}, "
            f"base_url={self.base_url}, backend={self._backend}"
        )

    @property
    def api_key(self) -> str:
        """实时从 settings 读取 api_key（避免 lifespan / 后台任务中的缓存过期问题）

        历史 bug：之前在 __init__ 里把 api_key 缓存到 self.api_key，
        但 lifespan 早期创建实例后，_auto_detect_backends() / 后台任务
        运行时 settings.DASHSCOPE_API_KEY 已被 db 覆盖，导致实例的
        self.api_key 仍是创建时的空值，调用 OpenAI() 时报 Missing credentials。
        """
        _placeholder = {"your_api_key_here", "unused", "no-key", "not-needed", ""}
        _emb_key = (settings.EMBEDDING_API_KEY or "").strip()
        _oai_key = (settings.OPENAI_COMPATIBLE_API_KEY or "").strip()
        _ds_key = (settings.DASHSCOPE_API_KEY or "").strip()
        for v in (_emb_key, _oai_key, _ds_key):
            if v and v not in _placeholder:
                return v
        return ""

    @property
    def vendor(self) -> str:
        return (settings.EMBEDDING_VENDOR or "dashscope").lower()

    @property
    def base_url(self) -> str:
        return (settings.EMBEDDING_API_BASE_URL
                or _DEFAULT_BASE_URLS.get(self.vendor, "")).rstrip("/")

    @property
    def model(self) -> str:
        return settings.EMBEDDING_MODEL_NAME or settings.EMBEDDING_MODEL

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION

    @property
    def _is_available(self) -> bool:
        """实时判断后端是否可用"""
        if self._backend == "dashscope":
            return bool(self.api_key)
        if self._backend in ("ollama", "llama_cpp"):
            return True
        return False

    def _resolve_vendor_config(self, vendor: Optional[str] = None,
                                 api_key: Optional[str] = None,
                                 base_url: Optional[str] = None,
                                 model: Optional[str] = None) -> dict:
        """解析运行时参数覆盖（用于测试或多租户场景）"""
        v = (vendor or self.vendor).lower()
        return {
            "vendor": v,
            "api_key": api_key or self.api_key,
            "base_url": (base_url or self.base_url).rstrip("/"),
            "model": model or self.model,
        }

    def _detect_backend(self) -> str:
        if self.api_key and self.api_key != "your_api_key_here":
            return "dashscope"

        # LoongArch架构检测
        if _IS_LOONGARCH:
            logger.info("检测到LoongArch架构，跳过Ollama检测")
            if self._check_llama_cpp_available():
                return "llama_cpp"
            if self.api_key and self.api_key != "your_api_key_here":
                return "dashscope"
            logger.warning("LoongArch: 未配置DashScope API Key，且未找到llama.cpp本地模型")
            logger.warning("建议：配置 DASHSCOPE_API_KEY 或 LLAMA_CPP_EMBED_MODEL_PATH")
            return "unavailable"

        # 标准架构：检测Ollama
        try:
            import requests
            ollama_url = settings.LLM_API_BASE_URL or "http://localhost:11434"
            api_url = ollama_url.rstrip("/")
            if api_url.endswith("/v1"):
                api_url = api_url[:-3]
            resp = requests.get(f"{api_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                return "ollama"
        except Exception:
            pass
        if self.api_key and self.api_key != "your_api_key_here":
            return "dashscope"
        return "unavailable"

    def _check_llama_cpp_available(self) -> bool:
        model_path = getattr(settings, 'LLAMA_CPP_EMBED_MODEL_PATH', None)
        if not model_path:
            return False
        import os
        if not os.path.exists(model_path):
            logger.warning(f"llama.cpp模型路径不存在: {model_path}")
            return False
        try:
            import llama_cpp
            return True
        except ImportError:
            logger.warning("llama-cpp-python未安装，本地Embedding不可用")
            return False

    @property
    def backend(self) -> str:
        return self._backend

    def _get_cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _init_dashscope(self) -> None:
        import dashscope
        import os as _os
        # 每次调用都强制设置，防止多进程/子进程环境下全局变量丢失
        if self.api_key:
            dashscope.api_key = self.api_key
        # 同时设置环境变量（某些 SDK 版本从环境变量读 key）
        _os.environ["DASHSCOPE_API_KEY"] = self.api_key or ""

    def _embed_text_ollama(self, text: str) -> List[float]:
        import requests
        ollama_url = settings.LLM_API_BASE_URL or "http://localhost:11434"
        api_url = ollama_url.rstrip("/")
        if api_url.endswith("/v1"):
            api_url = api_url[:-3]

        embed_model = self._get_ollama_embed_model(api_url)

        resp = requests.post(
            f"{api_url}/api/embed",
            json={"model": embed_model, "input": text},
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Ollama embedding API错误 (status={resp.status_code}): {resp.text[:200]}")

        data = resp.json()
        embeddings = data.get("embeddings") or data.get("embedding")
        if embeddings:
            if isinstance(embeddings[0], list):
                return embeddings[0]
            return embeddings
        raise RuntimeError(f"Ollama embedding返回格式异常: {list(data.keys())}")

    def _embed_texts_ollama(self, texts: List[str]) -> List[List[float]]:
        import requests
        ollama_url = settings.LLM_API_BASE_URL or "http://localhost:11434"
        api_url = ollama_url.rstrip("/")
        if api_url.endswith("/v1"):
            api_url = api_url[:-3]

        embed_model = self._get_ollama_embed_model(api_url)

        results = []
        for text in texts:
            resp = requests.post(
                f"{api_url}/api/embed",
                json={"model": embed_model, "input": text},
                timeout=60,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama embedding API错误 (status={resp.status_code}): {resp.text[:200]}")

            data = resp.json()
            embeddings = data.get("embeddings") or data.get("embedding")
            if embeddings:
                if isinstance(embeddings[0], list):
                    results.append(embeddings[0])
                else:
                    results.append(embeddings)
            else:
                raise RuntimeError(f"Ollama embedding返回格式异常")

        return results

    def _get_ollama_embed_model(self, api_url: str) -> str:
        embed_model = getattr(settings, 'EMBEDDING_MODEL', '') or 'nomic-embed-text'
        if embed_model.startswith("text-embedding"):
            embed_model = "nomic-embed-text"

        try:
            import requests
            resp = requests.get(f"{api_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                for candidate in [embed_model, "nomic-embed-text", "mxbai-embed-large", "all-minilm"]:
                    for m in models:
                        if m.lower().startswith(candidate.lower()):
                            return m.split(":")[0]

                logger.info(f"未找到Embedding模型，尝试自动拉取 nomic-embed-text ...")
                pull_resp = requests.post(
                    f"{api_url}/api/pull",
                    json={"name": "nomic-embed-text"},
                    timeout=300,
                )
                if pull_resp.status_code == 200:
                    logger.info("nomic-embed-text 模型拉取成功")
                    return "nomic-embed-text"
                logger.warning(f"模型拉取失败: {pull_resp.status_code}")
        except Exception as e:
            logger.warning(f"获取Ollama模型列表失败: {e}")

        return embed_model

    def _embed_text_llama_cpp(self, text: str) -> List[float]:
        try:
            from llama_cpp import Llama

            model_path = getattr(settings, 'LLAMA_CPP_EMBED_MODEL_PATH', None)
            if not model_path:
                raise RuntimeError("未配置LLAMA_CPP_EMBED_MODEL_PATH")

            llm = Llama(
                model_path=model_path,
                embedding=True,
                n_ctx=512,
                verbose=False,
            )
            embedding = llm.create_embedding(text)
            return embedding['data'][0]['embedding']
        except Exception as e:
            logger.error(f"llama.cpp Embedding失败: {e}")
            raise RuntimeError(f"本地Embedding失败: {str(e)}")

    def _embed_texts_llama_cpp(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            results.append(self._embed_text_llama_cpp(text))
        return results

    # ---------- OpenAI 兼容 Embedding（用于 vLLM / llama-server / LMStudio / 第三方厂商） ----------

    def _embed_text_openai_compatible(self, text: str) -> List[float]:
        if not self.base_url:
            raise RuntimeError("OpenAI 兼容 Embedding 需要配置 EMBEDDING_API_BASE_URL")
        if not self.model:
            raise RuntimeError("OpenAI 兼容 Embedding 需要配置 EMBEDDING_MODEL_NAME")

        # 限流
        with self._client_lock:
            now = time.time()
            wait = self._min_request_interval - (now - self._last_request_time)
            if wait > 0:
                time.sleep(wait)
            self._last_request_time = time.time()

        import requests
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key or 'no-key'}",
            "Content-Type": "application/json",
        }
        payload = {"input": text, "model": self.model}
        resp = requests.post(url, json=payload, headers=headers, timeout=self.request_timeout)
        if resp.status_code != 200:
            raise RuntimeError(
                f"OpenAI-compatible Embedding 错误 (status={resp.status_code}): {resp.text[:200]}"
            )
        data = resp.json()
        items = data.get("data") or []
        if not items:
            raise RuntimeError(f"OpenAI-compatible Embedding 返回格式异常: {list(data.keys())}")
        return items[0].get("embedding") or items[0].get("data")

    def _embed_texts_openai_compatible(self, texts: List[str]) -> List[List[float]]:
        if not self.base_url:
            raise RuntimeError("OpenAI 兼容 Embedding 需要配置 EMBEDDING_API_BASE_URL")
        if not self.model:
            raise RuntimeError("OpenAI 兼容 Embedding 需要配置 EMBEDDING_MODEL_NAME")

        import requests
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key or 'no-key'}",
            "Content-Type": "application/json",
        }
        results: List[List[float]] = []
        # 大多数 OpenAI 兼容服务支持批量输入
        try:
            payload = {"input": texts, "model": self.model}
            resp = requests.post(url, json=payload, headers=headers, timeout=self.request_timeout)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data") or []
                # 按 index 排序
                items.sort(key=lambda x: x.get("index", 0))
                for it in items:
                    results.append(it.get("embedding") or it.get("data"))
                return results
        except Exception:
            pass

        # 批量失败则逐条调用
        for text in texts:
            results.append(self._embed_text_openai_compatible(text))
        return results

    def _embed_text_dashscope(self, text: str) -> List[float]:
        # 使用 OpenAI 兼容接口替代 dashscope SDK 原生接口
        # 原因：dashscope SDK 的 dashscope.api_key 全局变量在多进程/子进程环境下
        # 会被重置为 None，导致 401 No API-key provided
        # OpenAI 兼容接口通过 httpx 直接传 Authorization header，不受全局变量影响
        if not self.api_key:
            raise RuntimeError(
                "DASHSCOPE_API_KEY 未配置（db system_config 表中 key=dashscope_api_key 缺失或为占位符）。"
                "请在前端「系统配置」页填写 DashScope API Key，或在 .env 设置 DASHSCOPE_API_KEY 后重启服务。"
            )
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=self.api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            response = client.embeddings.create(
                model=self.model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(f"Embedding API错误: {e}")

    def _embed_texts_dashscope(self, texts: List[str]) -> List[List[float]]:
        # 使用 OpenAI 兼容接口替代 dashscope SDK 原生接口
        if not self.api_key:
            raise RuntimeError(
                "DASHSCOPE_API_KEY 未配置（db system_config 表中 key=dashscope_api_key 缺失或为占位符）。"
                "请在前端「系统配置」页填写 DashScope API Key，或在 .env 设置 DASHSCOPE_API_KEY 后重启服务。"
            )
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=self.api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )

            results = []
            batch_size = 10
            for batch_start in range(0, len(texts), batch_size):
                batch_texts = texts[batch_start:batch_start + batch_size]

                response = client.embeddings.create(
                    model=self.model,
                    input=batch_texts,
                )

                for emb_data in response.data:
                    results.append(emb_data.embedding)
                logger.debug(f"批量Embedding生成成功，本批数量: {len(batch_texts)}")

            return results
        except Exception as e:
            raise RuntimeError(f"批量Embedding API错误: {e}")

    def embed_text(self, text: str) -> List[float]:
        cache_key = self._get_cache_key(text)
        if cache_key in self._cache:
            logger.debug("命中Embedding缓存")
            return self._cache[cache_key]

        try:
            if self._backend == "ollama":
                embedding = self._embed_text_ollama(text)
            elif self._backend == "llama_cpp":
                embedding = self._embed_text_llama_cpp(text)
            elif self._backend == "openai_compatible":
                embedding = self._embed_text_openai_compatible(text)
            elif self._backend == "dashscope":
                embedding = self._embed_text_dashscope(text)
            else:
                raise RuntimeError("无可用的Embedding后端，请配置DashScope API Key或启动Ollama/llama-server")

            self._cache[cache_key] = embedding
            logger.debug(f"文本Embedding生成成功，文本长度: {len(text)}")
            return embedding

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"文本Embedding失败: {e}", exc_info=True)
            raise RuntimeError(f"文本向量化失败: {str(e)}")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        results: List[Optional[List[float]]] = [None] * len(texts)
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                results[i] = self._cache[cache_key]
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            try:
                if self._backend == "ollama":
                    embeddings = self._embed_texts_ollama(uncached_texts)
                elif self._backend == "llama_cpp":
                    embeddings = self._embed_texts_llama_cpp(uncached_texts)
                elif self._backend == "openai_compatible":
                    embeddings = self._embed_texts_openai_compatible(uncached_texts)
                elif self._backend == "dashscope":
                    embeddings = self._embed_texts_dashscope(uncached_texts)
                else:
                    raise RuntimeError("无可用的Embedding后端，请配置DashScope API Key或启动Ollama/llama-server")

                for i, embedding in enumerate(embeddings):
                    original_idx = uncached_indices[i]
                    results[original_idx] = embedding
                    cache_key = self._get_cache_key(uncached_texts[i])
                    self._cache[cache_key] = embedding

                logger.info(f"全部Embedding生成完成，总数量: {len(uncached_texts)}")

            except RuntimeError:
                raise
            except Exception as e:
                logger.error(f"批量Embedding失败: {e}", exc_info=True)
                raise RuntimeError(f"批量文本向量化失败: {str(e)}")

        return results

    def embed_image(self, image_bytes: bytes) -> List[float]:
        if self._backend in ("ollama", "llama_cpp"):
            raise RuntimeError("本地后端暂不支持图片Embedding，请配置DashScope API Key")

        try:
            import dashscope
            from dashscope import MultiModalEmbedding

            self._init_dashscope()

            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            resp = MultiModalEmbedding.call(
                model="text-embedding-v3",
                input=[
                    {
                        "task_type": "image",
                        "image_url": f"data:image/jpeg;base64,{image_base64}"
                    }
                ],
            )

            if resp.status_code == 200:
                embedding = resp.output['embeddings'][0]['embedding']
                logger.debug(f"图片Embedding生成成功，图片大小: {len(image_bytes)} bytes")
                return embedding
            else:
                error_msg = getattr(resp, 'message', str(resp))
                raise RuntimeError(f"多模态Embedding API错误 (status={resp.status_code}): {error_msg}")

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"图片Embedding失败: {e}", exc_info=True)
            raise RuntimeError(f"图片向量化失败: {str(e)}")

    def clear_cache(self) -> None:
        self._cache.clear()
        logger.info("Embedding缓存已清空")

    def get_cache_size(self) -> int:
        return len(self._cache)

    def is_available(self) -> bool:
        # self.api_key 已经是 property，会自动过滤占位符
        if self._backend == "dashscope":
            return bool(self.api_key)
        elif self._backend in ("ollama", "llama_cpp"):
            return True
        return False


_embedding_service_instance: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance


def reset_embedding_service():
    global _embedding_service_instance
    _embedding_service_instance = None
