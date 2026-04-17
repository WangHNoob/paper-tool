"""日志配置模块"""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """配置全局日志"""
    root_logger = logging.getLogger("paper_tool")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] %(levelname)-7s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root_logger.addHandler(handler)
