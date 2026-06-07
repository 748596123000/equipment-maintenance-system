"""
PDF文档解析模块（无 PyMuPDF 依赖版）

使用 pdfplumber + pdfminer.six 解析 PDF 文档，提取：
- 文本内容（含段落结构和标题层级）
- 表格数据
- 图片信息（嵌入图片 + 整页渲染图，兼容扫描件）
- 文档元数据（标题、作者、页数等）

支持的 PDF 类型：
- 文本型 PDF（直接提取文本）
- 扫描件 PDF（无文本层，整页渲染为图片，AI 视觉分析）
- 混合型 PDF（部分页有文本，部分页是图片）

设计目标：在 LoongArch 等无 PyMuPDF 预编译 wheel 的平台上也能正常运行。
"""

import io
import logging
import os
import re
import base64
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

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
    PDF文档解析器（无 PyMuPDF 依赖）

    使用 pdfplumber 提取文本和表格，使用 pdfplumber + pdfminer 提取嵌入图片，
    整页渲染通过 pdfplumber 的 page.to_image() 完成（兼容扫描件）。

    Attributes:
        file_path: PDF文件路径
        max_pages: 最大解析页数限制
    """

    HEADING_PATTERNS = [
        (r"^第[一二三四五六七八九十百]+[章节篇部]\s*.+", 1),
        (r"^[一二三四五六七八九十]+[、.．]\s*.+", 2),
        (r"^\d{1,2}\.\d{1,2}(\.\d{1,2})+\s*.+", 3),
        (r"^\d{1,2}[.、．]\s*.+", 2),
        (r"^[A-Z][.、．]\s*.+", 3),
        (r"^（[一二三四五六七八九十]+）\s*.+", 3),
        (r"^(?:摘要|引言|背景|目的|方法|结果|讨论|结论|参考文献|附录|目录|前言|概述|说明)\s*", 1),
    ]

    FONT_SIZE_THRESHOLDS = {
        1: 18.0,
        2: 14.0,
        3: 12.0,
    }

    def __init__(self, file_path: str, max_pages: Optional[int] = None):
        self.file_path = file_path
        self.max_pages = max_pages
        self._doc: Optional[pdfplumber.PDF] = None

    def _open_document(self) -> pdfplumber.PDF:
        if self._doc is not None:
            return self._doc

        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"PDF文件不存在: {self.file_path}")

        try:
            self._doc = pdfplumber.open(self.file_path)
        except Exception as e:
            raise RuntimeError(f"打开PDF文件失败: {e}")

        return self._doc

    def _close_document(self) -> None:
        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:
                pass
            self._doc = None

    def get_metadata(self) -> dict:
        doc = self._open_document()
        meta = doc.metadata or {}
        metadata = {
            "title": (meta.get("Title") or "").strip(),
            "author": (meta.get("Author") or "").strip(),
            "subject": (meta.get("Subject") or "").strip(),
            "keywords": (meta.get("Keywords") or "").strip(),
            "creator": (meta.get("Creator") or "").strip(),
            "producer": (meta.get("Producer") or "").strip(),
            "creation_date": str(meta.get("CreationDate") or ""),
            "modification_date": str(meta.get("ModDate") or ""),
            "total_pages": len(doc.pages),
            "format": "PDF",
            "encrypted": False,
        }
        logger.info(f"提取元数据完成: {self.file_path}, 共 {metadata['total_pages']} 页")
        return metadata

    def extract_text(self) -> List[TextParagraph]:
        """
        提取全部文本，返回结构化数据
        """
        doc = self._open_document()
        total_pages = len(doc.pages)
        if self.max_pages is not None:
            total_pages = min(total_pages, self.max_pages)

        paragraphs: List[TextParagraph] = []
        current_title = ""
        current_level = 0

        for page_num in range(1, total_pages + 1):
            try:
                page = doc.pages[page_num - 1]
                page_text = page.extract_text() or ""
                if not page_text.strip():
                    continue

                lines = page_text.split("\n")
                page_text_parts: List[str] = []
                page_title = current_title

                for raw_line in lines:
                    line_text = raw_line.strip()
                    if not line_text:
                        continue

                    heading_level = self._detect_heading_level(line_text, 0.0, False)

                    if heading_level > 0:
                        if page_text_parts:
                            combined = "\n".join(page_text_parts).strip()
                            if combined:
                                paragraphs.append(TextParagraph(
                                    page=page_num,
                                    title=page_title,
                                    content=combined,
                                    level=0,
                                ))
                            page_text_parts = []

                        current_title = line_text
                        current_level = heading_level
                        page_title = current_title

                        paragraphs.append(TextParagraph(
                            page=page_num,
                            title=line_text,
                            content=line_text,
                            level=heading_level,
                        ))
                    else:
                        page_text_parts.append(line_text)

                if page_text_parts:
                    combined = "\n".join(page_text_parts).strip()
                    if combined:
                        paragraphs.append(TextParagraph(
                            page=page_num,
                            title=page_title,
                            content=combined,
                            level=0,
                        ))

            except Exception as e:
                logger.error(f"提取第 {page_num} 页文本失败: {e}", exc_info=True)

        logger.info(f"文本提取完成: 共 {len(paragraphs)} 个段落")
        return paragraphs

    def _detect_heading_level(self, text: str, font_size: float, is_bold: bool) -> int:
        text_stripped = text.strip()
        if not text_stripped:
            return 0

        for pattern, level in self.HEADING_PATTERNS:
            if re.match(pattern, text_stripped):
                return level

        if font_size >= self.FONT_SIZE_THRESHOLDS[1]:
            return 1
        elif font_size >= self.FONT_SIZE_THRESHOLDS[2]:
            return 2
        elif font_size >= self.FONT_SIZE_THRESHOLDS[3] and is_bold:
            return 3

        if is_bold and len(text_stripped) <= 30 and not text_stripped.endswith(("。", "，", "；")):
            return 3

        return 0

    def extract_tables(self) -> List[TableData]:
        doc = self._open_document()
        total_pages = len(doc.pages)
        if self.max_pages is not None:
            total_pages = min(total_pages, self.max_pages)

        all_tables: List[TableData] = []

        for page_num in range(1, total_pages + 1):
            try:
                page = doc.pages[page_num - 1]
                tables = page.extract_tables() or []
                if not tables:
                    continue

                for table_idx, table in enumerate(tables):
                    cleaned_rows = []
                    for row in table:
                        cleaned_row = [cell.strip() if cell else "" for cell in row]
                        if any(cell for cell in cleaned_row):
                            cleaned_rows.append(cleaned_row)

                    if cleaned_rows:
                        caption = self._extract_table_caption(page, table_idx)
                        all_tables.append(TableData(
                            page_number=page_num,
                            rows=cleaned_rows,
                            caption=caption,
                        ))
            except Exception as e:
                logger.error(f"提取第 {page_num} 页表格失败: {e}", exc_info=True)
                continue

        logger.info(f"表格提取完成: 共提取 {len(all_tables)} 个表格")
        return all_tables

    def _extract_table_caption(self, page, table_index: int) -> Optional[str]:
        try:
            text = page.extract_text() or ""
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            for line in lines:
                if re.search(r"(?:表\s*\d+|Table\s*\d+)", line, re.IGNORECASE):
                    return line

            if lines:
                for line in reversed(lines):
                    if len(line) <= 50 and not line.endswith(("。", "；")):
                        return line
        except Exception as e:
            logger.debug(f"提取表格标题失败: {e}")

        return None

    def extract_images(self, output_dir: Optional[str] = None) -> List[ImageInfo]:
        """
        提取PDF中的图片

        策略：
        1. 先尝试提取嵌入图片（PDF 对象中的 image XObject）
        2. 如果某页没有任何图片（常见于扫描件），把整页渲染为图片

        Args:
            output_dir: 图片保存目录
        """
        if output_dir is None:
            output_dir = settings.IMAGE_DIR

        os.makedirs(output_dir, exist_ok=True)

        all_images: List[ImageInfo] = []
        filename_base = os.path.splitext(os.path.basename(self.file_path))[0]

        doc = self._open_document()
        total_pages = len(doc.pages)
        if self.max_pages is not None:
            total_pages = min(total_pages, self.max_pages)

        for page_num in range(1, total_pages + 1):
            try:
                page = doc.pages[page_num - 1]
                images = page.images or []

                if images:
                    for img_index, img in enumerate(images):
                        try:
                            stream = img.get("stream")
                            image_bytes = None
                            if stream is not None:
                                # pdfminer.six PDFStream 对象
                                if hasattr(stream, "get_data"):
                                    try:
                                        image_bytes = stream.get_data()
                                    except Exception:
                                        image_bytes = None
                                if image_bytes is None and hasattr(stream, "data"):
                                    try:
                                        image_bytes = stream.data
                                    except Exception:
                                        image_bytes = None

                            if not image_bytes or len(image_bytes) < 100:
                                continue

                            # 判断图片格式
                            image_format = "png"
                            stream_name = getattr(stream, "name", "") or ""
                            if stream_name and "." in stream_name:
                                ext = stream_name.rsplit(".", 1)[-1].lower()
                                if ext in ("jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp"):
                                    image_format = ext

                            image_filename = f"{filename_base}_p{page_num}_img{img_index}.{image_format}"
                            image_path = os.path.join(output_dir, image_filename)
                            with open(image_path, "wb") as f:
                                f.write(image_bytes)

                            bbox = (
                                float(img.get("x0", 0) or 0),
                                float(img.get("top", 0) or 0),
                                float(img.get("x1", 0) or 0),
                                float(img.get("bottom", 0) or 0),
                            )

                            all_images.append(ImageInfo(
                                page_number=page_num,
                                image_index=img_index,
                                width=int(img.get("width", 0) or 0),
                                height=int(img.get("height", 0) or 0),
                                bbox=bbox,
                                image_bytes=image_bytes,
                                image_format=image_format,
                            ))
                        except Exception as e:
                            logger.debug(f"提取第{page_num}页第{img_index}张图片失败: {e}")
                            continue
                else:
                    # 扫描件页面：把整页渲染为图片
                    try:
                        page_img = page.to_image(resolution=150)
                        pil_img = page_img.original
                        img_buf = io.BytesIO()
                        pil_img.save(img_buf, format="PNG")
                        image_bytes = img_buf.getvalue()
                        if image_bytes and len(image_bytes) >= 100:
                            image_filename = f"{filename_base}_p{page_num}_img0.png"
                            image_path = os.path.join(output_dir, image_filename)
                            with open(image_path, "wb") as f:
                                f.write(image_bytes)
                            page_w = float(page.width or 0)
                            page_h = float(page.height or 0)
                            all_images.append(ImageInfo(
                                page_number=page_num,
                                image_index=0,
                                width=pil_img.width,
                                height=pil_img.height,
                                bbox=(0.0, 0.0, page_w, page_h),
                                image_bytes=image_bytes,
                                image_format="png",
                            ))
                    except Exception as e:
                        logger.debug(f"渲染第{page_num}页为图片失败: {e}")

            except Exception as e:
                logger.error(f"处理第{page_num}页图片时失败: {e}", exc_info=True)
                continue

        logger.info(f"图片提取完成: 共提取 {len(all_images)} 张图片，保存至 {output_dir}")
        return all_images

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
        self, output_dir: str, filename_base: str, generate_descriptions: bool = False
    ) -> List[Dict]:
        """
        提取并生成图片描述（v13 纯 PIL 版，无 pypdfium2 依赖）

        v13 核心修复（2026-06-04）：
        - 移除 page.to_image() 调用（需 pypdfium2，LoongArch 无此模块）
        - 改为从 page.images 提取每张嵌入图，用 PIL 转成标准 PNG
        - DCTDecode(JPEG): 字节是合法 JPEG → PIL.open() → 保存 PNG
        - FlateDecode: 字节是原始 RGB 像素 → Image.frombuffer() → 保存 PNG
        - 无嵌入图的页面跳过，不生成伪图片
        - max_images_per_page = 3（控制单页图片数量）
        """
        doc = self._open_document()
        try:
            total_pages = len(doc.pages)
            if self.max_pages is not None:
                total_pages = min(total_pages, self.max_pages)

            os.makedirs(output_dir, exist_ok=True)

            image_descriptions: List[Dict] = []
            success_count = 0
            fail_count = 0
            max_images_per_page = 3

            from PIL import Image as _PIL

            for page_num in range(1, total_pages + 1):
                try:
                    page = doc.pages[page_num - 1]
                    raw_images = page.images or []

                    if not raw_images:
                        continue

                    for img_idx, img_data in enumerate(raw_images[:max_images_per_page]):
                        try:
                            stream = img_data.get("stream")
                            if stream is None:
                                continue

                            image_bytes = None
                            if hasattr(stream, "get_data"):
                                try:
                                    image_bytes = stream.get_data()
                                except Exception:
                                    image_bytes = None
                            if image_bytes is None and hasattr(stream, "data"):
                                try:
                                    image_bytes = stream.data
                                except Exception:
                                    image_bytes = None
                            if not image_bytes or len(image_bytes) < 100:
                                continue

                            # 获取真实像素尺寸
                            # 注意：img_data["width"/"height"] 是 PDF 点坐标（72DPI），不是像素
                            # 真实像素尺寸在 stream 的属性里（Width/Height 或 srcsize）
                            stream = img_data.get("stream")
                            w = 0
                            h = 0
                            # 方法1: stream 的 Width/Height 属性（真实像素尺寸）
                            if stream:
                                try:
                                    w = int(stream.attrs.get("Width", 0))
                                    h = int(stream.attrs.get("Height", 0))
                                except Exception:
                                    pass
                            # 方法2: srcsize
                            if w == 0 or h == 0:
                                try:
                                    srcsize = img_data.get("srcsize", (0, 0))
                                    w = int(srcsize[0])
                                    h = int(srcsize[1])
                                except Exception:
                                    pass
                            # 方法3: 兜底用 PDF 点坐标（可能不正确但总比 0 好）
                            if w == 0 or h == 0:
                                w = int(img_data.get("width", 0) or 0)
                                h = int(img_data.get("height", 0) or 0)

                            # 用 PIL 将任意格式字节转成标准 PNG
                            valid_png = None
                            try:
                                pil_img = _PIL.open(io.BytesIO(image_bytes))
                                pil_img.load()
                                buf = io.BytesIO()
                                pil_img.save(buf, format="PNG")
                                valid_png = buf.getvalue()
                            except Exception:
                                pass

                            # PIL.open 失败 → 尝试 zlib 解压后再 frombuffer
                            # PDF FlateDecode 图片: stream.get_data() 返回 deflate 压缩字节
                            if valid_png is None and w > 0 and h > 0:
                                try:
                                    # 先尝试 zlib 解压
                                    raw_bytes = None
                                    try:
                                        import zlib
                                        raw_bytes = zlib.decompress(image_bytes)
                                    except Exception:
                                        pass

                                    # 如果 zlib 解压失败，尝试跳过 zlib header (raw deflate)
                                    if raw_bytes is None:
                                        try:
                                            import zlib
                                            raw_bytes = zlib.decompress(image_bytes, -15)
                                        except Exception:
                                            pass

                                    use_bytes = raw_bytes if raw_bytes else image_bytes

                                    cs_raw = img_data.get("colorspace") or ""
                                    # colorspace 可能是 list（如 [/DeviceRGB]）或 str
                                    if isinstance(cs_raw, list):
                                        cs = " ".join(str(x) for x in cs_raw).lower()
                                    else:
                                        cs = str(cs_raw).lower()
                                    if "rgb" in cs:
                                        mode = "RGB"
                                    elif "gray" in cs or cs == "g" or cs == "/devicegray":
                                        mode = "L"
                                    elif "cmyk" in cs:
                                        mode = "CMYK"
                                    else:
                                        if len(use_bytes) == w * h:
                                            mode = "L"
                                        elif len(use_bytes) == w * h * 3:
                                            mode = "RGB"
                                        elif len(use_bytes) == w * h * 4:
                                            mode = "RGBA"
                                        else:
                                            raise ValueError(f"bytes={len(use_bytes)} 与 {w}x{h} 不匹配")

                                    pil_img = _PIL.frombuffer(mode, (w, h), use_bytes)
                                    if mode == "CMYK":
                                        pil_img = pil_img.convert("RGB")
                                    buf = io.BytesIO()
                                    pil_img.save(buf, format="PNG")
                                    valid_png = buf.getvalue()
                                except Exception as e:
                                    logger.warning(f"第{page_num}页图{img_idx} frombuffer 失败: {e}")

                            if valid_png is None or len(valid_png) < 100:
                                logger.warning(f"第{page_num}页图{img_idx} 转 PNG 失败（bytes={len(image_bytes)}, w={w}, h={h}）")
                                fail_count += 1
                                continue

                            image_filename = f"{filename_base}_p{page_num}_img{img_idx}.png"
                            image_path = os.path.join(output_dir, image_filename)

                            with open(image_path, "wb") as f:
                                f.write(valid_png)

                            description = None
                            if generate_descriptions:
                                try:
                                    description = self._describe_image(valid_png, "png")
                                except Exception as desc_err:
                                    logger.warning(f"第{page_num}页图{img_idx} AI 描述失败: {desc_err}")

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
                                    "is_full_page_render": False,
                                },
                            }
                            image_descriptions.append(result_item)
                            success_count += 1

                        except Exception as e:
                            logger.warning(f"第{page_num}页图{img_idx} 处理失败: {type(e).__name__}: {e}")
                            fail_count += 1
                            continue

                except Exception as e:
                    logger.error(f"处理第{page_num}页时失败: {type(e).__name__}: {e}", exc_info=True)
                    fail_count += 1
                    continue

            logger.info(f"图片提取完成: 共 {len(image_descriptions)} 张图片（成功 {success_count}, 失败 {fail_count}，描述{'已生成' if generate_descriptions else '待后台生成'}）")
            return image_descriptions
        finally:
            try:
                if doc is not None:
                    doc.close()
            except Exception:
                pass

    def parse_pdf(self) -> dict:
        doc = self._open_document()
        total_pages = len(doc.pages)
        if self.max_pages is not None:
            total_pages = min(total_pages, self.max_pages)

        logger.info(f"开始解析PDF: {self.file_path}, 共 {total_pages} 页")

        metadata = self.get_metadata()
        paragraphs = self.extract_text()
        tables = self.extract_tables()
        # 修复：删除冗余的 self.extract_images() 调用
        # 原 bug：_extract_and_describe_images 也会保存图片到磁盘，
        #        pdfplumber stream 二次读取会返回损坏数据，
        #        导致 5MB+ 的损坏文件覆盖了正确的 1.25MB PNG。
        # 现在只调用一次 _extract_and_describe_images（唯一进入 paragraphs metadata 的入口）。
        images: List[ImageInfo] = []  # 保留字段为空，避免破坏返回结构

        filename_base = os.path.splitext(os.path.basename(self.file_path))[0]
        image_descriptions = self._extract_and_describe_images(
            output_dir=settings.IMAGE_DIR,
            filename_base=filename_base,
        )

        all_paragraphs = []
        text_para_idx = 0
        img_desc_idx = 0

        text_paragraphs = [
            {
                "page": p.page,
                "title": p.title,
                "content": p.content,
                "level": p.level,
            }
            for p in paragraphs
        ]

        while text_para_idx < len(text_paragraphs) or img_desc_idx < len(image_descriptions):
            if text_para_idx < len(text_paragraphs):
                text_page = text_paragraphs[text_para_idx]["page"]
            else:
                text_page = float("inf")

            if img_desc_idx < len(image_descriptions):
                img_page = image_descriptions[img_desc_idx]["page"]
            else:
                img_page = float("inf")

            if text_page <= img_page:
                all_paragraphs.append(text_paragraphs[text_para_idx])
                text_para_idx += 1
                while img_desc_idx < len(image_descriptions) and image_descriptions[img_desc_idx]["page"] <= text_page:
                    all_paragraphs.append(image_descriptions[img_desc_idx])
                    img_desc_idx += 1
            else:
                all_paragraphs.append(image_descriptions[img_desc_idx])
                img_desc_idx += 1

        while img_desc_idx < len(image_descriptions):
            all_paragraphs.append(image_descriptions[img_desc_idx])
            img_desc_idx += 1

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
        doc = self._open_document()
        if page_number < 1 or page_number > len(doc.pages):
            raise ValueError(f"页码超出范围: {page_number}, 文档共 {len(doc.pages)} 页")

        page = doc.pages[page_number - 1]
        text = (page.extract_text() or "").strip()

        tables = self._extract_tables_for_page(page_number)
        images = self._extract_images_for_page(page_number)

        return PDFPage(
            page_number=page_number,
            text=text,
            tables=tables,
            images=images,
        )

    def _extract_tables_for_page(self, page_number: int) -> List[TableData]:
        try:
            doc = self._open_document()
            page = doc.pages[page_number - 1]
            tables = page.extract_tables() or []

            result = []
            for table_idx, table in enumerate(tables):
                cleaned_rows = []
                for row in table:
                    cleaned_row = [cell.strip() if cell else "" for cell in row]
                    if any(cell for cell in cleaned_row):
                        cleaned_rows.append(cleaned_row)

                if cleaned_rows:
                    caption = self._extract_table_caption(page, table_idx)
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
        doc = self._open_document()
        page = doc.pages[page_number - 1]
        images: List[ImageInfo] = []
        raw_images = page.images or []

        if not raw_images:
            return images

        from PIL import Image as _PIL

        for img_index, img in enumerate(raw_images):
            try:
                stream = img.get("stream")
                if stream is None:
                    continue
                image_bytes = None
                if hasattr(stream, "get_data"):
                    try:
                        image_bytes = stream.get_data()
                    except Exception:
                        image_bytes = None
                if image_bytes is None and hasattr(stream, "data"):
                    try:
                        image_bytes = stream.data
                    except Exception:
                        image_bytes = None
                if not image_bytes or len(image_bytes) < 100:
                    continue

                # 获取真实像素尺寸（同 _extract_and_describe_images 的逻辑）
                stream_obj = img.get("stream")
                w = 0
                h = 0
                if stream_obj:
                    try:
                        w = int(stream_obj.attrs.get("Width", 0))
                        h = int(stream_obj.attrs.get("Height", 0))
                    except Exception:
                        pass
                if w == 0 or h == 0:
                    try:
                        srcsize = img.get("srcsize", (0, 0))
                        w = int(srcsize[0])
                        h = int(srcsize[1])
                    except Exception:
                        pass
                if w == 0 or h == 0:
                    w = int(img.get("width", 0) or 0)
                    h = int(img.get("height", 0) or 0)

                # 用 PIL 转成标准 PNG
                valid_png = None
                try:
                    pil_img = _PIL.open(io.BytesIO(image_bytes))
                    pil_img.load()
                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    valid_png = buf.getvalue()
                except Exception:
                    pass

                # PIL.open 失败 → 尝试 zlib 解压后再 frombuffer
                if valid_png is None and w > 0 and h > 0:
                    try:
                        raw_bytes = None
                        try:
                            import zlib
                            raw_bytes = zlib.decompress(image_bytes)
                        except Exception:
                            pass
                        if raw_bytes is None:
                            try:
                                import zlib
                                raw_bytes = zlib.decompress(image_bytes, -15)
                            except Exception:
                                pass

                        use_bytes = raw_bytes if raw_bytes else image_bytes

                        cs_raw = img.get("colorspace") or ""
                        if isinstance(cs_raw, list):
                            cs = " ".join(str(x) for x in cs_raw).lower()
                        else:
                            cs = str(cs_raw).lower()
                        if "rgb" in cs:
                            mode = "RGB"
                        elif "gray" in cs or cs == "g" or cs == "/devicegray":
                            mode = "L"
                        elif "cmyk" in cs:
                            mode = "CMYK"
                        else:
                            if len(use_bytes) == w * h:
                                mode = "L"
                            elif len(use_bytes) == w * h * 3:
                                mode = "RGB"
                            elif len(use_bytes) == w * h * 4:
                                mode = "RGBA"
                            else:
                                raise ValueError(f"bytes={len(use_bytes)} 不匹配 {w}x{h}")

                        pil_img = _PIL.frombuffer(mode, (w, h), use_bytes)
                        if mode == "CMYK":
                            pil_img = pil_img.convert("RGB")
                        buf = io.BytesIO()
                        pil_img.save(buf, format="PNG")
                        valid_png = buf.getvalue()
                    except Exception:
                        pass

                if valid_png is None or len(valid_png) < 100:
                    logger.debug(f"第{page_number}页图{img_index} 转 PNG 失败（bytes={len(image_bytes)}, w={w}, h={h}）")
                    continue

                bbox = (
                    float(img.get("x0", 0) or 0),
                    float(img.get("top", 0) or 0),
                    float(img.get("x1", 0) or 0),
                    float(img.get("bottom", 0) or 0),
                )
                images.append(ImageInfo(
                    page_number=page_number,
                    image_index=img_index,
                    width=w, height=h,
                    bbox=bbox,
                    image_bytes=valid_png,
                    image_format="png",
                ))
            except Exception as e:
                logger.debug(f"提取第 {page_number} 页第 {img_index} 张图片失败: {e}")
                continue

        return images

    def parse(self) -> PDFDocument:
        doc = self._open_document()
        total_pages = len(doc.pages)

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
        doc = self.parse()
        full_text = "\n".join(page.text for page in doc.pages if page.text.strip())
        return full_text

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close_document()
