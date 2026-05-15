"""
文本分块模块

将长文本按照语义结构进行智能分块，支持：
- 按章节/标题结构分块（StructuredChunker）
- 固定长度分块（FixedSizeChunker，带重叠）
- 表格和图片关联分块
- 从PDF解析结果直接分块的主入口

分块策略优先级：章节结构 > 段落语义 > 固定长度
每个chunk包含：content, metadata(source, page, chapter, device_model, chunk_index)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """
    文本块数据结构

    Attributes:
        chunk_id: 文本块唯一标识
        content: 文本内容
        chunk_type: 文本块类型 (text/table/image_context)
        page_number: 来源页码
        section_title: 所属章节标题
        document_id: 来源文档ID
        metadata: 附加元数据（source, page, chapter, device_model, chunk_index等）
    """
    chunk_id: str
    content: str
    chunk_type: str = "text"
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    document_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class StructuredChunker:
    """
    结构化分块器：按文档结构（标题层级）进行智能分块

    根据标题层级将文本分割为章节，章节内按段落分块，
    超长段落再按固定大小分块。每个chunk保留标题信息作为上下文前缀。

    Attributes:
        chunk_size: 分块大小（字符数）
        chunk_overlap: 分块重叠大小（字符数）
    """

    # 常见章节标题模式（按优先级排列）
    SECTION_PATTERNS = [
        # "第一章 xxx" / "第一节 xxx" / "第一篇 xxx"
        (r"^第[一二三四五六七八九十百]+[章节篇部]\s*.+", 1),
        # "一、xxx" / "二、xxx"
        (r"^[一二三四五六七八九十]+[、.．]\s*.+", 2),
        # "1.1 xxx" / "1.1.1 xxx" (多级编号)
        (r"^\d{1,2}\.\d{1,2}(\.\d{1,2})+\s*.+", 3),
        # "1. xxx" / "1、xxx"
        (r"^\d{1,2}[.、．]\s*.+", 2),
        # "A. xxx" / "B. xxx"
        (r"^[A-Z][.、．]\s*.+", 3),
        # "(一) xxx" / "(二) xxx"
        (r"^（[一二三四五六七八九十]+）\s*.+", 3),
        # 常见章节关键词
        (r"^(?:摘要|引言|背景|目的|方法|结果|讨论|结论|参考文献|附录|目录|前言|概述|说明)\s*", 1),
    ]

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        """
        初始化结构化分块器

        Args:
            chunk_size: 分块大小，默认从配置读取
            chunk_overlap: 分块重叠大小，默认从配置读取
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def _detect_heading_level(self, line: str) -> int:
        """
        检测文本行的标题层级

        Args:
            line: 文本行

        Returns:
            int: 标题层级（0=非标题, 1/2/3=标题级别）
        """
        line = line.strip()
        if not line:
            return 0

        for pattern, level in self.SECTION_PATTERNS:
            if re.match(pattern, line):
                return level

        return 0

    def _split_by_sections(self, text: str) -> List[dict]:
        """
        按章节标题分割文本

        Args:
            text: 原始文本

        Returns:
            List[dict]: 章节列表，每项包含 title, level, content
        """
        lines = text.split("\n")
        sections = []
        current_section = {"title": "", "level": 0, "content": ""}

        for line in lines:
            heading_level = self._detect_heading_level(line)
            if heading_level > 0:
                # 保存上一个章节
                if current_section["content"].strip():
                    sections.append(current_section)
                current_section = {"title": line.strip(), "level": heading_level, "content": ""}
            else:
                current_section["content"] += line + "\n"

        # 保存最后一个章节
        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """
        按段落分割文本

        Args:
            text: 原始文本

        Returns:
            List[str]: 段落列表
        """
        paragraphs = re.split(r'\n\s*\n|\n{2,}', text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _fixed_size_chunk(self, text: str) -> List[str]:
        """
        固定大小分块（带重叠），优先在句号等位置断句

        Args:
            text: 原始文本

        Returns:
            List[str]: 文本块列表
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]

            # 尝试在句号、换行等位置断句
            if end < len(text):
                last_period = max(
                    chunk.rfind("。"),
                    chunk.rfind("！"),
                    chunk.rfind("？"),
                    chunk.rfind("\n"),
                )
                if last_period > self.chunk_size * 0.5:
                    chunk = text[start:last_period + 1]
                    end = start + last_period + 1

            chunks.append(chunk.strip())
            start = end - self.chunk_overlap
            if start >= len(text):
                break

        return [c for c in chunks if c]

    def chunk(
        self,
        text: str,
        document_id: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[TextChunk]:
        """
        按文档结构进行智能分块

        优先按章节分割，章节内按段落分块，
        超长段落再按固定大小分块。
        每个chunk的content前会添加所属章节标题作为上下文前缀。

        Args:
            text: 原始文本
            document_id: 文档ID
            source: 来源文档名

        Returns:
            List[TextChunk]: 文本块列表
        """
        chunks = []
        sections = self._split_by_sections(text)
        chunk_index = 0

        for section in sections:
            section_title = section["title"]
            section_level = section["level"]
            section_content = section["content"]

            if not section_content.strip():
                continue

            # 构建上下文前缀（包含父级标题信息）
            context_prefix = ""
            if section_title:
                context_prefix = f"【{section_title}】\n"

            # 如果章节内容较短，直接作为一个块
            if len(section_content) <= self.chunk_size:
                chunk_index += 1
                content = context_prefix + section_content.strip()
                chunks.append(TextChunk(
                    chunk_id=f"{document_id}_chunk_{chunk_index}" if document_id else f"chunk_{chunk_index}",
                    content=content,
                    chunk_type="text",
                    section_title=section_title,
                    document_id=document_id,
                    metadata={
                        "source": source or "",
                        "chapter": section_title,
                        "chunk_index": chunk_index,
                        "heading_level": section_level,
                    },
                ))
            else:
                # 章节内容较长，按段落分块
                paragraphs = self._split_by_paragraphs(section_content)
                current_chunk = ""

                for para in paragraphs:
                    if len(current_chunk) + len(para) <= self.chunk_size:
                        current_chunk += para + "\n"
                    else:
                        if current_chunk.strip():
                            chunk_index += 1
                            content = context_prefix + current_chunk.strip()
                            chunks.append(TextChunk(
                                chunk_id=f"{document_id}_chunk_{chunk_index}" if document_id else f"chunk_{chunk_index}",
                                content=content,
                                chunk_type="text",
                                section_title=section_title,
                                document_id=document_id,
                                metadata={
                                    "source": source or "",
                                    "chapter": section_title,
                                    "chunk_index": chunk_index,
                                    "heading_level": section_level,
                                },
                            ))

                        # 超长段落单独分块
                        if len(para) > self.chunk_size:
                            sub_chunks = self._fixed_size_chunk(para)
                            for sub in sub_chunks:
                                chunk_index += 1
                                content = context_prefix + sub
                                chunks.append(TextChunk(
                                    chunk_id=f"{document_id}_chunk_{chunk_index}" if document_id else f"chunk_{chunk_index}",
                                    content=content,
                                    chunk_type="text",
                                    section_title=section_title,
                                    document_id=document_id,
                                    metadata={
                                        "source": source or "",
                                        "chapter": section_title,
                                        "chunk_index": chunk_index,
                                        "heading_level": section_level,
                                    },
                                ))
                            current_chunk = ""
                        else:
                            current_chunk = para + "\n"

                # 保存剩余内容
                if current_chunk.strip():
                    chunk_index += 1
                    content = context_prefix + current_chunk.strip()
                    chunks.append(TextChunk(
                        chunk_id=f"{document_id}_chunk_{chunk_index}" if document_id else f"chunk_{chunk_index}",
                        content=content,
                        chunk_type="text",
                        section_title=section_title,
                        document_id=document_id,
                        metadata={
                            "source": source or "",
                            "chapter": section_title,
                            "chunk_index": chunk_index,
                            "heading_level": section_level,
                        },
                    ))

        logger.info(f"结构化分块完成: 共生成 {len(chunks)} 个文本块")
        return chunks


class FixedSizeChunker:
    """
    固定大小分块器：按固定长度分割文本，支持重叠

    适用于没有明确结构的文档或纯文本内容。

    Attributes:
        chunk_size: 分块大小（字符数）
        chunk_overlap: 分块重叠大小（字符数）
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        """
        初始化固定大小分块器

        Args:
            chunk_size: 分块大小，默认从配置读取
            chunk_overlap: 分块重叠大小，默认从配置读取
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def _split_text(self, text: str) -> List[str]:
        """
        固定大小分割文本（带重叠），优先在句号等位置断句

        Args:
            text: 原始文本

        Returns:
            List[str]: 文本块列表
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]

            # 尝试在句号、换行等位置断句
            if end < len(text):
                last_period = max(
                    chunk.rfind("。"),
                    chunk.rfind("！"),
                    chunk.rfind("？"),
                    chunk.rfind("；"),
                    chunk.rfind("\n"),
                )
                if last_period > self.chunk_size * 0.5:
                    chunk = text[start:last_period + 1]
                    end = start + last_period + 1

            chunks.append(chunk.strip())
            start = end - self.chunk_overlap
            if start >= len(text):
                break

        return [c for c in chunks if c]

    def chunk(
        self,
        text: str,
        document_id: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[TextChunk]:
        """
        固定大小分块

        Args:
            text: 原始文本
            document_id: 文档ID
            source: 来源文档名

        Returns:
            List[TextChunk]: 文本块列表
        """
        if not text or not text.strip():
            return []

        raw_chunks = self._split_text(text)
        chunks = []

        for i, content in enumerate(raw_chunks):
            chunks.append(TextChunk(
                chunk_id=f"{document_id}_chunk_{i + 1}" if document_id else f"chunk_{i + 1}",
                content=content,
                chunk_type="text",
                document_id=document_id,
                metadata={
                    "source": source or "",
                    "chunk_index": i + 1,
                },
            ))

        logger.info(f"固定大小分块完成: 共生成 {len(chunks)} 个文本块")
        return chunks


def chunk_documents(
    pdf_parse_result: dict,
    document_id: Optional[str] = None,
    strategy: str = "structure",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[TextChunk]:
    """
    主入口：接收PDF解析结果，返回分块列表

    将PDF解析器返回的结构化数据转换为文本块列表。
    支持结构化分块和固定大小分块两种策略。

    Args:
        pdf_parse_result: PDF解析结果（由PDFParser.parse_pdf()返回的字典）
        document_id: 文档ID
        strategy: 分块策略 ("structure" 或 "fixed_size")
        chunk_size: 分块大小（可选，覆盖默认配置）
        chunk_overlap: 分块重叠大小（可选，覆盖默认配置）

    Returns:
        List[TextChunk]: 文本块列表，每个包含 content 和 metadata
    """
    if not pdf_parse_result:
        logger.warning("PDF解析结果为空，返回空列表")
        return []

    filename = pdf_parse_result.get("filename", "")
    paragraphs = pdf_parse_result.get("paragraphs", [])
    tables = pdf_parse_result.get("tables", [])

    if not paragraphs and not tables:
        logger.warning("PDF解析结果中没有段落和表格数据")
        return []

    # 根据策略选择分块器
    if strategy == "structure":
        chunker = StructuredChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    elif strategy == "fixed_size":
        chunker = FixedSizeChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    else:
        raise ValueError(f"不支持的分块策略: {strategy}，可选: structure, fixed_size")

    # 将段落按章节组织成完整文本
    full_text = _build_full_text_from_paragraphs(paragraphs)

    # 执行分块
    chunks = chunker.chunk(
        text=full_text,
        document_id=document_id,
        source=filename,
    )

    # 为每个chunk补充页码信息
    _enrich_chunks_with_page_info(chunks, paragraphs)

    # 将表格数据也作为独立的chunk添加
    table_chunks = _create_table_chunks(tables, document_id, filename)
    chunks.extend(table_chunks)

    logger.info(
        f"文档分块完成: {filename}, "
        f"文本块={len(chunks) - len(table_chunks)}, 表格块={len(table_chunks)}, "
        f"总计={len(chunks)}"
    )
    return chunks


def _build_full_text_from_paragraphs(paragraphs: List[dict]) -> str:
    """
    将结构化段落列表重建为完整文本

    保留标题层级信息，用换行分隔段落。

    Args:
        paragraphs: 段落列表，每个包含 page, title, content, level

    Returns:
        str: 重建的完整文本
    """
    text_parts = []

    for para in paragraphs:
        content = para.get("content", "").strip()
        if not content:
            continue

        level = para.get("level", 0)
        # 标题级别的内容直接添加（分块器会识别为标题）
        text_parts.append(content)
        # 段落之间用空行分隔
        text_parts.append("")

    return "\n".join(text_parts)


def _enrich_chunks_with_page_info(
    chunks: List[TextChunk],
    paragraphs: List[dict],
) -> None:
    """
    为分块结果补充页码信息

    通过匹配chunk内容与段落内容来确定页码。

    Args:
        chunks: 文本块列表（会被原地修改）
        paragraphs: 原始段落列表
    """
    if not paragraphs:
        return

    # 建立内容到页码的映射
    content_page_map = {}
    for para in paragraphs:
        content = para.get("content", "").strip()
        if content:
            # 取内容的前50个字符作为匹配键
            key = content[:50]
            content_page_map[key] = para.get("page", 0)

    # 为每个chunk匹配页码
    for chunk in chunks:
        content = chunk.content.strip()
        if not content:
            continue

        # 移除可能的标题前缀后匹配
        match_content = content
        if match_content.startswith("【") and "】\n" in match_content:
            match_content = match_content.split("】\n", 1)[1].strip()

        # 尝试匹配
        match_key = match_content[:50]
        if match_key in content_page_map:
            chunk.page_number = content_page_map[match_key]
            chunk.metadata["page"] = content_page_map[match_key]
        else:
            # 模糊匹配：查找包含该内容的段落
            for key, page in content_page_map.items():
                if key in content or content[:30] in key:
                    chunk.page_number = page
                    chunk.metadata["page"] = page
                    break


def _create_table_chunks(
    tables: List[dict],
    document_id: Optional[str] = None,
    source: Optional[str] = None,
) -> List[TextChunk]:
    """
    将表格数据转换为文本块

    将表格的行列数据转换为可检索的文本格式。

    Args:
        tables: 表格数据列表
        document_id: 文档ID
        source: 来源文档名

    Returns:
        List[TextChunk]: 表格文本块列表
    """
    chunks = []
    base_index = 0  # 会在外部追加偏移

    for table in tables:
        page_number = table.get("page_number", 0)
        rows = table.get("rows", [])
        caption = table.get("caption", "")

        if not rows:
            continue

        # 将表格转换为文本格式
        table_text_parts = []
        if caption:
            table_text_parts.append(f"表格标题: {caption}")

        # 第一行作为表头
        if rows:
            header = " | ".join(rows[0])
            table_text_parts.append(f"表头: {header}")
            table_text_parts.append("-" * len(header))

            # 数据行
            for row in rows[1:]:
                row_text = " | ".join(row)
                table_text_parts.append(row_text)

        table_text = "\n".join(table_text_parts)

        # 如果表格文本过长，进行分块
        if len(table_text) > settings.CHUNK_SIZE * 2:
            # 按行分割大表格
            parts = []
            current_part = table_text_parts[:2]  # 包含标题和表头
            for row_text in table_text_parts[2:]:
                current_part.append(row_text)
                if len("\n".join(current_part)) > settings.CHUNK_SIZE:
                    parts.append("\n".join(current_part))
                    current_part = [table_text_parts[0], table_text_parts[1]]  # 保留标题和表头
            if len(current_part) > 2:
                parts.append("\n".join(current_part))

            for i, part in enumerate(parts):
                chunk_id = f"{document_id}_table_chunk_{len(chunks) + i + 1}" if document_id else f"table_chunk_{len(chunks) + i + 1}"
                chunks.append(TextChunk(
                    chunk_id=chunk_id,
                    content=part,
                    chunk_type="table",
                    page_number=page_number,
                    section_title=caption,
                    document_id=document_id,
                    metadata={
                        "source": source or "",
                        "page": page_number,
                        "chapter": caption or "",
                        "chunk_index": len(chunks) + i + 1,
                        "is_table": True,
                    },
                ))
        else:
            chunk_id = f"{document_id}_table_chunk_{len(chunks) + 1}" if document_id else f"table_chunk_{len(chunks) + 1}"
            chunks.append(TextChunk(
                chunk_id=chunk_id,
                content=table_text,
                chunk_type="table",
                page_number=page_number,
                section_title=caption,
                document_id=document_id,
                metadata={
                    "source": source or "",
                    "page": page_number,
                    "chapter": caption or "",
                    "chunk_index": len(chunks) + 1,
                    "is_table": True,
                },
            ))

    return chunks


# ========== 兼容旧接口 ==========

class TextChunker:
    """
    文本分块器（兼容旧接口）

    内部委托给StructuredChunker和FixedSizeChunker实现。
    """

    SECTION_PATTERNS = [
        r"^第[一二三四五六七八九十百]+[章节篇]\s*.+",
        r"^[一二三四五六七八九十]+[、.]\s*.+",
        r"^\d+[.、]\s*.+",
        r"^[A-Z][.、]\s*.+",
        r"^[\d.]+\s+.+",
        r"^(?:摘要|引言|背景|目的|方法|结果|讨论|结论|参考文献|附录)\s*",
    ]

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self._structured_chunker = StructuredChunker(chunk_size, chunk_overlap)
        self._fixed_chunker = FixedSizeChunker(chunk_size, chunk_overlap)

    def _is_section_heading(self, line: str) -> bool:
        """判断一行文本是否为章节标题"""
        line = line.strip()
        if not line:
            return False
        for pattern in self.SECTION_PATTERNS:
            if re.match(pattern, line):
                return True
        if len(line) <= 30 and not line.endswith("。"):
            return True
        return False

    def _split_by_sections(self, text: str) -> List[dict]:
        """按章节标题分割文本"""
        lines = text.split("\n")
        sections = []
        current_section = {"title": "", "content": ""}

        for line in lines:
            if self._is_section_heading(line):
                if current_section["content"].strip():
                    sections.append(current_section)
                current_section = {"title": line.strip(), "content": ""}
            else:
                current_section["content"] += line + "\n"

        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """按段落分割文本"""
        paragraphs = re.split(r'\n\s*\n|\n{2,}', text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _fixed_size_chunk(self, text: str) -> List[str]:
        """固定大小分块（带重叠）"""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]

            if end < len(text):
                last_period = max(
                    chunk.rfind("。"),
                    chunk.rfind("！"),
                    chunk.rfind("？"),
                    chunk.rfind("\n"),
                )
                if last_period > self.chunk_size * 0.5:
                    chunk = text[start:last_period + 1]
                    end = start + last_period + 1

            chunks.append(chunk.strip())
            start = end - self.chunk_overlap

        return [c for c in chunks if c]

    def chunk_by_structure(
        self,
        text: str,
        document_id: Optional[str] = None,
    ) -> List[TextChunk]:
        """按文档结构进行智能分块"""
        return self._structured_chunker.chunk(text, document_id)

    def chunk_by_fixed_size(
        self,
        text: str,
        document_id: Optional[str] = None,
    ) -> List[TextChunk]:
        """固定大小分块"""
        return self._fixed_chunker.chunk(text, document_id)

    def chunk(
        self,
        text: str,
        document_id: Optional[str] = None,
        strategy: str = "structure",
    ) -> List[TextChunk]:
        """
        文本分块入口方法

        Args:
            text: 原始文本
            document_id: 文档ID
            strategy: 分块策略 (structure/fixed_size)

        Returns:
            List[TextChunk]: 文本块列表
        """
        if not text or not text.strip():
            logger.warning("输入文本为空，返回空列表")
            return []

        if strategy == "structure":
            return self.chunk_by_structure(text, document_id)
        elif strategy == "fixed_size":
            return self.chunk_by_fixed_size(text, document_id)
        else:
            raise ValueError(f"不支持的分块策略: {strategy}，可选: structure, fixed_size")
