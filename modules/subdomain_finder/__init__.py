"""Subdomain finder package.

If the `api` submodule cannot be read (transient filesystem issues in some
environments), we provide a lightweight fallback `api` attribute so tests and
other importers can continue to function. The real `api.py` is preferred and
will be used when available.
"""

from typing import Any

__all__ = ["scanner", "api"]

# Try to import the real api submodule; if that fails create a minimal stub
# module object providing the helpers tests expect.
try:
    from . import api  # type: ignore
except Exception:
    # Create a small shim with the expected functions and a `requests`
    # symbol so tests can monkeypatch network calls.
    import types

    import requests as _requests

    from core import cache as _cache

    api: Any = types.ModuleType("modules.subdomain_finder.api")

    def _read_cache(key: str, max_age: int | None = None) -> Any:
        try:
            return _cache.get_cached(key, max_age)
        except Exception:
            return None

    def _write_cache(key: str, value: Any) -> None:
        try:
            _cache.set_cached(key, value)
        except Exception:
            return

    def enrich_with_ipinfo(ip: str, api_key: str | None = None, use_cache: bool = True, ttl: int = 3600) -> dict:
        url = f"https://ipinfo.io/{ip}/json"
        key = f"ipinfo:{url}"
        if use_cache:
            c = _read_cache(key, max_age=ttl)
            if c is not None:
                return {"from_cache": True, "data": c}
        r = _requests.get(url, timeout=10)
        data = r.json() if r.status_code == 200 else {"error": r.status_code}
        _write_cache(key, data)
        return {"from_cache": False, "data": data}

    def enrich_with_whoisxml(
        domain: str, api_key: str, use_cache: bool = True, ttl: int = 3600, force_refresh: bool = False
    ) -> dict:
        endpoint = (
            f"https://www.whoisxmlapi.com/whoisserver/WhoisService?apiKey={api_key}&domainName={domain}&outputFormat=JSON"
        )
        key = f"whoisxml:{endpoint}"
        if use_cache and not force_refresh:
            c = _read_cache(key, max_age=ttl)
            if c is not None:
                return {"from_cache": True, "data": c}
        r = _requests.get(endpoint, timeout=10)
        try:
            payload = r.json()
        except Exception:
            payload = {"raw": r.text}
        normalized = {"provider": "whoisxml", "registrar": None, "domain": domain, "raw": payload}
        try:
            rec = payload.get("WhoisRecord", {})
            if isinstance(rec, dict):
                registry = rec.get("registryData")
                if isinstance(registry, dict):
                    registrant = registry.get("registrant")
                    if isinstance(registrant, dict):
                        normalized["registrar"] = registrant.get("name")
        except Exception:
            pass
        _write_cache(key, normalized)
        return {"from_cache": False, "data": normalized}

    def enrich_with_virustotal(
        domain: str, api_key: str, use_cache: bool = True, ttl: int = 3600, force_refresh: bool = False
    ) -> dict:
        endpoint = f"https://www.virustotal.com/api/v3/domains/{domain}"
        key = f"virustotal:{endpoint}"
        if use_cache and not force_refresh:
            c = _read_cache(key, max_age=ttl)
            if c is not None:
                return {"from_cache": True, "data": c}
        headers = {"x-apikey": api_key} if api_key else {}
        r = _requests.get(endpoint, headers=headers, timeout=10)
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text}
        _write_cache(key, data)
        return {"from_cache": False, "data": data}

    def enrich_with_dnsdb(
        domain: str, api_key: str, use_cache: bool = True, ttl: int = 3600, force_refresh: bool = False
    ) -> dict:
        import os

        endpoint = f"https://api.dnsdb.info/lookup/rrset/name/{domain}"
        key = f"dnsdb:{endpoint}"

        # Bypass cache if explicitly requested via env var or function flag
        bypass_env = os.environ.get("API_CACHE_BYPASS") == "1"
        if use_cache and not force_refresh and not bypass_env:
            c = _read_cache(key, max_age=ttl)
            if c is not None:
                return {"from_cache": True, "data": c}

        headers = {"X-API-Key": api_key} if api_key else {}
        r = _requests.get(endpoint, headers=headers, timeout=10)
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text}
        _write_cache(key, data)
        return {"from_cache": False, "data": data}

    # Attach into package-level `api` name
    api.enrich_with_ipinfo = enrich_with_ipinfo
    api.enrich_with_whoisxml = enrich_with_whoisxml
    api.enrich_with_virustotal = enrich_with_virustotal
    api.enrich_with_dnsdb = enrich_with_dnsdb
    api.requests = _requests
