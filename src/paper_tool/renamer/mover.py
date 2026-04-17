"""文件移动/重命名执行器"""

import logging
import shutil
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class FileMover:
    """文件移动执行器，支持冲突处理策略"""

    def __init__(self, conflict_strategy: str = "append_number"):
        self._conflict_strategy = conflict_strategy

    def move(self, src: Path, dst: Path) -> Path:
        """移动文件到目标路径。

        Args:
            src: 源文件路径
            dst: 目标文件路径

        Returns:
            实际的目标路径（可能因冲突处理而不同）

        Raises:
            FileNotFoundError: 源文件不存在
            OSError: 文件操作失败
        """
        if not src.exists():
            raise FileNotFoundError(f"源文件不存在: {src}")

        actual_dst = self._resolve_conflict(dst)
        actual_dst.parent.mkdir(parents=True, exist_ok=True)

        # Windows 重试：处理文件锁
        for attempt in range(5):
            try:
                shutil.move(str(src), str(actual_dst))
                logger.info("文件移动成功: %s -> %s", src.name, actual_dst)
                return actual_dst
            except PermissionError:
                if attempt < 4:
                    logger.debug("文件被锁定，等待重试: %s", src.name)
                    time.sleep(0.5)
                else:
                    raise

        return actual_dst  # unreachable, but for type checker

    def _resolve_conflict(self, dst: Path) -> Path:
        """根据冲突策略处理文件名冲突。

        Args:
            dst: 目标路径

        Returns:
            解决冲突后的实际路径
        """
        if not dst.exists():
            return dst

        if self._conflict_strategy == "skip":
            logger.info("文件已存在，跳过: %s", dst)
            return dst

        # append_number 策略
        stem = dst.stem
        suffix = dst.suffix
        parent = dst.parent
        counter = 1

        while True:
            new_dst = parent / f"{stem}_{counter}{suffix}"
            if not new_dst.exists():
                logger.debug("冲突解决: %s -> %s", dst.name, new_dst.name)
                return new_dst
            counter += 1
