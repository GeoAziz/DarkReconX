"""Tests for async HTTP verification module."""

import asyncio

import httpx
import pytest

from modules.utils.async_verify import (
    MockAsyncClient,
    MockResponse,
    batch_http_verify,
    http_verify,
)

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_http_verify_success_mock(monkeypatch):
    """Test successful HTTP verification with mocked httpx."""

    class MockAsyncContext:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def head(self, url):
            return MockResponse(200, {"Server": "nginx", "Content-Length": "1234"})

    def mock_async_client(**kwargs):
        return MockAsyncContext()

    monkeypatch.setattr("httpx.AsyncClient", mock_async_client)

    result = await http_verify("http://example.com", timeout=5)
    assert result["status"] == 200
    assert result["live"] is True
    assert result["error"] is None
    assert "Server" in result["headers"]


@pytest.mark.asyncio
async def test_http_verify_redirect(monkeypatch):
    """Test HTTP verification with 3xx redirect (still considered live)."""

    class MockAsyncContext:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def head(self, url):
            return MockResponse(301, {"Location": "https://example.com"})

    def mock_async_client(**kwargs):
        return MockAsyncContext()

    monkeypatch.setattr("httpx.AsyncClient", mock_async_client)

    result = await http_verify("http://example.com", follow_redirects=False)
    assert result["status"] == 301
    assert result["live"] is True


@pytest.mark.asyncio
async def test_http_verify_not_found(monkeypatch):
    """Test HTTP verification with 404 response."""

    class MockAsyncContext:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def head(self, url):
            return MockResponse(404, {})

    def mock_async_client(**kwargs):
        return MockAsyncContext()

    monkeypatch.setattr("httpx.AsyncClient", mock_async_client)

    result = await http_verify("http://example.com/notfound")
    assert result["status"] == 404
    assert result["live"] is False


@pytest.mark.asyncio
async def test_http_verify_timeout(monkeypatch):
    """Test HTTP verification timeout handling."""

    class MockAsyncContext:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def head(self, url):
            raise asyncio.TimeoutError("Request timed out")

    def mock_async_client(**kwargs):
        return MockAsyncContext()

    monkeypatch.setattr("httpx.AsyncClient", mock_async_client)

    result = await http_verify("http://slow.example.com", timeout=1)
    assert result["status"] is None
    assert result["error"] == "timeout"
    assert result["live"] is False


@pytest.mark.asyncio
async def test_http_verify_ssl_error(monkeypatch):
    """Test HTTP verification SSL error handling."""

    class MockAsyncContext:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def head(self, url):
            raise httpx.RequestError("SSL certificate verification failed")

    def mock_async_client(**kwargs):
        return MockAsyncContext()

    monkeypatch.setattr("httpx.AsyncClient", mock_async_client)

    result = await http_verify("https://bad-cert.example.com")
    assert result["status"] is None
    assert result["error"] is not None
    assert result["live"] is False


@pytest.mark.asyncio
async def test_http_verify_connection_error(monkeypatch):
    """Test HTTP verification connection error handling."""

    class MockAsyncContext:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def head(self, url):
            raise httpx.ConnectError("Failed to establish connection")

    def mock_async_client(**kwargs):
        return MockAsyncContext()

    monkeypatch.setattr("httpx.AsyncClient", mock_async_client)

    result = await http_verify("http://unreachable.example.com")
    assert result["status"] is None
    assert "connection_error" in result["error"]
    assert result["live"] is False


@pytest.mark.asyncio
async def test_http_verify_response_time(monkeypatch):
    """Test that response time is calculated correctly."""

    class MockAsyncContext:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def head(self, url):
            await asyncio.sleep(0.05)  # 50ms delay
            return MockResponse(200, {})

    def mock_async_client(**kwargs):
        return MockAsyncContext()

    monkeypatch.setattr("httpx.AsyncClient", mock_async_client)

    result = await http_verify("http://example.com")
    # Response time should be >= 50ms (accounting for execution overhead)
    assert result["time_ms"] >= 40


@pytest.mark.asyncio
async def test_batch_http_verify(monkeypatch):
    """Test batch verification of multiple URLs."""

    class MockAsyncContext:
        def __init__(self, status_map: dict):
            self.status_map = status_map

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def head(self, url):
            status = self.status_map.get(url, 200)
            return MockResponse(status, {"Server": "mock"})

    status_map = {
        "http://a.example.com": 200,
        "http://b.example.com": 404,
        "http://c.example.com": 200,
    }

    def mock_async_client(**kwargs):
        return MockAsyncContext(status_map)

    monkeypatch.setattr("httpx.AsyncClient", mock_async_client)

    urls = list(status_map.keys())
    results = await batch_http_verify(urls, concurrency=2)

    assert len(results) == 3
    assert results[0]["status"] == 200
    assert results[1]["status"] == 404
    assert results[2]["status"] == 200


@pytest.mark.asyncio
async def test_batch_http_verify_concurrency(monkeypatch):
    """Test that batch verify respects concurrency limit."""

    concurrent_count = 0
    max_concurrent = 0

    class MockAsyncContext:
        async def __aenter__(self):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            return self

        async def __aexit__(self, *args):
            nonlocal concurrent_count
            concurrent_count -= 1

        async def head(self, url):
            await asyncio.sleep(0.01)
            return MockResponse(200, {})

    def mock_async_client(**kwargs):
        return MockAsyncContext()

    monkeypatch.setattr("httpx.AsyncClient", mock_async_client)

    urls = [f"http://example{i}.com" for i in range(10)]
    results = await batch_http_verify(urls, concurrency=3)

    assert len(results) == 10
    assert max_concurrent <= 3  # Should never exceed concurrency limit
