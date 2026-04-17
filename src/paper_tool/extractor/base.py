"""抽取器基类 (策略模式)"""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseExtractor(ABC):
    """PDF 文本抽取器基类"""

    @abstractmethod
    def extract(self, file_path: Path, max_pages: int = 10, max_chars: int = 8000) -> str:
        """从 PDF 文件中抽取文本。

        Args:
            file_path: PDF 文件路径
            max_pages: 最大抽取页数
            max_chars: 最大字符数

        Returns:
            抽取的文本内容
        """
        ...
