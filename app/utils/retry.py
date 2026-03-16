from __future__ import annotations

import random
import time
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")


def retry(
    *,
    exceptions: Iterable[type[BaseException]],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            attempt = 0
            delay = base_delay
            while True:
                try:
                    return func(*args, **kwargs)
                except tuple(exceptions):
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    jitter = random.uniform(0, 0.3)
                    time.sleep(min(delay + jitter, max_delay))
                    delay *= 2

        return wrapper

    return decorator