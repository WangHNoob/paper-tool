"""异步重试装饰器"""

import asyncio
import functools
import logging
from typing import Any, Callable, Sequence

logger = logging.getLogger(__name__)


def async_retry(
    max_attempts: int = 3,
    delays: Sequence[float] = (5.0, 15.0, 45.0),
    retryable_exceptions: Sequence[type[Exception]] = (Exception,),
) -> Callable:
    """异步重试装饰器。

    Args:
        max_attempts: 最大尝试次数
        delays: 每次重试前的等待秒数
        retryable_exceptions: 可重试的异常类型
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except tuple(retryable_exceptions) as e:
                    last_exception = e
                    if attempt < max_attempts:
                        delay = delays[min(attempt - 1, len(delays) - 1)]
                        logger.warning(
                            "%s 第 %d 次尝试失败 (%s)，%0.1f 秒后重试",
                            func.__name__,
                            attempt,
                            e,
                            delay,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "%s 经过 %d 次尝试后仍然失败: %s",
                            func.__name__,
                            max_attempts,
                            e,
                        )
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator
