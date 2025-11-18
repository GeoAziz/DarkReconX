"""core.http_client

Simple HTTP client wrapper (skeleton) — will support direct + Tor routing.
"""

from typing import Optional

class HTTPClient:
    def __init__(self, tor_proxy: Optional[str] = None, timeout: int = 30):
        """Initialize HTTP client.

        Args:
            tor_proxy: SOCKS5 proxy string like "socks5h://127.0.0.1:9050" or None
            timeout: request timeout seconds
        """
        self.tor_proxy = tor_proxy
        self.timeout = timeout

    def get(self, url: str, **kwargs):
        """Placeholder for GET request implementation."""
        raise NotImplementedError("HTTPClient.get not implemented yet")

    def post(self, url: str, data=None, **kwargs):
        """Placeholder for POST request implementation."""
        raise NotImplementedError("HTTPClient.post not implemented yet")
