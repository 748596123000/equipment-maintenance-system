"""
Embedding向量化服务模块 - 麒麟V11 LoongArch适配版

适配说明：
- LoongArch架构不支持Ollama（x86预编译二进制）
- 使用llama.cpp替代Ollama作为本地Embedding后端
- 优先推荐DashScope API（通义千问text-embedding）
- 本地模型需手动下载GGUF格式并配置路径

支持后端：
- dashscope: 通义千问text-embedding API（推荐）
- llama_cpp: llama.cpp本地GGUF模型（需手动配置）
- unavailable: 无可用后端
"""

import base64
import hashlib
import logging
from typing import List, Optional

from cachetools import LRUCache

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingServiceLoongArch:

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.DASHSCOPE_API_KEY
        self.model = model or settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        self._cache: LRUCache = LRUCache(maxsize=5000)
        self._backend = self._detect_backend()
        self._llama_cpp_path = getattr(settings, 'LLAMA_CPP_EMBED_MODEL_PATH', None)

    def _detect_backend(self) -> str:
        if self.api_key and self.api_key != "your_api_key_here" and self.api_key != "":
            return "dashscope"

        if self._check_llama_cpp_available():
            return "llama_cpp"

        logger.warning("LoongArch: 未配置DashScope API Key，且未找到llama.cpp本地模型")
        logger.warning("建议：在.env中配置 DASHSCOPE_API_KEY 或 LLAMA_CPP_EMBED_MODEL_PATH")
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
        if self.api_key:
            dashscope.api_key = self.api_key

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

    def _embed_text_dashscope(self, text: str) -> List[float]:
        import dashscope
        from dashscope import TextEmbedding

        self._init_dashscope()

        resp = TextEmbedding.call(
            model=self.model,
            input=text,
        )

        if resp.status_code == 200:
            embedding = resp.output['embeddings'][0]['embedding']
            return embedding
        else:
            error_msg = getattr(resp, 'message', str(resp))
            raise RuntimeError(f"Embedding API错误 (status={resp.status_code}): {error_msg}")

    def _embed_texts_dashscope(self, texts: List[str]) -> List[List[float]]:
        import dashscope
        from dashscope import TextEmbedding

        self._init_dashscope()

        results = []
        batch_size = 10
        for batch_start in range(0, len(texts), batch_size):
            batch_texts = texts[batch_start:batch_start + batch_size]

            resp = TextEmbedding.call(
                model=self.model,
                input=batch_texts,
            )

            if resp.status_code == 200:
                for emb_data in resp.output['embeddings']:
                    results.append(emb_data['embedding'])
                logger.debug(f"批量Embedding生成成功，本批数量: {len(batch_texts)}")
            else:
                error_msg = getattr(resp, 'message', str(resp))
                raise RuntimeError(f"批量Embedding API错误 (status={resp.status_code}): {error_msg}")

        return results

    def embed_text(self, text: str) -> List[float]:
        cache_key = self._get_cache_key(text)
        if cache_key in self._cache:
            logger.debug("命中Embedding缓存")
            return self._cache[cache_key]

        try:
            if self._backend == "dashscope":
                embedding = self._embed_text_dashscope(text)
            elif self._backend == "llama_cpp":
                embedding = self._embed_text_llama_cpp(text)
            else:
                raise RuntimeError(
                    "LoongArch: 无可用的Embedding后端。\n"
                    "请配置以下任一方式：\n"
                    "1. DASHSCOPE_API_KEY - 使用通义千问API（推荐）\n"
                    "2. LLAMA_CPP_EMBED_MODEL_PATH - 使用本地GGUF模型"
                )

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
                if self._backend == "dashscope":
                    embeddings = self._embed_texts_dashscope(uncached_texts)
                elif self._backend == "llama_cpp":
                    embeddings = self._embed_texts_llama_cpp(uncached_texts)
                else:
                    raise RuntimeError(
                        "LoongArch: 无可用的Embedding后端。\n"
                        "请配置以下任一方式：\n"
                        "1. DASHSCOPE_API_KEY - 使用通义千问API（推荐）\n"
                        "2. LLAMA_CPP_EMBED_MODEL_PATH - 使用本地GGUF模型"
                    )

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
        if self._backend == "llama_cpp":
            raise RuntimeError("llama.cpp后端暂不支持图片Embedding，请配置DashScope API Key")

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
        if self._backend == "dashscope":
            return bool(self.api_key and self.api_key != "your_api_key_here")
        elif self._backend == "llama_cpp":
            return True
        return False


_embedding_service_instance: Optional[EmbeddingServiceLoongArch] = None


def get_embedding_service() -> EmbeddingServiceLoongArch:
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingServiceLoongArch()
    return _embedding_service_instance


def reset_embedding_service():
    global _embedding_service_instance
    _embedding_service_instance = None
