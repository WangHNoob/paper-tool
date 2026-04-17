"""核心数据模型"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class PaperInfo:
    """论文元数据"""

    file_path: Path
    text: str = ""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: str = ""
    journal: str = ""
    keywords: list[str] = field(default_factory=list)

    @property
    def file_name(self) -> str:
        return self.file_path.name


@dataclass
class ClassifyResult:
    """分类结果"""

    category: str
    confidence: float
    reasoning: str
    is_fallback: bool = False


@dataclass
class ProcessingTask:
    """处理任务"""

    id: str
    paper_info: PaperInfo
    classify_result: ClassifyResult | None = None
    new_path: Path | None = None
    status: TaskStatus = TaskStatus.PENDING
    error_message: str = ""
