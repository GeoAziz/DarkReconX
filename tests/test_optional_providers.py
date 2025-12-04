"""Tests for optional providers: Shodan, Censys, VirusTotal."""

import pytest


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    """Clear API keys before each test."""
    monkeypatch.delenv("SHODAN_API_KEY", raising=False)
    monkeypatch.delenv("CENSYS_API_ID", raising=False)
    monkeypatch.delenv("CENSYS_API_SECRET", raising=False)
    monkeypatch.delenv("VT_API_KEY", raising=False)
    yield


def test_shodan_missing_key():
    """Test Shodan provider handles missing API key gracefully."""
    from modules.shodan import ShodanModule

    mod = ShodanModule()
    res = mod.run("8.8.8.8")
    assert res["success"] is False
    assert "Missing" in res.get("error", "")


def test_censys_missing_key():
    """Test Censys provider handles missing API credentials gracefully."""
    from modules.censys.scanner import CensysModule

    mod = CensysModule()
    res = mod.run("8.8.8.8")
    assert res["success"] is False
    assert "Missing" in res.get("error", "")


def test_virustotal_missing_key():
    """Test VirusTotal provider handles missing API key gracefully."""
    from modules.virustotal.scanner import VirusTotalModule

    mod = VirusTotalModule()
    res = mod.run("8.8.8.8")
    assert res["success"] is False
    assert "Missing" in res.get("error", "")


def test_optional_providers_with_cache(monkeypatch):
    """Test optional providers work with mocked cache_aware_fetch."""
    monkeypatch.setenv("SHODAN_API_KEY", "fake")
    monkeypatch.setenv("CENSYS_API_ID", "fake")
    monkeypatch.setenv("CENSYS_API_SECRET", "fake")
    monkeypatch.setenv("VT_API_KEY", "fake")

    async def fake_cache(key, fetch_fn, refresh_cache=False, no_cache=False, max_age=None):
        return ({"data": {"attributes": {}}}, False)

    monkeypatch.setattr("modules.shodan.scanner.cache_aware_fetch", fake_cache)
    monkeypatch.setattr("modules.censys.scanner.cache_aware_fetch", fake_cache)
    monkeypatch.setattr("modules.virustotal.scanner.cache_aware_fetch", fake_cache)

    from modules.censys.scanner import CensysModule
    from modules.shodan import ShodanModule
    from modules.virustotal.scanner import VirusTotalModule

    s = ShodanModule()
    c = CensysModule()
    v = VirusTotalModule()

    rs = s.run("8.8.8.8")
    rc = c.run("8.8.8.8")
    rv = v.run("8.8.8.8")

    assert rs["success"] is True
    assert rc["success"] is True
    assert rv["success"] is True
