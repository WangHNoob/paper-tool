"""应用主类，生命周期管理"""

import asyncio
import logging
import signal
import sys

from .config.loader import ConfigLoader
from .core.pipeline import Pipeline
from .db.database import Database
from .db.operations import list_operations
from .db.rollback import rollback_operation
from .monitor.watcher import PDFWatcher
from .ui.gui import GUIApp
from .ui.tray import TrayApp
from .utils.logging import setup_logging

logger = logging.getLogger(__name__)

CONFIG_RELOAD_INTERVAL = 30  # 秒


class PaperToolApp:
    """Paper Tool 主应用"""

    def __init__(self, config_path: str):
        self._config_path = config_path
        self._config_loader = ConfigLoader(config_path)
        self._db: Database | None = None
        self._pipeline: Pipeline | None = None
        self._watcher: PDFWatcher | None = None
        self._tray: TrayApp | None = None
        self._gui: GUIApp | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running = False

    async def start(self) -> None:
        """启动应用"""
        logger.info("Paper Tool 启动中...")

        # 加载配置
        config = self._config_loader.load()
        setup_logging(config.log_level)

        # 初始化数据库
        self._db = Database(config.database.path)
        self._db.connect()

        # 初始化流水线
        self._pipeline = Pipeline(config, self._db)
        self._pipeline.init_classifier()
        self._pipeline.start()

        # 初始化文件监控
        self._loop = asyncio.get_event_loop()
        self._watcher = PDFWatcher(
            loop=self._loop,
            queue=self._pipeline.queue.queue,
            config=config.monitor,
        )
        self._watcher.start()

        # 初始化 GUI
        self._gui = GUIApp(
            on_rollback=self._do_rollback,
            on_refresh=self._list_operations,
        )

        # 初始化系统托盘
        self._tray = TrayApp(
            on_pause=self._pause,
            on_resume=self._resume,
            on_show_gui=lambda: self._gui.start(),
            on_quit=self._shutdown,
        )
        self._tray.start()

        self._running = True
        logger.info("Paper Tool 已启动，监控目录: %s", config.monitor.watch_dir)

        # 启动配置热重载协程
        await self._config_reload_loop()

    async def _config_reload_loop(self) -> None:
        """定时检查配置热重载"""
        while self._running:
            await asyncio.sleep(CONFIG_RELOAD_INTERVAL)
            new_config = self._config_loader.check_and_reload()
            if new_config is not None:
                logger.info("配置已更新，重新初始化分类器...")
                if self._pipeline is not None:
                    self._pipeline._config = new_config
                    self._pipeline.init_classifier()

    def _pause(self) -> None:
        if self._watcher:
            self._watcher.pause()

    def _resume(self) -> None:
        if self._watcher:
            self._watcher.resume()

    def _shutdown(self) -> None:
        """关闭应用"""
        logger.info("Paper Tool 正在关闭...")
        self._running = False

        if self._watcher:
            self._watcher.stop()
        if self._pipeline:
            self._pipeline.stop()
        if self._tray:
            self._tray.stop()
        if self._gui:
            self._gui.stop()
        if self._db:
            self._db.close()

        if self._loop and self._loop.is_running():
            self._loop.stop()

    def _do_rollback(self, op_id: int) -> bool:
        if self._db is None:
            return False
        return rollback_operation(self._db, op_id)

    def _list_operations(self) -> list[dict]:
        if self._db is None:
            return []
        return list_operations(self._db, limit=100)
