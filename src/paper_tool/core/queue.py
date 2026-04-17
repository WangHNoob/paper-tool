"""异步任务队列 (Semaphore 控制并发)"""

import asyncio
import logging
import uuid
from pathlib import Path

from .models import PaperInfo, ProcessingTask, TaskStatus

logger = logging.getLogger(__name__)


class ProcessingQueue:
    """异步处理队列，使用 Semaphore 控制并发"""

    def __init__(self, max_concurrency: int = 2):
        self._queue: asyncio.Queue[Path] = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._max_concurrency = max_concurrency
        self._tasks: dict[str, ProcessingTask] = {}

    @property
    def queue(self) -> asyncio.Queue[Path]:
        return self._queue

    async def put(self, path: Path) -> None:
        """将文件路径加入队列"""
        await self._queue.put(path)

    def create_task(self, path: Path) -> ProcessingTask:
        """创建处理任务"""
        task_id = uuid.uuid4().hex[:8]
        task = ProcessingTask(
            id=task_id,
            paper_info=PaperInfo(file_path=path),
            status=TaskStatus.PENDING,
        )
        self._tasks[task_id] = task
        return task

    async def acquire(self) -> None:
        """获取并发槽位"""
        await self._semaphore.acquire()

    def release(self) -> None:
        """释放并发槽位"""
        self._semaphore.release()

    def update_task(self, task_id: str, **kwargs) -> None:
        """更新任务状态"""
        task = self._tasks.get(task_id)
        if task is None:
            return
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)

    def get_task(self, task_id: str) -> ProcessingTask | None:
        return self._tasks.get(task_id)

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()
