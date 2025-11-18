"""Unit tests for AsyncSubdomainFinder with mocked async DNS and HTTP."""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure project root is in path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.mark.asyncio
async def test_async_scanner_dns_only(monkeypatch, tmp_path):
    """Test async scanner with DNS resolution only (no HTTP verification)."""
    from modules.subdomain_finder.async_scanner import AsyncSubdomainFinder

    # Create a small wordlist
    wordlist = tmp_path / "test_words.txt"
    wordlist.write_text("www\napi\nmail\ninvalid", encoding="utf-8")

    # Mock dns.asyncresolver.resolve
    async def mock_resolve(fqdn, record_type):
        if fqdn in ["www.example.com", "api.example.com"]:
            # Return a mock answer with an IP
            mock_answer = MagicMock()
            mock_answer.__iter__ = lambda self: iter([MagicMock(__str__=lambda s: "1.2.3.4")])
            return mock_answer
        else:
            # Raise exception for unresolvable domains
            raise Exception("NXDOMAIN")

    finder = AsyncSubdomainFinder(
        domain="example.com",
        wordlist=str(wordlist),
        concurrency=10,
        verbose=False,
        verify_http=False,
    )

    # Patch the asyncresolver.resolve method
    with patch.object(finder.asyncresolver, "resolve", side_effect=mock_resolve):
        results = await finder.run_async()

    # Should find 2 subdomains
    assert len(results) == 2
    assert any(r["fqdn"] == "www.example.com" for r in results)
    assert any(r["fqdn"] == "api.example.com" for r in results)
    assert all("ip" in r for r in results)


@pytest.mark.asyncio
async def test_async_scanner_with_http_verification(monkeypatch, tmp_path):
    """Test async scanner with HTTP verification enabled."""
    from modules.subdomain_finder.async_scanner import AsyncSubdomainFinder

    # Create a small wordlist
    wordlist = tmp_path / "test_words.txt"
    wordlist.write_text("www\napi", encoding="utf-8")

    # Mock dns.asyncresolver.resolve
    async def mock_resolve(fqdn, record_type):
        mock_answer = MagicMock()
        mock_answer.__iter__ = lambda self: iter([MagicMock(__str__=lambda s: "1.2.3.4")])
        return mock_answer

    # Mock httpx.AsyncClient
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = MagicMock()
    mock_client.head = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    finder = AsyncSubdomainFinder(
        domain="example.com",
        wordlist=str(wordlist),
        concurrency=10,
        verbose=False,
        verify_http=True,
        http_timeout=5.0,
    )

    # Patch both DNS and httpx
    with patch.object(finder.asyncresolver, "resolve", side_effect=mock_resolve):
        with patch("httpx.AsyncClient", return_value=mock_client):
            results = await finder.run_async()

    # Should find 2 subdomains with HTTP status
    assert len(results) == 2
    assert all("http_status" in r for r in results)
    assert all(r["http_status"] == 200 for r in results)


def test_async_scanner_sync_wrapper(monkeypatch, tmp_path):
    """Test the synchronous wrapper run() method."""
    from modules.subdomain_finder.async_scanner import AsyncSubdomainFinder

    wordlist = tmp_path / "test_words.txt"
    wordlist.write_text("www", encoding="utf-8")

    async def mock_resolve(fqdn, record_type):
        mock_answer = MagicMock()
        mock_answer.__iter__ = lambda self: iter([MagicMock(__str__=lambda s: "1.2.3.4")])
        return mock_answer

    finder = AsyncSubdomainFinder(
        domain="example.com",
        wordlist=str(wordlist),
        concurrency=10,
        verbose=False,
    )

    with patch.object(finder.asyncresolver, "resolve", side_effect=mock_resolve):
        results = finder.run()

    assert len(results) == 1
    assert results[0]["fqdn"] == "www.example.com"


def test_async_scanner_missing_wordlist(tmp_path):
    """Test async scanner behavior when wordlist is missing."""
    from modules.subdomain_finder.async_scanner import AsyncSubdomainFinder

    finder = AsyncSubdomainFinder(
        domain="example.com",
        wordlist=str(tmp_path / "nonexistent.txt"),
        concurrency=10,
    )

    results = finder.run()
    assert results == []
