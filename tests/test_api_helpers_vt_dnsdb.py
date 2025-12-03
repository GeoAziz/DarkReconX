import os

import core.cache as cache_mod
from modules.subdomain_finder import api as api_helpers


class DummyResp:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def json(self):
        return self._json


def test_virustotal_cache_and_force_refresh(monkeypatch):
    domain = "example.com"
    endpoint = f"https://www.virustotal.com/api/v3/domains/{domain}"
    cache_key = f"virustotal:{endpoint}"
    p = cache_mod._key_to_path(cache_key)
    if p.exists():
        p.unlink()

    called = {"count": 0}

    def fake_get(url, headers=None, timeout=10):
        called["count"] += 1
        return DummyResp(200, json_data={"data": {"id": domain}})

    monkeypatch.setattr(api_helpers.requests, "get", fake_get)

    # first call should fetch and write cache
    r1 = api_helpers.enrich_with_virustotal(domain, api_key="KEY", use_cache=True, ttl=10, force_refresh=True)
    assert r1.get("from_cache") is False
    assert called["count"] == 1

    # second call should read from cache (no network)
    r2 = api_helpers.enrich_with_virustotal(domain, api_key="KEY", use_cache=True, ttl=3600, force_refresh=False)
    assert r2.get("from_cache") is True
    assert called["count"] == 1

    # force refresh should call network again
    r3 = api_helpers.enrich_with_virustotal(domain, api_key="KEY", use_cache=True, ttl=3600, force_refresh=True)
    assert r3.get("from_cache") is False
    assert called["count"] == 2


def test_dnsdb_refresh_and_cache_bypass(monkeypatch):
    domain = "example.com"
    endpoint = f"https://api.dnsdb.info/lookup/rrset/name/{domain}"
    cache_key = f"dnsdb:{endpoint}"
    p = cache_mod._key_to_path(cache_key)
    if p.exists():
        p.unlink()

    called = {"count": 0}

    def fake_get(url, headers=None, timeout=10):
        called["count"] += 1
        return DummyResp(200, json_data={"data": [{"name": domain, "type": "A"}]})

    monkeypatch.setattr(api_helpers.requests, "get", fake_get)

    # normal fetch writes cache
    r1 = api_helpers.enrich_with_dnsdb(domain, api_key="KEY", use_cache=True, ttl=10, force_refresh=False)
    assert called["count"] == 1
    assert r1.get("from_cache") is False

    # read from cache
    r2 = api_helpers.enrich_with_dnsdb(domain, api_key="KEY", use_cache=True, ttl=3600, force_refresh=False)
    assert r2.get("from_cache") is True
    assert called["count"] == 1

    # bypass via function param
    r3 = api_helpers.enrich_with_dnsdb(domain, api_key="KEY", use_cache=False, ttl=3600, force_refresh=False)
    assert r3.get("from_cache") is False
    assert called["count"] == 2

    # bypass via env var
    os.environ["API_CACHE_BYPASS"] = "1"
    r4 = api_helpers.enrich_with_dnsdb(domain, api_key="KEY", use_cache=True, ttl=3600, force_refresh=False)
    assert r4.get("from_cache") is False
    assert called["count"] == 3
    os.environ.pop("API_CACHE_BYPASS", None)
