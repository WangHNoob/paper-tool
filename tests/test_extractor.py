"""PDF 抽取器测试"""

import tempfile
from pathlib import Path

import fitz
import pytest

from paper_tool.extractor.text import PyMuPDFExtractor


@pytest.fixture
def sample_pdf(tmp_path):
    """创建一个简单的测试 PDF"""
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    text_point = fitz.Point(72, 72)
    page.insert_text(text_point, "Test Paper Title\nAuthor One, Author Two\nAbstract: This is a test paper about machine learning.")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def empty_pdf(tmp_path):
    """创建一个空白的 PDF"""
    pdf_path = tmp_path / "empty.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


class TestPyMuPDFExtractor:
    def setup_method(self):
        self.extractor = PyMuPDFExtractor()

    def test_extract_text_from_pdf(self, sample_pdf):
        text = self.extractor.extract(sample_pdf)
        assert "Test Paper Title" in text
        assert "Author One" in text

    def test_extract_empty_pdf(self, empty_pdf):
        text = self.extractor.extract(empty_pdf)
        assert isinstance(text, str)

    def test_extract_nonexistent_file(self):
        with pytest.raises(Exception):
            self.extractor.extract(Path("/nonexistent/file.pdf"))

    def test_extract_max_chars_truncation(self, sample_pdf):
        text = self.extractor.extract(sample_pdf, max_chars=20)
        assert len(text) <= 50  # 加上截断提示
        assert "截断" in text

    def test_extract_max_pages(self, tmp_path):
        """测试多页 PDF 的页数限制"""
        pdf_path = tmp_path / "multi_page.pdf"
        doc = fitz.open()
        for i in range(20):
            page = doc.new_page()
            page.insert_text(fitz.Point(72, 72), f"Page {i + 1} content " * 50)
        doc.save(str(pdf_path))
        doc.close()

        text = self.extractor.extract(pdf_path, max_pages=5)
        assert "Page 1" in text
        assert "Page 5" in text
