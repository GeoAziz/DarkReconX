"""core.http_client

Small HTTP client wrapper that can route requests through Tor using
``core.tor_client.TorClient`` or perform normal requests using
``requests.Session``. The goal is to provide a unified, simple interface
for modules to call.
"""

from typing import Optional
import requests
from rich.console import Console
from config.loader import get_config
from core.tor_client import TorClient

console = Console()

_CFG = get_config()


class HTTPClient:
    """Unified HTTP client for DarkReconX.

    Parameters
    ----------
    use_tor: bool
        If True, route requests via the local Tor SOCKS proxy with
        :class:`TorClient`.
    """

    def __init__(self, use_tor: Optional[bool] = None):
        # If not explicitly passed, read from config/default.yml
        cfg = _CFG.config if hasattr(_CFG, "config") else {}
        if use_tor is None:
            self.use_tor = bool(cfg.get("tor", {}).get("enabled", False))
        else:
            self.use_tor = bool(use_tor)

        if self.use_tor:
            # allow TorClient to be configured later if needed
            self.client = TorClient()
        else:
            self.client = requests.Session()

    def get(self, url: str, **kwargs) -> Optional[str]:
        """Perform a GET request and return response text or None on error."""
        try:
            if self.use_tor:
                return self.client.get(url, **kwargs)
            else:
                resp = self.client.get(url, timeout=10, **kwargs)
                resp.raise_for_status()
                return resp.text
        except Exception as e:
            console.print(f"[red]HTTP GET Error:[/red] {e}")
            return None

    def post(self, url: str, data=None, **kwargs) -> Optional[str]:
        try:
            if self.use_tor:
                # TorClient has a post implementation
                return self.client.post(url, data=data, **kwargs)
            else:
                resp = self.client.post(url, data=data, timeout=10, **kwargs)
                resp.raise_for_status()
                return resp.text
        except Exception as e:
            console.print(f"[red]HTTP POST Error:[/red] {e}")
            return None


if __name__ == "__main__":
    # Quick smoke tests. First, non-Tor request should work if network is available.
    console.print("[bold]HTTPClient smoke test (direct):[/bold]")
    client = HTTPClient(use_tor=False)
    text = client.get("http://httpbin.org/ip")
    console.print(text)

    console.print("[bold]HTTPClient smoke test (via Tor):[/bold]")
    # Check Tor availability first so the message is clear for users who
    # haven't started Tor locally.
    try:
        from core.tor_client import is_tor_available

        if not is_tor_available():
            console.print("[yellow]Tor does not appear to be running locally (127.0.0.1:9050). Skipping Tor smoke test.[/yellow]")
        else:
            tor_client = HTTPClient(use_tor=True)
            text2 = tor_client.get("http://httpbin.org/ip")
            console.print(text2)
    except Exception:
        console.print("[yellow]Could not import Tor availability checker; skipping Tor smoke test.[/yellow]")
