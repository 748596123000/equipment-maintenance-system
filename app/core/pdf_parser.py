"""
PDF文档解析模块

使用PyMuPDF和pdfplumber解析PDF文档，提取：
- 文本内容（含段落结构和标题层级）
- 表格数据
- 图片信息
- 文档元数据（标题、作者、页数等）

支持多种PDF格式，包括扫描件（需配合OCR）。
"""

import logging
import os
import re
import base64
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import pdfplumber

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TableData:
    """表格数据结构"""
    page_number: int
    rows: List[List[str]]
    caption: Optional[str] = None


@dataclass
class ImageInfo:
    """图片信息结构"""
    page_number: int
    image_index: int
    width: int
    height: int
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    image_bytes: Optional[bytes] = None
    image_format: str = "png"
    caption: Optional[str] = None


@dataclass
class PDFPage:
    """PDF页面数据"""
    page_number: int
    text: str
    tables: List[TableData] = field(default_factory=list)
    images: List[ImageInfo] = field(default_factory=list)


@dataclass
class PDFDocument:
    """PDF文档解析结果"""
    filename: str
    title: Optional[str]
    author: Optional[str]
    total_pages: int
    pages: List[PDFPage]
    metadata: dict = field(default_factory=dict)


@dataclass
class TextParagraph:
    """结构化文本段落，包含页码、标题级别和内容"""
    page: int
    title: str
    content: str
    level: int = 0  # 0=正文, 1=一级标题, 2=二级标题, 3=三级标题


