"""python -m paper_tool 入口"""

import sys

from PyQt6.QtWidgets import QApplication

from .main import PaperToolApp
from .utils.logging import setup_logging

_MUTEX_NAME = "PaperTool_SingleInstance"


def _ensure_single_instance() -> None:
    """通过 Windows 命名互斥体确保只有一个实例运行"""
    if sys.platform != "win32":
        return
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("Paper Tool 已在运行")
        sys.exit(0)


def main() -> None:
    """应用入口函数"""
    _ensure_single_instance()

    config_path = "config.yaml"
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg in ("-c", "--config") and i + 1 < len(args):
            config_path = args[i + 1]
            break

    setup_logging("INFO")

    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)

    app = PaperToolApp(config_path)
    app.start()

    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()
