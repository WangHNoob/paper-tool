"""系统托盘 (pystray)"""

import logging
import threading
from typing import Callable

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


def _create_icon_image() -> Image.Image:
    """创建默认托盘图标"""
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # 简单的文档图标
    draw.rectangle([12, 4, 52, 60], fill=(52, 152, 219), outline=(41, 128, 185))
    draw.rectangle([20, 14, 44, 18], fill=(255, 255, 255))
    draw.rectangle([20, 22, 44, 26], fill=(255, 255, 255))
    draw.rectangle([20, 30, 40, 34], fill=(255, 255, 255))
    return image


class TrayApp:
    """系统托盘应用"""

    def __init__(
        self,
        on_pause: Callable[[], None],
        on_resume: Callable[[], None],
        on_show_gui: Callable[[], None],
        on_quit: Callable[[], None],
    ):
        self._on_pause = on_pause
        self._on_resume = on_resume
        self._on_show_gui = on_show_gui
        self._on_quit = on_quit
        self._paused = False
        self._thread: threading.Thread | None = None
        self._icon = None

    def start(self) -> None:
        """在独立线程中启动托盘"""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止托盘"""
        if self._icon is not None:
            self._icon.stop()

    def _run(self) -> None:
        """托盘主循环"""
        import pystray

        image = _create_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", self._show_gui),
            pystray.MenuItem("暂停监控", self._toggle_pause),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._quit),
        )
        self._icon = pystray.Icon("paper_tool", image, "Paper Tool", menu)
        self._icon.run()

    def _show_gui(self, icon, item) -> None:
        self._on_show_gui()

    def _toggle_pause(self, icon, item) -> None:
        if self._paused:
            self._on_resume()
            self._paused = False
        else:
            self._on_pause()
            self._paused = True

    def _quit(self, icon, item) -> None:
        self._on_quit()
        icon.stop()
