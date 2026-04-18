"""日志配置模块"""

import logging
import sys
from datetime import timezone, timedelta

_TZ_SHANGHAI = timezone(timedelta(hours=8))


class _CSTFormatter(logging.Formatter):
    """使用东八区时间的格式化器"""

    def formatTime(self, record, datefmt=None):
        ct = record.created
        import datetime as dt
        t = dt.datetime.fromtimestamp(ct, tz=_TZ_SHANGHAI)
        if datefmt:
            return t.strftime(datefmt)
        return t.isoformat()


def setup_logging(level: str = "INFO") -> None:
    """配置全局日志"""
    root_logger = logging.getLogger("paper_tool")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            _CSTFormatter(
                "[%(asctime)s] %(levelname)-7s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root_logger.addHandler(handler)
