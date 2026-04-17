"""PyMuPDF 文本抽取实现"""

import logging
from pathlib import Path

import fitz

from .base import BaseExtractor

logger = logging.getLogger(__name__)


class PyMuPDFExtractor(BaseExtractor):
    """基于 PyMuPDF 的 PDF 文本抽取器"""

    def extract(self, file_path: Path, max_pages: int = 10, max_chars: int = 8000) -> str:
        """从 PDF 文件中抽取文本。

        Args:
            file_path: PDF 文件路径
            max_pages: 最大抽取页数（前 N 页）
            max_chars: 最大字符数（截断）

        Returns:
            抽取的文本内容

        Raises:
            ValueError: 文件不是有效 PDF
            OSError: 文件读取失败
        """
        text_parts: list[str] = []
        try:
            doc = fitz.open(str(file_path))
        except fitz.FileDataError as e:
            raise ValueError(f"无效的 PDF 文件: {file_path}") from e

        try:
            page_count = min(len(doc), max_pages)
            for i in range(page_count):
                page = doc[i]
                page_text = page.get_text("text")
                if page_text:
                    text_parts.append(page_text.strip())

                total_chars = sum(len(t) for t in text_parts)
                if total_chars >= max_chars:
                    break
        finally:
            doc.close()

        full_text = "\n\n".join(text_parts)

        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "\n...[已截断]"

        logger.debug(
            "从 %s 抽取了 %d 字符 (共 %d 页)",
            file_path.name,
            len(full_text),
            page_count,
        )
        return full_text
