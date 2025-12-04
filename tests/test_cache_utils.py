"""Tests for cache management utilities."""

from unittest.mock import patch

import pytest

from core.cache import get_cached, set_cached
from core.cache_utils import clear_cache, get_cache_stats


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Fixture to provide an isolated cache directory for tests."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    monkeypatch.setattr("core.cache.CACHE_DIR", cache_dir)
    # Also patch the import in cache_utils
    monkeypatch.setattr("core.cache_utils.CACHE_DIR", cache_dir)
    return cache_dir


def test_get_cached_and_set_cached(isolated_cache):
    """Test basic cache set and get operations."""
    set_cached("test:key", {"data": "value"})
    result = get_cached("test:key")
    assert result == {"data": "value"}


def test_get_cached_miss(isolated_cache):
    """Test cache miss returns None."""
    result = get_cached("nonexistent:key")
    assert result is None


def test_get_cache_stats(isolated_cache):
    """Test cache statistics retrieval."""
    set_cached("key1", {"data": 1})
    set_cached("key2", {"data": 2})
    set_cached("key3", {"data": 3})

    stats = get_cache_stats()
    assert stats["items"] == 3
    assert stats["size_bytes"] > 0


def test_clear_cache_all(isolated_cache):
    """Test clearing all cache entries."""
    set_cached("key1", {"data": 1})
    set_cached("key2", {"data": 2})
    set_cached("key3", {"data": 3})

    cleared = clear_cache()
    assert cleared == 3

    stats = get_cache_stats()
    assert stats["items"] == 0
