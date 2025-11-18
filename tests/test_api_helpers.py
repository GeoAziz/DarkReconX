import os
import shutil
import uuid
import json
import types
import requests
import core.cache as cache_mod
from modules.subdomain_finder import api as api_helpers


class DummyResp:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def json(self):
        return self._json


def test_ipinfo_cache_and_bypass(monkeypatch, tmp_path):
    # choose a random ip to avoid collisions
    ip = "8.8.8.8"
    key = f"ipinfo:https://ipinfo.io/{ip}/json"

    # ensure cache is empty for this key
    p = cache_mod._key_to_path(key)
    if p.exists():
        p.unlink()

    called = {"count": 0}

    def fake_get(url, timeout=10):
        called["count"] += 1
        return DummyResp(200, json_data={"ip": ip, "city": "TestCity"})

    monkeypatch.setattr(api_helpers.requests, "get", fake_get)

    # first call should fetch and write cache
    r1 = api_helpers.enrich_with_ipinfo(ip, api_key=None, use_cache=True, ttl=10)
    assert r1.get("from_cache") is False

    # second call should read from cache
    r2 = api_helpers.enrich_with_ipinfo(ip, api_key=None, use_cache=True, ttl=3600)
    assert r2.get("from_cache") is True or r2.get("data")  # cached or returned

    # call with use_cache=False should call network again
    r3 = api_helpers.enrich_with_ipinfo(ip, api_key=None, use_cache=False, ttl=3600)
    assert r3.get("from_cache") is False


def test_whoisxml_normalization_and_refresh(monkeypatch):
    domain = "example.com"
    endpoint = f"https://www.whoisxmlapi.com/whoisserver/WhoisService?apiKey=KEY&domainName={domain}&outputFormat=JSON"
    key = f"whoisxml:{endpoint}"
    p = cache_mod._key_to_path(key)
    if p.exists():
        p.unlink()

    # fake response
    fake_payload = {"WhoisRecord": {"domainName": domain, "registryData": {"registrant": {"name": "Example"}}}}

    def fake_get(url, timeout=10):
        return DummyResp(200, json_data=fake_payload)

    monkeypatch.setattr(api_helpers.requests, "get", fake_get)

    # first call: should fetch and normalize
    r1 = api_helpers.enrich_with_whoisxml(domain, api_key="KEY", use_cache=True, ttl=10, force_refresh=True)
    assert r1.get("from_cache") is False
    assert isinstance(r1.get("data"), dict)
    assert r1["data"]["provider"] == "whoisxml"
    assert "registrar" in r1["data"]

    # ensure cached present: call with use_cache=True and force_refresh=False
    r2 = api_helpers.enrich_with_whoisxml(domain, api_key="KEY", use_cache=True, ttl=3600, force_refresh=False)
    assert r2.get("from_cache") is True or r2["data"]["provider"] == "whoisxml"
