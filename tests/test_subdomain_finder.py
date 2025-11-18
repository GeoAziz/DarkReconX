import dns.resolver
import pytest
from pathlib import Path
from types import SimpleNamespace

from modules.subdomain_finder.scanner import SubdomainFinder


def test_subdomain_finder_dns_and_verify(monkeypatch, tmp_path):
    # create a small wordlist
    wl = tmp_path / "wl.txt"
    wl.write_text("www\nmail\n")

    # mock dns.resolver.resolve: return a truthy value for www.example.com
    def fake_resolve(name, rdtype):
        if name == "www.example.com":
            return ["1.2.3.4"]
        raise dns.resolver.NXDOMAIN()

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)

    # patch HTTPClient.head so we don't make real network calls
    called = {"urls": []}

    def fake_head(self, url, **kwargs):
        called["urls"].append(url)
        if "www.example.com" in url:
            return 200
        return None

    monkeypatch.setattr("core.http_client.HTTPClient.head", fake_head, raising=False)

    finder = SubdomainFinder("example.com", wordlist=str(wl), use_tor=False, workers=2, verify_http=True)
    results = finder.run()

    assert results == ["www.example.com"]
    # ensure HEAD was attempted for the discovered host
    assert any("www.example.com" in u for u in called["urls"]) 
