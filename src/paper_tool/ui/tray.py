"""系统托盘 (QSystemTrayIcon)"""

import logging
from typing import Callable

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QBrush, QColor, QPen, QPixmap, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

logger = logging.getLogger(__name__)


def _create_icon() -> QIcon:
    """程序化生成托盘图标"""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    from PyQt6.QtGui import QPainter
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 文档图标
    painter.setBrush(QBrush(QColor(52, 152, 219)))
    painter.setPen(QPen(QColor(41, 128, 185), 1))
    painter.drawRoundedRect(12, 4, 40, 56, 4, 4)

    # 文本行
    painter.setBrush(QBrush(QColor(255, 255, 255)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRect(20, 14, 24, 4)
    painter.drawRect(20, 22, 24, 4)
    painter.drawRect(20, 30, 20, 4)
    painter.end()
    return QIcon(pixmap)


class TrayApp(QObject):
    """系统托盘应用"""

    def __init__(
        self,
        on_pause: Callable[[], None],
        on_resume: Callable[[], None],
        on_show_gui: Callable[[], None],
        on_quit: Callable[[], None],
        parent=None,
    ):
        super().__init__(parent)
        self._on_pause = on_pause
        self._on_resume = on_resume
        self._on_show_gui = on_show_gui
        self._on_quit = on_quit
        self._paused = False

        self._icon = QSystemTrayIcon(_create_icon(), self)

        menu = QMenu()
        menu.addAction("显示窗口", self._show_gui)
        self._pause_action = menu.addAction("暂停监控", self._toggle_pause)
        menu.addSeparator()
        menu.addAction("退出", self._quit)
        self._icon.setContextMenu(menu)

        self._icon.activated.connect(self._on_activated)
        self._icon.setToolTip("Paper Tool")

    def show(self) -> None:
        self._icon.show()

    def stop(self) -> None:
        self._icon.hide()

    def _show_gui(self) -> None:
        self._on_show_gui()

    def _toggle_pause(self) -> None:
        if self._paused:
            self._on_resume()
            self._paused = False
            self._pause_action.setText("暂停监控")
        else:
            self._on_pause()
            self._paused = True
            self._pause_action.setText("恢复监控")

    def _quit(self) -> None:
        self._on_quit()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_gui()
