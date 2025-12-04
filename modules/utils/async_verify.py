"""Async HTTP verification module for host/subdomain validation.

This module provides async-safe HTTP verification using httpx.AsyncClient
to check if hosts/subdomains are live and responding.
"""

import asyncio
import time
from typing import Any, Dict, Optional

import httpx


async def http_verify(url: str, timeout: float = 5.0, method: str = "HEAD", follow_redirects: bool = False) -> Dict[str, Any]:
    """Verify a URL is live by making an async HTTP HEAD or GET request.

    Args:
        url: Full URL to verify (e.g., http://example.com or https://sub.example.com:8080).
        timeout: Request timeout in seconds.
        method: HTTP method ("HEAD" or "GET").
        follow_redirects: Whether to follow redirects.

    Returns:
        Dict with keys:
        - "url": The URL that was checked.
        - "status": HTTP status code (int) if successful, None on error.
        - "headers": Response headers dict if successful, empty dict on error.
        - "time_ms": Response time in milliseconds.
        - "error": Error message if verification failed.
        - "live": Boolean indicating if host is live (status 2xx or 3xx).

    Example:
        result = await http_verify("http://example.com", timeout=5)
        # {"url": "http://example.com", "status": 200, "live": True, "time_ms": 120, ...}
    """
    start_time = time.monotonic()
    result: Dict[str, Any] = {
        "url": url,
        "status": None,
        "headers": {},
        "time_ms": 0,
        "error": None,
        "live": False,
    }

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=follow_redirects,
            verify=False,  # Disable SSL verification to allow self-signed certs
        ) as client:
            if method.upper() == "HEAD":
                resp = await client.head(url)
            else:
                resp = await client.get(url)

            result["status"] = resp.status_code
            result["headers"] = dict(resp.headers)
            result["live"] = 200 <= resp.status_code < 400  # 2xx and 3xx are "live"

    except asyncio.TimeoutError:
        result["error"] = "timeout"
    except httpx.ConnectError as e:
        result["error"] = f"connection_error: {str(e)[:50]}"
    except httpx.RequestError as e:
        # Catches SSL and other request-level errors
        result["error"] = f"request_error: {str(e)[:50]}"
    except httpx.HTTPError as e:
        result["error"] = f"http_error: {str(e)[:50]}"
    except Exception as e:
        result["error"] = f"unknown_error: {str(e)[:50]}"

    result["time_ms"] = round((time.monotonic() - start_time) * 1000, 2)
    return result


async def batch_http_verify(urls: list, timeout: float = 5.0, concurrency: int = 10, method: str = "HEAD") -> list:
    """Verify multiple URLs concurrently with a concurrency limit.

    Args:
        urls: List of URLs to verify.
        timeout: Timeout per request.
        concurrency: Max concurrent requests.
        method: HTTP method to use.

    Returns:
        List of verification results (one per URL).
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def _verify_with_semaphore(url: str) -> Dict[str, Any]:
        async with semaphore:
            return await http_verify(url, timeout=timeout, method=method)

    results = await asyncio.gather(*[_verify_with_semaphore(url) for url in urls], return_exceptions=False)
    return results


# Mock helper for testing
class MockAsyncClient:
    """Mock httpx.AsyncClient for testing async_verify without network calls."""

    def __init__(self, status_code: int = 200, headers: Optional[dict] = None, delay_ms: float = 10):
        self.status_code = status_code
        self.headers = headers or {"Server": "mock"}
        self.delay_ms = delay_ms

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def head(self, url: str):
        await asyncio.sleep(self.delay_ms / 1000)
        return MockResponse(self.status_code, self.headers)

    async def get(self, url: str):
        await asyncio.sleep(self.delay_ms / 1000)
        return MockResponse(self.status_code, self.headers)


class MockResponse:
    """Mock httpx.Response for testing."""

    def __init__(self, status_code: int, headers: dict):
        self.status_code = status_code
        self.headers = headers
