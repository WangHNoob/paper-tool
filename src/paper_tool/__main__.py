"""python -m paper_tool 入口"""

import asyncio
import sys

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

    # 检查命令行参数
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg in ("-c", "--config") and i + 1 < len(args):
            config_path = args[i + 1]
            break

    setup_logging("INFO")

    app = PaperToolApp(config_path)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(app.start())
    except KeyboardInterrupt:
        app._shutdown()
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
    finally:
        loop.close()


if __name__ == "__main__":
    main()
