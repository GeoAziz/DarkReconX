"""core.tor_client

Manage Tor daemon / SOCKS proxy usage (skeleton).
"""

class TorClient:
    def __init__(self, socks_host: str = "127.0.0.1", socks_port: int = 9050):
        self.socks_host = socks_host
        self.socks_port = socks_port

    def start(self):
        """Start or connect to Tor service (placeholder)."""
        raise NotImplementedError("TorClient.start not implemented yet")

    def stop(self):
        """Stop Tor service (placeholder)."""
        raise NotImplementedError("TorClient.stop not implemented yet")
