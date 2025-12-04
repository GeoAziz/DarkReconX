import json
import os
import types

import pytest


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    monkeypatch.delenv("DNSDB_API_KEY", raising=False)
    monkeypatch.delenv("WHOISXML_API_KEY", raising=False)
    monkeypatch.delenv("IPINFO_API_TOKEN", raising=False)
    yield


def test_dnsdb_missing_key():
    from modules.dnsdb.scanner import DNSDBModule

    mod = DNSDBModule()
    res = mod.run("example.com")
    assert res["success"] is False
    assert "Missing" in res.get("error", "")


def test_whoisxml_missing_key():
    from modules.whoisxml.scanner import WhoisXMLModule

    mod = WhoisXMLModule()
    res = mod.run("example.com")
    assert res["success"] is False
    assert "Missing" in res.get("error", "")


def test_ipinfo_missing_key():
    from modules.ipinfo.scanner import IPInfoModule

    mod = IPInfoModule()
    res = mod.run("8.8.8.8")
    assert res["success"] is False
    assert "Missing" in res.get("error", "")


def test_providers_with_cache(monkeypatch, tmp_path):
    # Provide fake API keys
    monkeypatch.setenv("DNSDB_API_KEY", "fake")
    monkeypatch.setenv("WHOISXML_API_KEY", "fake")
    monkeypatch.setenv("IPINFO_API_TOKEN", "fake")

    # Patch cache_aware_fetch to return fake data
    async def fake_cache(key, fetch_fn, refresh_cache=False, no_cache=False, max_age=None):
        return ({"ok": True}, False)

    # Patch in both places: the module and where it's imported
    monkeypatch.setattr("core.cache_utils.cache_aware_fetch", fake_cache)
    monkeypatch.setattr("modules.dnsdb.scanner.cache_aware_fetch", fake_cache)
    monkeypatch.setattr("modules.whoisxml.scanner.cache_aware_fetch", fake_cache)
    monkeypatch.setattr("modules.ipinfo.scanner.cache_aware_fetch", fake_cache)

    from modules.dnsdb.scanner import DNSDBModule
    from modules.ipinfo.scanner import IPInfoModule
    from modules.whoisxml.scanner import WhoisXMLModule

    d = DNSDBModule()
    w = WhoisXMLModule()
    i = IPInfoModule()

    rd = d.run("example.com")
    rw = w.run("example.com")
    ri = i.run("8.8.8.8")

    assert rd["success"] is True
    assert rw["success"] is True
    assert ri["success"] is True
