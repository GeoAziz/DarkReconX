"""Cache management utilities for CLI and modules.

Provides helpers for cache refresh, bypass, and TTL management.
"""

import asyncio
from typing import Any, Callable, Optional

from core.cache import CACHE_DIR, get_cached, set_cached


async def cache_aware_fetch(
    key: str,
    fetch_fn: Callable,
    refresh_cache: bool = False,
    no_cache: bool = False,
    max_age: Optional[int] = None,
) -> tuple[Any, bool]:
    """Fetch data with optional cache bypass or refresh.

    Args:
        key: Cache key identifier.
        fetch_fn: Async function to call if cache miss or refresh requested.
        refresh_cache: Force re-fetch even if cached data exists.
        no_cache: Skip cache entirely (don't read or write).
        max_age: Max age of cached data in seconds.

    Returns:
        Tuple of (data, was_cached) where was_cached indicates if data came from cache.

    Example:
        async def get_data():
            return await provider.lookup("example.com")

        data, from_cache = await cache_aware_fetch(
            "dns:example.com",
            get_data,
            refresh_cache=args.refresh_cache,
            no_cache=args.no_cache,
            max_age=86400
        )
    """
    # If no_cache is set, always fetch fresh
    if no_cache:
        result = await fetch_fn() if asyncio.iscoroutinefunction(fetch_fn) else fetch_fn()
        return result, False

    # If refresh_cache is set, bypass cache and fetch fresh
    if refresh_cache:
        result = await fetch_fn() if asyncio.iscoroutinefunction(fetch_fn) else fetch_fn()
        if not no_cache:
            set_cached(key, result)
        return result, False

    # Normal path: try cache first
    cached = get_cached(key, max_age=max_age)
    if cached is not None:
        return cached, True

    # Cache miss: fetch and store
    result = await fetch_fn() if asyncio.iscoroutinefunction(fetch_fn) else fetch_fn()
    set_cached(key, result)
    return result, False


def get_cache_stats() -> dict:
    """Get cache statistics (count of cached items)."""
    cache_dir = CACHE_DIR
    if not cache_dir.exists():
        return {"items": 0, "size_bytes": 0}

    count = 0
    total_size = 0
    for fname in cache_dir.iterdir():
        if fname.suffix == ".json":
            count += 1
            total_size += fname.stat().st_size

    return {"items": count, "size_bytes": total_size}


def clear_cache(pattern: Optional[str] = None) -> int:
    """Clear cache entries optionally matching a pattern.

    Args:
        pattern: Optional substring to match cache keys. If None, clears all.

    Returns:
        Number of entries cleared.
    """
    cache_dir = CACHE_DIR
    if not cache_dir.exists():
        return 0

    cleared = 0
    for fpath in cache_dir.iterdir():
        if fpath.suffix != ".json":
            continue
        if pattern:
            if pattern.lower() in fpath.name.lower():
                fpath.unlink()
                cleared += 1
        else:
            fpath.unlink()
            cleared += 1

    return cleared
