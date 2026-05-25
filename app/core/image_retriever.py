"""
图片检索模块

实现基于多模态能力的图片检索功能：
- 以图搜图：上传图片，使用LLM视觉能力描述图片内容，然后进行文本检索
- 图文跨模态检索：根据文本描述搜索相关图片
- 图片与设备文档的关联匹配

由于纯图片向量检索较复杂，采用"图片 -> LM视觉描述 -> 文本检索"的方案。
使用通义千问的多模态能力（qwen-vl-max）来描述图片内容。
"""

import base64
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

from app.config import settings
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


@dataclass
class ImageSearchResult:
    """图片检索结果"""
    image_id: str
    image_path: str
    similarity: float
    source_document: Optional[str] = None
    page_number: Optional[int] = None
    caption: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "image_id": self.image_id,
            "image_path": self.image_path,
            "similarity": self.similarity,
            "source_document": self.source_document,
            "page_number": self.page_number,
            "caption": self.caption,
            "metadata": self.metadata,
        }


class ImageRetriever:
    """
    图片检索器

    使用通义千问多模态模型（qwen-vl-max）描述图片内容，
    然后通过文本检索在知识库中查找相关内容。
    支持以图搜图和图文跨模态检索。

    方案：图片 -> LLM视觉描述 -> 文本Embedding -> 向量检索

    Attributes:
        image_dir: 图片存储目录
        collection_name: ChromaDB图片集合名称
        vl_model: 多模态模型名称
    """

    # 图片描述提示词
    IMAGE_DESCRIPTION_PROMPT = """请详细描述这张图片的内容。这是一张与设备检修相关的图片。
请从以下方面进行描述：
1. 图片中展示的设备类型和型号（如果能识别）
2. 设备的状态或故障现象
3. 图片中涉及的操作或检修活动
4. 重要的技术参数或标识
5. 图片中显示的工具或安全设备

请用简洁的中文描述，重点提取可用于检索的关键信息。"""

    def __init__(
        self,
        image_dir: Optional[str] = None,
        collection_name: str = "equipment_images",
        vl_model: str = "qwen-vl-max",
    ):
        """
        初始化图片检索器

        Args:
            image_dir: 图片存储目录
            collection_name: ChromaDB集合名称
            vl_model: 多模态视觉模型名称
        """
        self.image_dir = image_dir or settings.IMAGE_DIR
        self.collection_name = collection_name
        self.vl_model = vl_model
        self.llm_service = get_llm_service()
        self._collection = None
        self._client = None

    def init_collection(self) -> None:
        """
        初始化图片向量数据库集合

        使用ChromaDB存储图片描述文本和对应的元数据，
        支持通过文本描述检索图片。
        """
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )

            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "description": "设备图片描述库"
                }
            )

            logger.info(f"图片向量集合初始化完成: {self.collection_name}")

        except Exception as e:
            logger.error(f"图片向量集合初始化失败: {e}", exc_info=True)
            raise RuntimeError(f"图片向量集合初始化失败: {e}")

    def _ensure_collection(self):
        """确保集合已初始化"""
        if self._collection is None:
            self.init_collection()

    def _extract_image_features(self, image_bytes: bytes) -> str:
        """
        提取图片特征描述

        使用通义千问多模态模型（qwen-vl-max）描述图片内容，
        将图片转换为可用于检索的文本描述。

        Args:
            image_bytes: 图片二进制数据

        Returns:
            str: 图片内容的文本描述
        """
        try:
            # 将图片转为base64
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            # 判断图片格式
            image_format = "image/png"
            if image_bytes[:2] == b'\xff\xd8':
                image_format = "image/jpeg"
            elif image_bytes[:4] == b'\x89PNG':
                image_format = "image/png"
            elif image_bytes[:4] == b'GIF8':
                image_format = "image/gif"
            elif image_bytes[:4] == b'RIFF':
                image_format = "image/webp"

            # 构建多模态消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_format};base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": self.IMAGE_DESCRIPTION_PROMPT
                        }
                    ]
                }
            ]

            # 使用视觉模型生成描述
            # 创建一个临时的LLM服务实例，使用视觉模型
            from openai import OpenAI

            client = OpenAI(
                api_key=self.llm_service.api_key,
                base_url=self.llm_service.base_url,
            )

            response = client.chat.completions.create(
                model=self.vl_model,
                messages=messages,
                temperature=0.3,
                max_tokens=500,
            )

            description = response.choices[0].message.content
            logger.info(f"图片描述生成成功: {description[:100]}...")
            return description

        except Exception as e:
            logger.error(f"图片特征提取失败: {e}", exc_info=True)
            raise RuntimeError(f"图片描述生成失败: {str(e)}")

    def search_by_image(
        self,
        image_path: str,
        top_k: int = 5,
        threshold: float = 0.3,
    ) -> List[ImageSearchResult]:
        """
        以图搜图：通过上传的图片查找相似的文本/图片结果

        流程：
        1. 读取图片文件
        2. 使用多模态模型描述图片内容
        3. 使用描述文本在知识库中检索相关内容

        Args:
            image_path: 图片文件路径
            top_k: 返回结果数量
            threshold: 相似度阈值

        Returns:
            List[ImageSearchResult]: 相似结果列表
        """
        # 读取图片文件
        if not os.path.exists(image_path):
            logger.error(f"图片文件不存在: {image_path}")
            return []

        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
        except Exception as e:
            logger.error(f"读取图片文件失败: {e}", exc_info=True)
            return []

        if len(image_bytes) < 100:
            logger.warning("图片文件过小，可能不是有效图片")
            return []

        # 提取图片特征描述
        try:
            description = self._extract_image_features(image_bytes)
        except Exception as e:
            logger.error(f"图片描述生成失败: {e}", exc_info=True)
            return []

        # 使用描述文本在知识库中检索
        return self.search_by_text_for_images(description, top_k, threshold)

    def search_by_text_for_images(
        self,
        query_text: str,
        top_k: int = 5,
        threshold: float = 0.3,
    ) -> List[ImageSearchResult]:
        """
        根据文本描述搜索相关图片

        在图片描述库中检索与文本描述匹配的图片。

        Args:
            query_text: 文本描述
            top_k: 返回结果数量
            threshold: 相似度阈值

        Returns:
            List[ImageSearchResult]: 匹配的图片列表
        """
        self._ensure_collection()

        try:
            count = self._collection.count()
            if count == 0:
                logger.warning("图片描述库为空")
                return []
        except Exception:
            pass

        # 生成查询文本的Embedding
        try:
            from app.services.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            query_embedding = embedding_service.embed_text(query_text)
        except Exception as e:
            logger.error(f"生成查询向量失败: {e}", exc_info=True)
            return []

        # 在图片描述库中检索
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, max(self._collection.count(), 1)),
                include=["metadatas", "documents", "distances"]
            )
        except Exception as e:
            logger.error(f"图片检索失败: {e}", exc_info=True)
            return []

        # 转换为ImageSearchResult
        search_results = []
        if results and results.get("ids"):
            for i in range(len(results["ids"][0])):
                image_id = results["ids"][0][i]
                distance = results["distances"][0][i] if results.get("distances") else 1.0
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}

                score = 1.0 - distance

                if score < threshold:
                    continue

                # 构建图片路径
                image_filename = meta.get("filename", f"{image_id}.png")
                image_path = os.path.join(self.image_dir, image_filename)

                # 如果文件不存在，尝试在image_dir下搜索
                if not os.path.exists(image_path):
                    # 尝试通过模糊匹配找到图片文件
                    image_path = self._find_image_file(image_id, meta)

                search_results.append(ImageSearchResult(
                    image_id=image_id,
                    image_path=image_path,
                    similarity=score,
                    source_document=meta.get("source_document"),
                    page_number=meta.get("page_number"),
                    caption=meta.get("caption", ""),
                    metadata=meta,
                ))

        logger.info(f"图文检索完成: query='{query_text[:30]}...', 返回 {len(search_results)} 条结果")
        return search_results

    def _find_image_file(self, image_id: str, metadata: dict) -> str:
        """
        在图片目录中查找图片文件

        Args:
            image_id: 图片ID
            metadata: 图片元数据

        Returns:
            str: 图片文件路径（未找到则返回空字符串）
        """
        if not os.path.exists(self.image_dir):
            return ""

        # 尝试通过source_document和page_number查找
        source = metadata.get("source_document", "")
        page = metadata.get("page_number", "")

        if source and page:
            # 尝试匹配文件名模式：{source}_p{page}_img*.*
            for ext in ["png", "jpg", "jpeg", "gif", "webp"]:
                pattern = f"*_p{page}_img*.{ext}"
                import glob
                matches = glob.glob(os.path.join(self.image_dir, pattern))
                if matches:
                    return matches[0]

        # 尝试通过image_id查找
        for ext in ["png", "jpg", "jpeg", "gif", "webp"]:
            candidate = os.path.join(self.image_dir, f"{image_id}.{ext}")
            if os.path.exists(candidate):
                return candidate

        return ""

    def add_image(
        self,
        image_id: str,
        image_bytes: bytes,
        source_document: Optional[str] = None,
        page_number: Optional[int] = None,
        caption: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        添加图片到检索库

        流程：
        1. 使用多模态模型生成图片描述
        2. 将描述文本向量化
        3. 存入ChromaDB（包含图片元数据）

        Args:
            image_id: 图片唯一标识
            image_bytes: 图片二进制数据
            source_document: 来源文档名
            page_number: 页码
            caption: 图片说明
            metadata: 附加元数据

        Returns:
            bool: 是否添加成功
        """
        self._ensure_collection()

        try:
            # 生成图片描述
            description = self._extract_image_features(image_bytes)

            # 如果有手动提供的caption，合并到描述中
            if caption:
                description = f"{caption}\n{description}"

            # 生成描述文本的Embedding
            from app.services.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            embedding = embedding_service.embed_text(description)

            # 构建元数据
            img_metadata = {
                "source_document": source_document or "",
                "page_number": page_number or 0,
                "caption": caption or "",
                "image_id": image_id,
            }

            # 合并附加元数据
            if metadata:
                for key, value in metadata.items():
                    if value is not None and key not in img_metadata:
                        if isinstance(value, (str, int, float, bool)):
                            img_metadata[key] = value
                        else:
                            img_metadata[key] = str(value)

            # 存入ChromaDB
            self._collection.add(
                ids=[image_id],
                documents=[description],
                embeddings=[embedding],
                metadatas=[img_metadata]
            )

            logger.info(f"图片已添加到检索库: {image_id}")
            return True

        except Exception as e:
            logger.error(f"图片添加失败: {e}", exc_info=True)
            return False

    def search(
        self,
        image_base64: str,
        top_k: int = 5,
    ) -> List[ImageSearchResult]:
        """
        通用图片检索入口

        接收Base64编码的图片，进行以图搜图。

        Args:
            image_base64: Base64编码的图片
            top_k: 返回结果数量

        Returns:
            List[ImageSearchResult]: 检索结果
        """
        try:
            image_bytes = base64.b64decode(image_base64)

            # 提取图片特征描述
            description = self._extract_image_features(image_bytes)

            # 使用描述文本检索
            return self.search_by_text_for_images(description, top_k)

        except Exception as e:
            logger.error(f"图片检索失败: {e}", exc_info=True)
            return []

    def delete_image(self, image_id: str) -> bool:
        """
        从检索库中删除图片

        Args:
            image_id: 图片ID

        Returns:
            bool: 是否删除成功
        """
        self._ensure_collection()

        try:
            self._collection.delete(ids=[image_id])
            logger.info(f"图片已从检索库删除: {image_id}")
            return True
        except Exception as e:
            logger.error(f"图片删除失败: {e}", exc_info=True)
            return False

    def get_stats(self) -> dict:
        """
        获取图片检索库统计信息

        Returns:
            dict: 统计信息
        """
        self._ensure_collection()

        try:
            count = self._collection.count()
            return {
                "collection_name": self.collection_name,
                "total_images": count,
                "image_dir": self.image_dir,
                "status": "active",
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}", exc_info=True)
            return {
                "collection_name": self.collection_name,
                "total_images": 0,
                "image_dir": self.image_dir,
                "status": "error",
                "error": str(e),
            }


# 全局图片检索器单例
_image_retriever_instance: Optional[ImageRetriever] = None


def get_image_retriever() -> ImageRetriever:
    """获取全局图片检索器实例"""
    global _image_retriever_instance
    if _image_retriever_instance is None:
        _image_retriever_instance = ImageRetriever()
    return _image_retriever_instance
