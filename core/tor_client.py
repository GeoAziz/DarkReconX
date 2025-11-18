"""core.tor_client

Tor client helper that routes requests through a local Tor SOCKS5 proxy.
Provides a simple wrapper around :mod:`requests` Session configured to use
Tor, plus a small helper to request a new identity using :mod:`stem` if
available. This file aims to be safe when Tor is not running: it will raise
clear exceptions or return None for network calls but won't crash during import.
"""

from typing import Optional
import os
import requests
from rich.console import Console

console = Console()

# Default Tor SOCKS proxy (Tor Browser / tor daemon default)
TOR_PROXY = {
    "http": "socks5h://127.0.0.1:9050",
    "https": "socks5h://127.0.0.1:9050",
}


class TorClient:
    """Simple Tor-backed HTTP client.

    This uses a :class:`requests.Session` configured to talk via the Tor
    SOCKS5 proxy. Calls return text on success or ``None`` on failure.
    """

    def __init__(self, socks_host: str = "127.0.0.1", socks_port: int = 9050):
        self.socks_host = socks_host
        self.socks_port = socks_port
        self.session = requests.Session()
        # Use socks5h to ensure DNS resolution happens through the proxy
        self.session.proxies = TOR_PROXY

    def get(self, url: str, timeout: int = 15, **kwargs) -> Optional[str]:
        """Perform a GET request via Tor.

        Returns response text or None on error.
        """
        # Quick availability check to provide a clearer error when Tor isn't
        # running locally.
        if not is_tor_available(self.socks_host, self.socks_port):
            console.print(
                f"[yellow][TOR ERROR][/yellow] Tor SOCKS proxy not available at {self.socks_host}:{self.socks_port}. "
                "Start Tor (or Tor Browser) so a SOCKS5 proxy listens on this port."
            )
            return None

        try:
            resp = self.session.get(url, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            # Print a concise, user-friendly message instead of long urllib3 trace text
            console.print(f"[yellow][TOR ERROR][/yellow] Could not GET {url} via Tor. Target may be unreachable or Tor may not be routing correctly.")
            return None

    def head(self, url: str, timeout: int = 10, **kwargs) -> Optional[requests.Response]:
        try:
            return self.session.head(url, timeout=timeout, **kwargs)
        except Exception as e:
            console.print(f"[yellow][TOR ERROR][/yellow] Could not perform HEAD to {url} via Tor. Skipping verification for this host.")
            return None

    def post(self, url: str, data=None, timeout: int = 15, **kwargs) -> Optional[str]:
        """Perform a POST request via Tor and return response text or None."""
        if not is_tor_available(self.socks_host, self.socks_port):
            console.print(
                f"[yellow][TOR ERROR][/yellow] Tor SOCKS proxy not available at {self.socks_host}:{self.socks_port}. "
                "Start Tor (or Tor Browser) so a SOCKS5 proxy listens on this port."
            )
            return None

        try:
            resp = self.session.post(url, data=data, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            console.print(f"[yellow][TOR ERROR][/yellow] Could not POST to {url} via Tor. Target or Tor proxy may be unreachable.")
            return None

    def put(self, url: str, data=None, timeout: int = 15, **kwargs) -> Optional[str]:
        try:
            resp = self.session.put(url, data=data, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            console.print(f"[yellow][TOR ERROR][/yellow] Could not PUT to {url} via Tor.")
            return None

    def delete(self, url: str, timeout: int = 15, **kwargs) -> Optional[str]:
        try:
            resp = self.session.delete(url, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            console.print(f"[yellow][TOR ERROR][/yellow] Could not DELETE {url} via Tor.")
            return None

    def options(self, url: str, timeout: int = 15, **kwargs) -> Optional[str]:
        try:
            resp = self.session.options(url, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            console.print(f"[yellow][TOR ERROR][/yellow] Could not OPTIONS {url} via Tor.")
            return None

    def patch(self, url: str, data=None, timeout: int = 15, **kwargs) -> Optional[str]:
        try:
            resp = self.session.patch(url, data=data, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            console.print(f"[yellow][TOR ERROR][/yellow] Could not PATCH {url} via Tor.")
            return None


def new_tor_identity(control_port: int = 9051, password: Optional[str] = None) -> bool:
    """Request a new Tor identity (NEWNYM) using stem if available.

    Returns True if the signal was sent successfully, False otherwise. The
    function is safe to call even if :mod:`stem` isn't installed — it will
    print a warning and return False.
    """
    try:
        from stem import Signal
        from stem.control import Controller
    except Exception:
        console.print("[yellow]Stem not installed; cannot request new Tor identity.[/yellow]")
        return False

    try:
        with Controller.from_port(port=control_port) as controller:
            if password is None:
                # try to authenticate without password first
                try:
                    controller.authenticate()
                except Exception:
                    # fallback to environment variable
                    pw = os.environ.get("TOR_CONTROL_PASSWORD")
                    controller.authenticate(password=pw)
            else:
                controller.authenticate(password=password)
            controller.signal(Signal.NEWNYM)
            console.print("[green]Requested new Tor identity (NEWNYM).[/green]")
            return True
    except Exception as e:
        console.print(f"[red]Failed to request new identity: {e}[/red]")
        return False


def is_tor_available(host: str = "127.0.0.1", port: int = 9050, timeout: float = 1.0) -> bool:
    """Quick check whether a SOCKS5 proxy (Tor) is listening on host:port.

    This attempts to open a TCP socket to the proxy port and returns True if
    a connection can be established. The function is intentionally lightweight
    and used to provide clearer user-facing messages when Tor isn't running.
    """
    import socket

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


if __name__ == "__main__":
    # Simple smoke test: attempt to hit httpbin.org/ip via Tor and print.
    client = TorClient()
    html = client.get("http://httpbin.org/ip")
    if html:
        console.print(html)
    else:
        console.print("[yellow]Tor request failed. Make sure Tor is running locally on port 9050.[/yellow]")
