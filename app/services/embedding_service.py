"""
Embedding向量化服务模块

提供文本和图片的向量化（Embedding）功能：
- 文本向量化：使用通义千问text-embedding-v3模型
- 批量文本向量化：支持批量处理
- 图片向量化：使用多模态Embedding模型
- 内存缓存机制：基于MD5哈希避免重复计算

通过dashscope SDK调用通义千问Embedding API。
"""

import base64
import hashlib
import logging
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding向量化服务

    封装通义千问Embedding API，提供文本和图片的向量化功能。
    支持批量处理和基于MD5的内存缓存。

    Attributes:
        api_key: API密钥
        model: Embedding模型名称
        dimension: 向量维度
        _cache: 内存缓存字典（MD5哈希 -> 向量）
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        初始化Embedding服务

        Args:
            api_key: 通义千问API密钥
            model: Embedding模型名称
        """
        self.api_key = api_key or settings.DASHSCOPE_API_KEY
        self.model = model or settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        self._cache: dict = {}  # 内存缓存：MD5哈希 -> 向量

    def _get_cache_key(self, text: str) -> str:
        """
        生成缓存键（文本的MD5哈希值）

        Args:
            text: 输入文本

        Returns:
            str: 缓存键（32位MD5十六进制字符串）
        """
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _init_dashscope(self) -> None:
        """
        初始化dashscope SDK的API Key

        每次调用前确保dashscope.api_key已设置。
        """
        import dashscope
        if self.api_key:
            dashscope.api_key = self.api_key

    def embed_text(self, text: str) -> List[float]:
        """
        将单条文本转换为向量

        使用dashscope TextEmbedding API，支持内存缓存。

        Args:
            text: 输入文本

        Returns:
            List[float]: 文本的Embedding向量

        Raises:
            RuntimeError: API调用失败时抛出
        """
        # 检查缓存
        cache_key = self._get_cache_key(text)
        if cache_key in self._cache:
            logger.debug("命中Embedding缓存")
            return self._cache[cache_key]

        try:
            import dashscope
            from dashscope import TextEmbedding

            self._init_dashscope()

            resp = TextEmbedding.call(
                model=self.model,
                input=text,
            )

            if resp.status_code == 200:
                embedding = resp.output['embeddings'][0]['embedding']
                self._cache[cache_key] = embedding
                logger.debug(f"文本Embedding生成成功，文本长度: {len(text)}")
                return embedding
            else:
                error_msg = getattr(resp, 'message', str(resp))
                raise RuntimeError(f"Embedding API错误 (status={resp.status_code}): {error_msg}")

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"文本Embedding失败: {e}", exc_info=True)
            raise RuntimeError(f"文本向量化失败: {str(e)}")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量将文本转换为向量

        优先从缓存获取已有结果，仅对未缓存的文本调用API。
        批量调用时使用dashscope的批量接口提高效率。

        Args:
            texts: 输入文本列表

        Returns:
            List[List[float]]: Embedding向量列表（与输入顺序一致）

        Raises:
            RuntimeError: API调用失败时抛出
        """
        if not texts:
            return []

        # 检查缓存，分离已缓存和未缓存的文本
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

        # 批量处理未缓存的文本（API限制每次最多10条）
        if uncached_texts:
            try:
                import dashscope
                from dashscope import TextEmbedding

                self._init_dashscope()

                # 分批处理，每批最多10条
                batch_size = 10
                for batch_start in range(0, len(uncached_texts), batch_size):
                    batch_texts = uncached_texts[batch_start:batch_start + batch_size]
                    batch_indices = uncached_indices[batch_start:batch_start + batch_size]

                    resp = TextEmbedding.call(
                        model=self.model,
                        input=batch_texts,
                    )

                    if resp.status_code == 200:
                        for i, emb_data in enumerate(resp.output['embeddings']):
                            embedding = emb_data['embedding']
                            original_idx = batch_indices[i]
                            results[original_idx] = embedding
                            # 写入缓存
                            cache_key = self._get_cache_key(batch_texts[i])
                            self._cache[cache_key] = embedding
                        logger.debug(f"批量Embedding生成成功，本批数量: {len(batch_texts)}")
                    else:
                        error_msg = getattr(resp, 'message', str(resp))
                        raise RuntimeError(f"批量Embedding API错误 (status={resp.status_code}): {error_msg}")

                logger.info(f"全部Embedding生成完成，总数量: {len(uncached_texts)}")

            except RuntimeError:
                raise
            except Exception as e:
                logger.error(f"批量Embedding失败: {e}", exc_info=True)
                raise RuntimeError(f"批量文本向量化失败: {str(e)}")

        return results

    def embed_image(self, image_bytes: bytes) -> List[float]:
        """
        将图片转换为向量（多模态Embedding）

        使用dashscope MultiModalEmbedding API提取图片特征向量。
        图片以Base64编码后传入API。

        Args:
            image_bytes: 图片二进制数据

        Returns:
            List[float]: 图片的Embedding向量

        Raises:
            RuntimeError: API调用失败时抛出
        """
        try:
            import dashscope
            from dashscope import MultiModalEmbedding

            self._init_dashscope()

            # 将图片转为Base64编码
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
        """
        清空Embedding内存缓存

        释放所有已缓存的向量数据。
        """
        self._cache.clear()
        logger.info("Embedding缓存已清空")

    def get_cache_size(self) -> int:
        """
        获取缓存大小

        Returns:
            int: 当前缓存条目数量
        """
        return len(self._cache)

    def is_available(self) -> bool:
        """
        检查服务是否可用

        Returns:
            bool: API密钥是否已配置且不为默认占位值
        """
        return bool(self.api_key and self.api_key != "your_api_key_here")


# 全局Embedding服务单例
_embedding_service_instance: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    获取全局Embedding服务单例

    Returns:
        EmbeddingService: 全局Embedding服务实例
    """
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance
