"""QThread 封装的 asyncio 事件循环"""

import asyncio
import logging
import threading

from PyQt6.QtCore import QThread

logger = logging.getLogger(__name__)


class AsyncioThread(QThread):
    """在 QThread 中运行 asyncio 事件循环，供 Qt 主线程调度协程"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            raise RuntimeError("AsyncioThread 尚未启动")
        return self._loop

    def run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        logger.info("AsyncioThread 事件循环已启动")
        self._loop.run_forever()
        pending = asyncio.all_tasks(self._loop)
        for task in pending:
            task.cancel()
        if pending:
            self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        self._loop.close()
        logger.info("AsyncioThread 事件循环已关闭")

    def start_and_wait(self, timeout: float = 5.0) -> None:
        """启动线程并阻塞直到事件循环就绪"""
        self.start()
        if not self._ready.wait(timeout):
            raise RuntimeError("AsyncioThread 启动超时")

    def stop(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)

    def run_coroutine(self, coro):
        """从任意线程安全地提交协程到 asyncio 事件循环"""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)