class PDFParser:
    """
    PDF文档解析器

    使用PyMuPDF提取文本和图片，使用pdfplumber提取表格数据。
    支持增量解析，可按页处理大文件。

    Attributes:
        file_path: PDF文件路径
        max_pages: 最大解析页数限制
    """

    # 标题层级判断的正则模式（按优先级排列）
    HEADING_PATTERNS = [
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

    # 字体大小与标题层级的映射阈值
    FONT_SIZE_THRESHOLDS = {
        1: 18.0,   # 一级标题：大于等于18磅
        2: 14.0,   # 二级标题：大于等于14磅
        3: 12.0,   # 三级标题：大于等于12磅
    }

    def __init__(self, file_path: str, max_pages: Optional[int] = None):
        """
        初始化PDF解析器

        Args:
            file_path: PDF文件路径
            max_pages: 最大解析页数，None表示不限制
        """
        self.file_path = file_path
        self.max_pages = max_pages
        self._doc: Optional[fitz.Document] = None

    def _open_document(self) -> fitz.Document:
        """
        打开PDF文档

        Returns:
            fitz.Document: 打开的PDF文档对象

        Raises:
            FileNotFoundError: 文件不存在
            RuntimeError: 文件加密或损坏
        """
        if self._doc is not None:
            return self._doc

        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"PDF文件不存在: {self.file_path}")

        try:
            self._doc = fitz.open(self.file_path)
        except fitz.FileDataError as e:
            raise RuntimeError(f"PDF文件损坏或格式不支持: {e}")
        except Exception as e:
            raise RuntimeError(f"打开PDF文件失败: {e}")

        # 检查是否加密
        if self._doc.is_encrypted:
            try:
                # 尝试用空密码解密
                self._doc.authenticate("")
            except Exception:
                self._doc.close()
                self._doc = None
                raise RuntimeError("PDF文件已加密，无法解析")

        return self._doc

    def _close_document(self) -> None:
        """关闭PDF文档，释放资源"""
        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:
                pass
            self._doc = None

    def get_metadata(self) -> dict:
        """
        获取PDF文档元数据

        Returns:
            dict: 包含title, author, subject, keywords, creator,
                  producer, creation_date, modification_date, total_pages等
        """
        doc = self._open_document()
        metadata = {
            "title": (doc.metadata.get("title") or "").strip(),
            "author": (doc.metadata.get("author") or "").strip(),
            "subject": (doc.metadata.get("subject") or "").strip(),
            "keywords": (doc.metadata.get("keywords") or "").strip(),
            "creator": (doc.metadata.get("creator") or "").strip(),
            "producer": (doc.metadata.get("producer") or "").strip(),
            "creation_date": doc.metadata.get("creationDate", ""),
            "modification_date": doc.metadata.get("modDate", ""),
            "total_pages": len(doc),
            "format": doc.metadata.get("format", ""),
            "encrypted": doc.is_encrypted,
        }
        logger.info(f"提取元数据完成: {self.file_path}, 共 {metadata['total_pages']} 页")
        return metadata

    def extract_text(self) -> List[TextParagraph]:
        """
        提取全部文本，返回结构化数据

        使用PyMuPDF的TextDict模式提取文本，通过字体大小和样式
        判断标题层级，保留章节结构。

        Returns:
            List[TextParagraph]: 结构化文本段落列表，每个包含
                page(页码), title(所属章节标题), content(内容), level(标题级别)
        """
        doc = self._open_document()
        total_pages = len(doc)
        if self.max_pages is not None:
            total_pages = min(total_pages, self.max_pages)

        paragraphs: List[TextParagraph] = []
        current_title = ""
        current_level = 0

        for page_num in range(1, total_pages + 1):
            try:
                page = doc[page_num - 1]

                # 使用 textdict 模式提取，保留字体信息
                blocks = page.get_text("dict")["blocks"]

                page_text_parts = []
                page_title = current_title
                page_level = current_level

                for block in blocks:
                    if block["type"] != 0:  # 只处理文本块，跳过图片块
                        continue

                    for line in block.get("lines", []):
                        line_text = ""
                        line_font_size = 0.0
                        is_bold = False

                        for span in line.get("spans", []):
                            line_text += span.get("text", "")
                            span_size = span.get("size", 0)
                            if span_size > line_font_size:
                                line_font_size = span_size
                            # 检查是否加粗
                            font_name = span.get("font", "").lower()
                            if "bold" in font_name or "black" in font_name or "heavy" in font_name:
                                is_bold = True

                        line_text = line_text.strip()
                        if not line_text:
                            continue

                        # 判断是否为标题
                        heading_level = self._detect_heading_level(line_text, line_font_size, is_bold)

                        if heading_level > 0:
                            # 这是一个标题行
                            # 先保存之前累积的正文内容
                            if page_text_parts:
                                combined_content = "\n".join(page_text_parts).strip()
                                if combined_content:
                                    paragraphs.append(TextParagraph(
                                        page=page_num,
                                        title=page_title,
                                        content=combined_content,
                                        level=0,
                                    ))
                                page_text_parts = []

                            # 更新当前标题
                            current_title = line_text
                            current_level = heading_level
                            page_title = current_title
                            page_level = current_level

                            # 将标题本身也作为一个段落保存
                            paragraphs.append(TextParagraph(
                                page=page_num,
                                title=line_text,
                                content=line_text,
                                level=heading_level,
                            ))
                        else:
                            # 正文内容
                            page_text_parts.append(line_text)

                    # 块之间添加段落分隔
                    page_text_parts.append("")

                # 保存页面剩余的正文内容
                if page_text_parts:
                    combined_content = "\n".join(page_text_parts).strip()
                    if combined_content:
                        paragraphs.append(TextParagraph(
                            page=page_num,
                            title=page_title,
                            content=combined_content,
                            level=0,
                        ))

            except Exception as e:
                logger.error(f"提取第 {page_num} 页文本失败: {e}", exc_info=True)
                # 降级为简单文本提取
                try:
                    page = doc[page_num - 1]
                    simple_text = page.get_text("text").strip()
                    if simple_text:
                        paragraphs.append(TextParagraph(
                            page=page_num,
                            title=current_title,
                            content=simple_text,
                            level=0,
                        ))
                except Exception as inner_e:
                    logger.error(f"降级提取第 {page_num} 页文本也失败: {inner_e}")

        logger.info(f"文本提取完成: 共 {len(paragraphs)} 个段落")
        return paragraphs

    def _detect_heading_level(self, text: str, font_size: float, is_bold: bool) -> int:
        """
        检测文本行的标题层级

        综合使用正则模式匹配和字体大小判断来确定标题层级。

        Args:
            text: 文本行内容
            font_size: 字体大小（磅）
            is_bold: 是否加粗

        Returns:
            int: 标题层级（0=非标题, 1=一级标题, 2=二级标题, 3=三级标题）
        """
        text_stripped = text.strip()
        if not text_stripped:
            return 0

        # 方法1：正则模式匹配
        for pattern, level in self.HEADING_PATTERNS:
            if re.match(pattern, text_stripped):
                return level

        # 方法2：基于字体大小判断
        if font_size >= self.FONT_SIZE_THRESHOLDS[1]:
            return 1
        elif font_size >= self.FONT_SIZE_THRESHOLDS[2]:
            return 2
        elif font_size >= self.FONT_SIZE_THRESHOLDS[3] and is_bold:
            return 3

        # 方法3：短行且加粗也可能是标题
        if is_bold and len(text_stripped) <= 30 and not text_stripped.endswith(("。", "，", "；")):
            return 3

        return 0

    def extract_tables(self) -> List[TableData]:
        """
        提取PDF中所有表格数据

        使用pdfplumber进行表格识别和提取。

        Returns:
            List[TableData]: 表格数据列表，每个包含页码、行数据和可选标题
        """
        doc = self._open_document()
        total_pages = len(doc)
        if self.max_pages is not None:
            total_pages = min(total_pages, self.max_pages)

        all_tables: List[TableData] = []

        try:
            with pdfplumber.open(self.file_path) as pdf:
                for page_num in range(1, total_pages + 1):
                    try:
                        pdf_page = pdf.pages[page_num - 1]
                        tables = pdf_page.extract_tables()

                        if not tables:
                            continue

                        for table_idx, table in enumerate(tables):
                            # 清理表格数据：去除None值，去除首尾空白
                            cleaned_rows = []
                            for row in table:
                                cleaned_row = []
                                for cell in row:
                                    if cell is None:
                                        cleaned_row.append("")
                                    else:
                                        cleaned_row.append(cell.strip())
                                # 跳过全空行
                                if any(cell for cell in cleaned_row):
                                    cleaned_rows.append(cleaned_row)

                            if cleaned_rows:
                                # 尝试从表格前的文本中提取表格标题
                                caption = self._extract_table_caption(pdf_page, table_idx)

                                table_data = TableData(
                                    page_number=page_num,
                                    rows=cleaned_rows,
                                    caption=caption,
                                )
                                all_tables.append(table_data)

                    except Exception as e:
                        logger.error(f"提取第 {page_num} 页表格失败: {e}", exc_info=True)
                        continue

        except Exception as e:
            logger.error(f"使用pdfplumber打开PDF失败: {e}", exc_info=True)
            logger.warning("表格提取失败，继续使用PyMuPDF提取文本")

        logger.info(f"表格提取完成: 共提取 {len(all_tables)} 个表格")
        return all_tables

    def _extract_table_caption(self, pdf_page, table_index: int) -> Optional[str]:
        """
        尝试从页面文本中提取表格标题

        通常表格标题在表格上方，包含"表"字或"Table"字样。

        Args:
            pdf_page: pdfplumber页面对象
            table_index: 表格在页面中的索引

        Returns:
            Optional[str]: 表格标题，未找到则返回None
        """
        try:
            text = pdf_page.extract_text() or ""
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            # 查找包含"表"或"Table"的行
            for line in lines:
                if re.search(r"(?:表\s*\d+|Table\s*\d+)", line, re.IGNORECASE):
                    return line

            # 如果没有明确的表格编号，取表格上方最近的短行作为标题
            if lines:
                for line in reversed(lines):
                    if len(line) <= 50 and not line.endswith(("。", "；")):
                        return line

        except Exception as e:
            logger.debug(f"提取表格标题失败: {e}")

        return None

    def extract_images(self, output_dir: Optional[str] = None) -> List[ImageInfo]:
        """
        提取PDF中的图片，保存到指定目录

        使用PyMuPDF提取嵌入图片，并保存为文件。

        Args:
            output_dir: 图片保存目录，默认使用配置中的IMAGE_DIR

        Returns:
            List[ImageInfo]: 图片信息列表
        """
        doc = self._open_document()
        total_pages = len(doc)
        if self.max_pages is not None:
            total_pages = min(total_pages, self.max_pages)

        if output_dir is None:
            output_dir = settings.IMAGE_DIR

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        all_images: List[ImageInfo] = []
        filename_base = os.path.splitext(os.path.basename(self.file_path))[0]

        for page_num in range(1, total_pages + 1):
            try:
                page = doc[page_num - 1]
                image_list = page.get_images(full=True)

                for img_index, img_info in enumerate(image_list):
                    try:
                        xref = img_info[0]
                        base_image = doc.extract_image(xref)

                        if base_image is None:
                            continue

                        image_bytes = base_image.get("image")
                        if not image_bytes or len(image_bytes) < 100:
                            # 跳过太小的图片（可能是装饰元素）
                            continue

                        # 获取图片在页面中的位置
                        bbox = self._get_image_bbox(page, xref, img_index)

                        # 保存图片到文件
                        image_format = base_image.get("ext", "png")
                        image_filename = f"{filename_base}_p{page_num}_img{img_index}.{image_format}"
                        image_path = os.path.join(output_dir, image_filename)

                        with open(image_path, "wb") as f:
                            f.write(image_bytes)

                        image_info = ImageInfo(
                            page_number=page_num,
                            image_index=img_index,
                            width=base_image.get("width", 0),
                            height=base_image.get("height", 0),
                            bbox=bbox,
                            image_bytes=image_bytes,
                            image_format=image_format,
                        )
                        all_images.append(image_info)

                    except Exception as e:
                        logger.debug(f"提取第 {page_num} 页第 {img_index} 张图片失败: {e}")
                        continue

            except Exception as e:
                logger.error(f"处理第 {page_num} 页图片时失败: {e}", exc_info=True)

        logger.info(f"图片提取完成: 共提取 {len(all_images)} 张图片，保存至 {output_dir}")
        return all_images

    def _get_image_bbox(
        self, page: fitz.Page, xref: int, img_index: int
    ) -> Tuple[float, float, float, float]:
        """
        获取图片在页面中的位置（边界框）

        Args:
            page: PyMuPDF页面对象
            xref: 图片的内部引用编号
            img_index: 图片索引

        Returns:
            Tuple[float, float, float, float]: 边界框 (x0, y0, x1, y1)
        """
        try:
            # 遍历页面中的图片引用，找到匹配xref的图片位置
            for img in page.get_images(full=True):
                if img[0] == xref:
                    # 使用 page.get_image_rects 获取图片位置
                    rects = page.get_image_rects(xref)
                    if rects:
                        rect = rects[0]
                        return (rect.x0, rect.y0, rect.x1, rect.y1)
                    break
        except Exception as e:
            logger.debug(f"获取图片位置失败: {e}")

        return (0.0, 0.0, 0.0, 0.0)

    def _describe_image(self, image_bytes: bytes, image_format: str = "png") -> Optional[str]:
        try:
            from app.services.vision_service import get_vision_service
            vision = get_vision_service()
            result = vision.describe_image(image_bytes, image_format)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"视觉模型调用失败: {e}")

        if not settings.dashscope_api_key:
            logger.debug("未配置DASHSCOPE_API_KEY，跳过图片描述生成")
            return None

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.dashscope_api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )

            # 将图片转为base64
            mime_type = "image/jpeg" if image_format in ("jpg", "jpeg") else "image/png"
            base64_str = base64.b64encode(image_bytes).decode("utf-8")

            response = client.chat.completions.create(
                model="qwen-vl-max",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{base64_str}"}
                        },
                        {
                            "type": "text",
                            "text": "请详细描述这张设备检修相关图片的内容，包括设备名称、部件、操作步骤等"
                        }
                    ]
                }],
                max_tokens=300
            )

            description = response.choices[0].message.content
            logger.debug(f"图片描述生成成功: {description[:50]}...")
            return description

        except Exception as e:
            logger.warning(f"调用通义千问多模态模型失败: {e}")
            return None

    def _extract_and_describe_images(
        self, output_dir: str, filename_base: str
    ) -> List[Dict]:
        """
        提取PDF中的图片并生成描述，每页最多处理3张

        Args:
            output_dir: 图片保存目录
            filename_base: 文件名基础部分（不含扩展名）

        Returns:
            List[Dict]: 图片描述段落列表，每个包含 page, title, content, level, metadata
        """
        doc = self._open_document()
        total_pages = len(doc)
        if self.max_pages is not None:
            total_pages = min(total_pages, self.max_pages)

        os.makedirs(output_dir, exist_ok=True)

        image_descriptions: List[Dict] = []
        max_images_per_page = 3

        for page_num in range(1, total_pages + 1):
            try:
                page = doc[page_num - 1]
                image_list = page.get_images(full=True)

                images_to_process = image_list[:max_images_per_page]

                def _describe_image_task(img_data, page_num, img_idx):
                    try:
                        xref = img_data[0]
                        base_image = doc.extract_image(xref)

                        if base_image is None:
                            return None

                        image_bytes = base_image.get("image")
                        if not image_bytes or len(image_bytes) < 100:
                            return None

                        image_format = base_image.get("ext", "png")
                        image_filename = f"{filename_base}_p{page_num}_img{img_idx}.{image_format}"
                        image_path = os.path.join(output_dir, image_filename)

                        with open(image_path, "wb") as f:
                            f.write(image_bytes)

                        description = self._describe_image(image_bytes, image_format)

                        result_item = {
                            "page": page_num,
                            "title": f"[图片描述] 第{page_num}页图片{img_idx + 1}",
                            "content": f"[图片描述] {description}" if description else f"[图片] 第{page_num}页图片{img_idx + 1}",
                            "level": 0,
                            "metadata": {
                                "type": "image",
                                "page": page_num,
                                "image_path": image_path,
                                "image_index": img_idx,
                                "has_description": bool(description),
                            },
                        }
                        return result_item
                    except Exception as e:
                        logger.debug(f"处理第{page_num}页第{img_idx}张图片失败: {e}")
                        return None

                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = []
                    for img_index, img_info in enumerate(images_to_process):
                        futures.append(executor.submit(_describe_image_task, img_info, page_num, img_index))
                    for future in as_completed(futures):
                        result = future.result()
                        if result:
                            image_descriptions.append(result)
                            logger.info(f"已生成第{result['page']}页第{result['metadata']['image_index'] + 1}张图片的描述")

            except Exception as e:
                logger.error(f"处理第{page_num}页图片时失败: {e}", exc_info=True)

        logger.info(f"图片描述生成完成: 共处理 {len(image_descriptions)} 张图片")
        return image_descriptions

    def parse_pdf(self) -> dict:
        """
        主入口：解析PDF文档，返回完整的解析结果

        整合文本提取、表格提取、图片提取和图片描述生成，
        返回统一的结构化数据。图片描述通过通义千问多模态模型
        自动生成，作为特殊段落加入解析结果。

        Returns:
            dict: 完整的解析结果，包含以下字段：
                - filename: 文件名
                - metadata: 文档元数据
                - paragraphs: 文本段落列表（含图片描述段落），每个包含 page, title, content, level
                - tables: 表格数据列表
                - images: 图片信息列表
                - total_pages: 总页数
        """
        doc = self._open_document()
        total_pages = len(doc)
        if self.max_pages is not None:
            total_pages = min(total_pages, self.max_pages)

        logger.info(f"开始解析PDF: {self.file_path}, 共 {total_pages} 页")

        # 提取元数据
        metadata = self.get_metadata()

        # 提取结构化文本
        paragraphs = self.extract_text()

        # 提取表格
        tables = self.extract_tables()

        # 提取图片（保存到默认目录）
        images = self.extract_images()

        # 提取图片并生成描述（每页最多3张）
        filename_base = os.path.splitext(os.path.basename(self.file_path))[0]
        image_descriptions = self._extract_and_describe_images(
            output_dir=settings.IMAGE_DIR,
            filename_base=filename_base,
        )

        # 将图片描述段落合并到文本段落中，按页码排序插入
        all_paragraphs = []
        text_para_idx = 0
        img_desc_idx = 0

        # 将普通段落转为字典列表
        text_paragraphs = [
            {
                "page": p.page,
                "title": p.title,
                "content": p.content,
                "level": p.level,
            }
            for p in paragraphs
        ]

        # 按页码合并：图片描述插入到对应页码的文本段落之后
        while text_para_idx < len(text_paragraphs) or img_desc_idx < len(image_descriptions):
            if text_para_idx < len(text_paragraphs):
                text_page = text_paragraphs[text_para_idx]["page"]
            else:
                text_page = float("inf")

            if img_desc_idx < len(image_descriptions):
                img_page = image_descriptions[img_desc_idx]["page"]
            else:
                img_page = float("inf")

            # 优先添加文本段落
            if text_page <= img_page:
                all_paragraphs.append(text_paragraphs[text_para_idx])
                text_para_idx += 1
                # 如果图片描述的页码等于当前文本段落页码，插入图片描述
                while img_desc_idx < len(image_descriptions) and image_descriptions[img_desc_idx]["page"] <= text_page:
                    all_paragraphs.append(image_descriptions[img_desc_idx])
                    img_desc_idx += 1
            else:
                all_paragraphs.append(image_descriptions[img_desc_idx])
                img_desc_idx += 1

        # 添加剩余的图片描述
        while img_desc_idx < len(image_descriptions):
            all_paragraphs.append(image_descriptions[img_desc_idx])
            img_desc_idx += 1

        # 构建完整的解析结果
        result = {
            "filename": os.path.basename(self.file_path),
            "metadata": metadata,
            "paragraphs": all_paragraphs,
            "tables": [
                {
                    "page_number": t.page_number,
                    "rows": t.rows,
                    "caption": t.caption,
                }
                for t in tables
            ],
            "images": [
                {
                    "page_number": img.page_number,
                    "image_index": img.image_index,
                    "width": img.width,
                    "height": img.height,
                    "format": img.image_format,
                    "caption": img.caption,
                }
                for img in images
            ],
            "total_pages": total_pages,
            "paragraph_count": len(all_paragraphs),
            "table_count": len(tables),
            "image_count": len(images),
        }

        self._close_document()
        logger.info(
            f"PDF解析完成: {self.file_path}, "
            f"段落={len(all_paragraphs)}, 表格={len(tables)}, 图片={len(images)}, "
            f"图片描述={len(image_descriptions)}"
        )
        return result

    def parse_page(self, page_number: int) -> PDFPage:
        """
        解析单个页面，提取文本、表格和图片

        Args:
            page_number: 页码（从1开始）

        Returns:
            PDFPage: 页面解析结果

        Raises:
            ValueError: 页码超出范围
        """
        doc = self._open_document()
        if page_number < 1 or page_number > len(doc):
            raise ValueError(f"页码超出范围: {page_number}, 文档共 {len(doc)} 页")

        # 提取文本
        page = doc[page_number - 1]
        text = page.get_text("text").strip()

        # 提取表格
        tables = self._extract_tables_for_page(page_number)

        # 提取图片
        images = self._extract_images_for_page(page_number)

        return PDFPage(
            page_number=page_number,
            text=text,
            tables=tables,
            images=images,
        )

    def _extract_tables_for_page(self, page_number: int) -> List[TableData]:
        """
        提取指定页面的表格数据

        Args:
            page_number: 页码（从1开始）

        Returns:
            List[TableData]: 表格数据列表
        """
        try:
            with pdfplumber.open(self.file_path) as pdf:
                pdf_page = pdf.pages[page_number - 1]
                tables = pdf_page.extract_tables()

                result = []
                for table_idx, table in enumerate(tables):
                    cleaned_rows = []
                    for row in table:
                        cleaned_row = [cell.strip() if cell else "" for cell in row]
                        if any(cell for cell in cleaned_row):
                            cleaned_rows.append(cleaned_row)

                    if cleaned_rows:
                        caption = self._extract_table_caption(pdf_page, table_idx)
                        result.append(TableData(
                            page_number=page_number,
                            rows=cleaned_rows,
                            caption=caption,
                        ))

                return result

        except Exception as e:
            logger.error(f"提取第 {page_number} 页表格失败: {e}", exc_info=True)
            return []

    def _extract_images_for_page(self, page_number: int) -> List[ImageInfo]:
        """
        提取指定页面的图片信息

        Args:
            page_number: 页码（从1开始）

        Returns:
            List[ImageInfo]: 图片信息列表
        """
        doc = self._open_document()
        page = doc[page_number - 1]
        images = []
        image_list = page.get_images(full=True)

        for img_index, img_info in enumerate(image_list):
            try:
                xref = img_info[0]
                base_image = doc.extract_image(xref)

                if base_image is None:
                    continue

                image_bytes = base_image.get("image")
                if not image_bytes or len(image_bytes) < 100:
                    continue

                bbox = self._get_image_bbox(page, xref, img_index)

                images.append(ImageInfo(
                    page_number=page_number,
                    image_index=img_index,
                    width=base_image.get("width", 0),
                    height=base_image.get("height", 0),
                    bbox=bbox,
                    image_bytes=image_bytes,
                    image_format=base_image.get("ext", "png"),
                ))

            except Exception as e:
                logger.debug(f"提取第 {page_number} 页第 {img_index} 张图片失败: {e}")
                continue

        return images

    def parse(self) -> PDFDocument:
        """
        解析整个PDF文档（兼容旧接口）

        Returns:
            PDFDocument: 完整的文档解析结果
        """
        doc = self._open_document()
        total_pages = len(doc)

        if self.max_pages is not None:
            total_pages = min(total_pages, self.max_pages)

        logger.info(f"开始解析PDF: {self.file_path}, 共 {total_pages} 页")

        metadata = self.get_metadata()
        pages = []

        for page_num in range(1, total_pages + 1):
            try:
                page = self.parse_page(page_num)
                pages.append(page)
                logger.debug(f"页面 {page_num}/{total_pages} 解析完成")
            except Exception as e:
                logger.error(f"页面 {page_num} 解析失败: {e}")
                pages.append(PDFPage(page_number=page_num, text=""))

        result = PDFDocument(
            filename=os.path.basename(self.file_path),
            title=metadata.get("title"),
            author=metadata.get("author"),
            total_pages=total_pages,
            pages=pages,
            metadata=metadata,
        )

        self._close_document()
        logger.info(f"PDF解析完成: {self.file_path}")
        return result

    def get_full_text(self) -> str:
        """
        获取文档全部文本内容（按页拼接）

        Returns:
            str: 完整文本
        """
        doc = self.parse()
        full_text = "\n".join(page.text for page in doc.pages if page.text.strip())
        return full_text

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口，确保资源释放"""
        self._close_document()
