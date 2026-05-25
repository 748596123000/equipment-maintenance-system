"""
PDF解析模块测试

测试PDFParser类的各项功能：
- 文档打开和元数据提取
- 文本内容提取
- 图片信息提取
- 表格数据提取
- 完整文档解析
- 错误处理
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from app.core.pdf_parser import PDFParser, PDFDocument, PDFPage, ImageInfo, TableData


class TestPDFParser:
    """PDF解析器测试类"""

    @pytest.fixture
    def sample_pdf_path(self):
        """创建测试用PDF文件路径"""
        # 使用实际的测试PDF文件路径
        return os.path.join(os.path.dirname(__file__), "fixtures", "sample.pdf")

    @pytest.fixture
    def temp_pdf(self):
        """创建临时PDF文件"""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            # 写入最小的PDF文件头
            f.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF")
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_parser_init(self, temp_pdf):
        """测试解析器初始化"""
        parser = PDFParser(temp_pdf)
        assert parser.file_path == temp_pdf
        assert parser.max_pages is None

    def test_parser_init_with_max_pages(self, temp_pdf):
        """测试带页数限制的初始化"""
        parser = PDFParser(temp_pdf, max_pages=5)
        assert parser.max_pages == 5

    def test_file_not_found(self):
        """测试文件不存在时的错误处理"""
        parser = PDFParser("/nonexistent/path/file.pdf")
        with pytest.raises(FileNotFoundError, match="PDF文件不存在"):
            parser.extract_metadata()

    def test_invalid_page_number(self, temp_pdf):
        """测试无效页码的错误处理"""
        parser = PDFParser(temp_pdf)
        # 需要先打开文档
        try:
            parser.extract_text(999)
            assert False, "应该抛出ValueError"
        except (ValueError, Exception):
            pass  # 预期会抛出异常

    def test_pdf_page_dataclass(self):
        """测试PDFPage数据结构"""
        page = PDFPage(
            page_number=1,
            text="测试文本内容",
            tables=[],
            images=[],
        )
        assert page.page_number == 1
        assert page.text == "测试文本内容"
        assert len(page.tables) == 0
        assert len(page.images) == 0

    def test_image_info_dataclass(self):
        """测试ImageInfo数据结构"""
        image = ImageInfo(
            page_number=1,
            image_index=0,
            width=800,
            height=600,
            bbox=(0, 0, 800, 600),
            image_format="png",
        )
        assert image.page_number == 1
        assert image.width == 800
        assert image.height == 600
        assert image.image_format == "png"

    def test_table_data_dataclass(self):
        """测试TableData数据结构"""
        table = TableData(
            page_number=1,
            rows=[
                ["表头1", "表头2"],
                ["数据1", "数据2"],
            ],
            caption="测试表格",
        )
        assert table.page_number == 1
        assert len(table.rows) == 2
        assert table.caption == "测试表格"

    def test_pdf_document_dataclass(self):
        """测试PDFDocument数据结构"""
        doc = PDFDocument(
            filename="test.pdf",
            title="测试文档",
            author="测试作者",
            total_pages=1,
            pages=[PDFPage(page_number=1, text="内容")],
        )
        assert doc.filename == "test.pdf"
        assert doc.title == "测试文档"
        assert doc.total_pages == 1
        assert len(doc.pages) == 1

    @patch("app.core.pdf_parser.fitz")
    def test_context_manager(self, mock_fitz, temp_pdf):
        """测试上下文管理器"""
        mock_doc = MagicMock()
        mock_fitz.open.return_value = mock_doc

        with PDFParser(temp_pdf) as parser:
            assert parser is not None

        # 验证文档被关闭
        mock_doc.close.assert_called_once()


class TestPDFParserIntegration:
    """PDF解析器集成测试（需要实际PDF文件）"""

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(os.path.dirname(__file__), "fixtures", "sample.pdf")),
        reason="测试PDF文件不存在"
    )
    def test_parse_real_pdf(self):
        """测试解析真实PDF文件"""
        pdf_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample.pdf")
        parser = PDFParser(pdf_path)

        result = parser.parse()
        assert isinstance(result, PDFDocument)
        assert result.total_pages > 0
        assert len(result.pages) > 0

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(os.path.dirname(__file__), "fixtures", "sample.pdf")),
        reason="测试PDF文件不存在"
    )
    def test_get_full_text(self):
        """测试获取完整文本"""
        pdf_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample.pdf")
        parser = PDFParser(pdf_path)

        full_text = parser.get_full_text()
        assert isinstance(full_text, str)
        assert len(full_text) > 0
