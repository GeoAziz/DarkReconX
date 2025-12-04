"""Simple retry/backoff helpers for sync and async calls.

Provides `retry` decorator for sync functions and `async_retry` for async functions.
"""

import asyncio
import functools
import time
from typing import Callable


def retry(attempts: int = 3, initial_backoff: float = 1.0, backoff_factor: float = 2.0, exceptions=(Exception,)):
    def _decorator(fn: Callable):
        @functools.wraps(fn)
        def _wrapped(*args, **kwargs):
            delay = initial_backoff
            last_exc = None
            for attempt in range(1, attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == attempts:
                        raise
                    time.sleep(delay)
                    delay *= backoff_factor
            # If we somehow exit loop
            if last_exc:
                raise last_exc
            raise RuntimeError("Retry loop exited without exception")

        return _wrapped

    return _decorator


def async_retry(attempts: int = 3, initial_backoff: float = 1.0, backoff_factor: float = 2.0, exceptions=(Exception,)):
    def _decorator(fn: Callable):
        @functools.wraps(fn)
        async def _wrapped(*args, **kwargs):
            delay = initial_backoff
            last_exc = None
            for attempt in range(1, attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == attempts:
                        raise
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
            if last_exc:
                raise last_exc
            raise RuntimeError("Retry loop exited without exception")

        return _wrapped

    return _decorator
