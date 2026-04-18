"""应用主类，生命周期管理"""

import asyncio
import logging

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication

from .config.loader import ConfigLoader
from .config.schema import AppConfig
from .core.pipeline import Pipeline
from .db.database import Database
from .db.operations import delete_all_operations, delete_operations, list_operations
from .db.rollback import rollback_operation
from .monitor.watcher import PDFWatcher
from .ui.gui import GUIApp
from .ui.tray import TrayApp
from .utils.asyncio_thread import AsyncioThread
from .utils.logging import setup_logging

logger = logging.getLogger(__name__)

CONFIG_RELOAD_INTERVAL = 30  # 秒


class PaperToolApp(QObject):
    """Paper Tool 主应用"""

    def __init__(self, config_path: str):
        super().__init__()
        self._config_path = config_path
        self._config_loader = ConfigLoader(config_path)
        self._asyncio_thread: AsyncioThread | None = None
        self._db: Database | None = None
        self._pipeline: Pipeline | None = None
        self._watcher: PDFWatcher | None = None
        self._tray: TrayApp | None = None
        self._gui: GUIApp | None = None
        self._running = False

    def start(self) -> None:
        """启动应用（非阻塞，QApplication 在主线程运行）"""
        logger.info("Paper Tool 启动中...")

        # 加载配置
        config = self._config_loader.load()
        setup_logging(config.log_level)

        # 初始化数据库
        self._db = Database(config.database.path)
        self._db.connect()

        # 启动 asyncio 线程
        self._asyncio_thread = AsyncioThread()
        self._asyncio_thread.start()
        loop = self._asyncio_thread.loop

        # 初始化流水线
        self._pipeline = Pipeline(config, self._db)
        self._pipeline.init_classifier()
        loop.call_soon_threadsafe(self._pipeline.start)

        # 初始化文件监控
        self._watcher = PDFWatcher(
            loop=loop,
            queue=self._pipeline.queue.queue,
            config=config.monitor,
        )
        self._watcher.start()

        # 初始化 GUI（Qt 主线程）
        self._gui = GUIApp(
            config_loader=self._config_loader,
            on_config_saved=self._apply_config,
            on_rollback=self._do_rollback,
            on_refresh=self._list_operations,
            on_delete=self._do_delete,
        )
        self._gui.show()

        # 初始化系统托盘
        self._tray = TrayApp(
            on_pause=self._pause,
            on_resume=self._resume,
            on_show_gui=self._gui.show,
            on_quit=self._shutdown,
        )
        self._tray.show()

        self._running = True
        logger.info("Paper Tool 已启动，监控目录: %s", config.monitor.watch_dir)

        # 启动配置热重载协程
        self._asyncio_thread.run_coroutine(self._config_reload_loop())

    async def _config_reload_loop(self) -> None:
        """定时检查配置热重载"""
        while self._running:
            await asyncio.sleep(CONFIG_RELOAD_INTERVAL)
            new_config = self._config_loader.check_and_reload()
            if new_config is not None:
                logger.info("配置文件已变更，热重载...")
                self._apply_config(new_config)

    def _apply_config(self, new_config: AppConfig) -> None:
        """应用新配置（来自 GUI 保存或热重载）"""
        logger.info("应用新配置...")
        if self._pipeline is not None:
            self._pipeline._config = new_config
            self._pipeline.init_classifier()

        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = PDFWatcher(
                loop=self._asyncio_thread.loop,
                queue=self._pipeline.queue.queue,
                config=new_config.monitor,
            )
            self._watcher.start()
            logger.info("文件监控已重启，监控目录: %s", new_config.monitor.watch_dir)

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
        if self._asyncio_thread:
            self._asyncio_thread.stop()
        if self._db:
            self._db.close()

        QApplication.quit()

    def _do_rollback(self, op_id: int) -> bool:
        if self._db is None:
            return False
        return rollback_operation(self._db, op_id)

    def _list_operations(self) -> list[dict]:
        if self._db is None:
            return []
        return list_operations(self._db, limit=100)

    def _do_delete(self, ids: list[int]) -> int:
        if self._db is None:
            return 0
        if ids:
            return delete_operations(self._db, ids)
        return delete_all_operations(self._db)
