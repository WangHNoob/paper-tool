"""watchdog 文件监控 + 防抖 + 文件就绪检查"""

import asyncio
import logging
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from watchdog.observers import Observer

from ..config.schema import MonitorConfig

logger = logging.getLogger(__name__)

# PDF 文件头魔数
PDF_MAGIC = b"%PDF-"


class PDFWatchHandler(FileSystemEventHandler):
    """PDF 文件事件处理器，带防抖和文件就绪检查"""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        queue: asyncio.Queue[Path],
        config: MonitorConfig,
    ):
        self._loop = loop
        self._queue = queue
        self._config = config
        self._last_events: dict[str, float] = {}  # path -> timestamp
        self._paused = False

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def on_created(self, event: FileCreatedEvent) -> None:
        if self._paused:
            return

        path = Path(event.src_path)

        # 检查扩展名（同步）
        if path.suffix.lower() not in self._config.file_extensions:
            return

        # 防抖（同步）
        now = time.monotonic()
        last_time = self._last_events.get(str(path), 0)
        if now - last_time < self._config.debounce_seconds:
            return

        # TTL 清理：移除 1 小时前的旧条目，防止内存泄漏
        if len(self._last_events) > 1000:
            cutoff = now - 3600
            self._last_events = {k: v for k, v in self._last_events.items() if v > cutoff}

        self._last_events[str(path)] = now

        # 文件就绪检查和 PDF 验证都在线程中执行，不阻塞 watchdog 线程
        asyncio.run_coroutine_threadsafe(self._check_and_submit(path), self._loop)

    async def _check_and_submit(self, path: Path) -> None:
        """异步检查文件就绪和 PDF 头，然后入队（不阻塞事件循环）"""
        # 文件就绪检查（线程中执行）
        ready = await asyncio.to_thread(self._is_file_ready, path)
        if not ready:
            logger.warning("文件未就绪，跳过: %s", path.name)
            return

        # PDF 头验证（线程中执行）
        is_pdf = await asyncio.to_thread(self._is_pdf, path)
        if not is_pdf:
            logger.warning("不是有效的 PDF 文件: %s", path.name)
            return

        logger.info("检测到新 PDF: %s", path.name)
        await self._queue.put(path)

    def _is_file_ready(self, path: Path) -> bool:
        """检查文件是否已经完全写入"""
        for _ in range(3):
            try:
                with open(path, "rb") as f:
                    pass
                if path.stat().st_size > 0:
                    return True
            except (OSError, PermissionError):
                time.sleep(1.0)
        return False

    def _is_pdf(self, path: Path) -> bool:
        """检查文件是否以 PDF 魔数开头"""
        try:
            with open(path, "rb") as f:
                header = f.read(5)
            return header == PDF_MAGIC
        except OSError:
            return False


class PDFWatcher:
    """PDF 文件监控器"""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        queue: asyncio.Queue[Path],
        config: MonitorConfig,
    ):
        self._loop = loop
        self._queue = queue
        self._config = config
        self._handler = PDFWatchHandler(loop, queue, config)
        self._observer: Observer | None = None

    def start(self) -> None:
        """启动文件监控"""
        watch_dir = Path(self._config.watch_dir)
        watch_dir.mkdir(parents=True, exist_ok=True)

        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            str(watch_dir),
            recursive=self._config.recursive,
        )
        self._observer.daemon = True
        self._observer.start()
        logger.info("开始监控目录: %s", watch_dir)

    def stop(self) -> None:
        """停止文件监控"""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.info("文件监控已停止")

    def pause(self) -> None:
        self._handler.pause()
        logger.info("文件监控已暂停")

    def resume(self) -> None:
        self._handler.resume()
        logger.info("文件监控已恢复")
