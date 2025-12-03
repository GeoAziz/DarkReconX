"""API integration helpers for subdomain enrichment.

This module provides small, safe wrappers for several external providers
with optional caching via `core.cache`. Each function accepts a `use_cache`
boolean (default True) to allow bypassing the cache during testing.
"""

import logging
import os
from typing import Dict, Optional
from urllib.parse import quote_plus

import requests

from core import cache

logger = logging.getLogger(__name__)


def _use_cache_override(use_cache: Optional[bool]) -> bool:
    # env var takes precedence when explicitly set
    env = os.environ.get("API_CACHE_BYPASS")
    if env and env.strip() in ("1", "true", "True"):
        return False
    if use_cache is None:
        return True
    return bool(use_cache)


def _normalize_virustotal(raw: Dict) -> Dict:
    # Normalize VT v3 responses into unified shape where possible.
    try:
        out = {
            "provider": "virustotal",
            "hostname": None,
            "ip": None,
            "asn": None,
            "registrar": None,
            "location": {},
            "raw": raw,
        }
        if not isinstance(raw, dict):
            return out
        data = raw.get("data") or raw
        # hostname is often in data['id'] for domain objects
        hostname = None
        if isinstance(data, dict):
            hostname = data.get("id") or data.get("name")
            attrs = data.get("attributes") if isinstance(data.get("attributes"), dict) else {}
            # try to extract network info
            network = attrs.get("network") or {}
            if isinstance(network, dict):
                out["ip"] = network.get("ip_address") or out.get("ip")
                out["asn"] = network.get("as_owner") or out.get("asn")
            # registrar might be under whois relationships
            whois = data.get("whois") or attrs.get("whois") or attrs.get("registrar")
            if isinstance(whois, dict):
                out["registrar"] = whois.get("registrar_name") or whois.get("registrar")
            # best-effort hostname
        out["hostname"] = hostname
        return out
    except Exception as e:
        logger.exception("VT normalization error: %s", e)
        return {"provider": "virustotal", "raw": raw}


def _normalize_dnsdb(raw: Dict) -> Dict:
    # Normalize DNSDB/pDNS responses into unified shape (first useful record)
    try:
        if not isinstance(raw, dict):
            return {"provider": "dnsdb", "raw": raw}

        records = []
        if isinstance(raw.get("data"), list):
            records = raw.get("data")
        elif isinstance(raw.get("rrset"), list):
            records = raw.get("rrset")
        else:
            records = [raw]

        # pick first record and extract common fields
        rec = records[0] if records else {}
        hostname = rec.get("name") or rec.get("rrname") or rec.get("rrset") or rec.get("rrname")
        ip = None
        # various keys for IP
        if isinstance(rec.get("rdata"), list) and rec.get("rdata"):
            ip = rec.get("rdata")[0]
        ip = ip or rec.get("rr") or rec.get("value") or rec.get("ip")
        return {"provider": "dnsdb", "hostname": hostname, "ip": ip, "raw_records": records}
    except Exception as e:
        logger.exception("DNSDB normalization error: %s", e)
        return {"provider": "dnsdb", "raw": raw}


def _normalize_whoisxml(raw: Dict) -> Dict:
    try:
        if not isinstance(raw, dict):
            return {"provider": "whoisxml", "raw": raw}
        # try common fields
        rec = raw.get("WhoisRecord") or raw.get("whoisRecord") or raw
        registrar = None
        registrant = {}
        if isinstance(rec, dict):
            registry = rec.get("registryData") or rec.get("registrar") or rec
            if isinstance(registry, dict):
                registrar = registry.get("registrarName") or registry.get("registrar") or registry.get("registrant")
                registrant = registry.get("registrant") or {}
        location = {}
        if isinstance(registrant, dict):
            location = {"country": registrant.get("country"), "city": registrant.get("city")}
        return {"provider": "whoisxml", "registrar": registrar, "registrant": registrant, "location": location}
    except Exception as e:
        logger.exception("WhoisXML normalization error: %s", e)
        return {"provider": "whoisxml", "raw": raw}


def _normalize_ipinfo(raw: Dict) -> Dict:
    try:
        if not isinstance(raw, dict):
            return {"provider": "ipinfo", "raw": raw}
        normalized = {
            "provider": "ipinfo",
            "ip": raw.get("ip"),
            "hostname": raw.get("hostname"),
            "org": raw.get("org"),
            "location": {"country": raw.get("country"), "city": raw.get("city")},
            "raw": raw,
        }
        return normalized
    except Exception as e:
        logger.exception("ipinfo normalization error: %s", e)
        return {"provider": "ipinfo", "raw": raw}


def enrich_with_securitytrails(domain: str, api_key: Optional[str], use_cache: Optional[bool] = True, ttl: int = 3600) -> Dict:
    # placeholder — keep signature consistent with other helpers
    logger.debug("securitytrails enrichment not implemented for %s", domain)
    return {"securitytrails": None, "domain": domain}


def enrich_with_virustotal(
    domain: str, api_key: Optional[str], use_cache: Optional[bool] = True, ttl: int = 3600, force_refresh: bool = False
) -> Dict:
    """Query VirusTotal v3 for a domain with optional caching.

    Returns dict with either {'data': ...} or {'error': ...} and a
    'from_cache' boolean when applicable.
    """
    if not api_key:
        return {"error": "missing_api_key", "domain": domain}

    endpoint = f"https://www.virustotal.com/api/v3/domains/{quote_plus(domain)}"
    cache_key = f"virustotal:{endpoint}"
    real_cache = _use_cache_override(use_cache)
    if real_cache and not force_refresh:
        cached = cache.get_cached(cache_key, max_age=ttl)
        if cached is not None:
            logger.debug("virustotal cache hit for %s", domain)
            return {"from_cache": True, "data": cached}

    headers = {"x-apikey": api_key}
    try:
        resp = requests.get(endpoint, headers=headers, timeout=10)
    except requests.RequestException as e:
        logger.warning("virustotal request failed for %s: %s", domain, e)
        return {"error": "request_exception", "exc": str(e), "domain": domain}

    if resp.status_code != 200:
        logger.info("virustotal non-200 for %s: %s", domain, resp.status_code)
        return {"error": "non_200", "status_code": resp.status_code, "text": resp.text}

    try:
        j = resp.json()
    except Exception as e:
        return {"error": "invalid_json", "exc": str(e), "text": resp.text}

    if real_cache or force_refresh:
        try:
            cache.set_cached(cache_key, j)
        except Exception:
            logger.debug("failed to write virustotal cache for %s", domain)

    return {"from_cache": False, "data": _normalize_virustotal(j)}


def enrich_with_dnsdb(
    domain: str, api_key: Optional[str], use_cache: Optional[bool] = True, ttl: int = 3600, force_refresh: bool = False
) -> Dict:
    """Query DNSDB Scout or similar pDNS provider.

    This is a minimal implementation that assumes a generic GET endpoint;
    DNSDB's real API may require different paths; treat this as a safe
    best-effort helper with caching.
    """
    if not api_key:
        return {"error": "missing_api_key", "domain": domain}

    endpoint = f"https://api.dnsdb.info/lookup/rrset/name/{quote_plus(domain)}"
    cache_key = f"dnsdb:{endpoint}"
    real_cache = _use_cache_override(use_cache)
    if real_cache and not force_refresh:
        cached = cache.get_cached(cache_key, max_age=ttl)
        if cached is not None:
            return {"from_cache": True, "data": cached}

    headers = {"Accept": "application/json", "X-API-Key": api_key}
    try:
        resp = requests.get(endpoint, headers=headers, timeout=10)
    except requests.RequestException as e:
        return {"error": "request_exception", "exc": str(e), "domain": domain}

    if resp.status_code != 200:
        return {"error": "non_200", "status_code": resp.status_code, "text": resp.text}

    try:
        j = resp.json()
    except Exception as e:
        return {"error": "invalid_json", "exc": str(e), "text": resp.text}

    if real_cache or force_refresh:
        try:
            cache.set_cached(cache_key, j)
        except Exception:
            logger.debug("failed to write dnsdb cache for %s", domain)

    return {"from_cache": False, "data": _normalize_dnsdb(j)}


def enrich_with_whoisxml(
    domain: str, api_key: Optional[str], use_cache: Optional[bool] = True, ttl: int = 3600, force_refresh: bool = False
) -> Dict:
    """Query WhoisXML's WHOIS API (simple wrapper).

    Endpoint: https://www.whoisxmlapi.com/whoisserver/WhoisService?domainName={domain}&apiKey={apiKey}&outputFormat=JSON
    """
    if not api_key:
        return {"error": "missing_api_key", "domain": domain}

    endpoint = f"https://www.whoisxmlapi.com/whoisserver/WhoisService?apiKey={quote_plus(api_key)}&domainName={quote_plus(domain)}&outputFormat=JSON"
    cache_key = f"whoisxml:{endpoint}"
    real_cache = _use_cache_override(use_cache)
    if real_cache and not force_refresh:
        cached = cache.get_cached(cache_key, max_age=ttl)
        if cached is not None:
            return {"from_cache": True, "data": cached}

    try:
        resp = requests.get(endpoint, timeout=10)
    except requests.RequestException as e:
        return {"error": "request_exception", "exc": str(e), "domain": domain}

    if resp.status_code != 200:
        return {"error": "non_200", "status_code": resp.status_code, "text": resp.text}

    try:
        j = resp.json()
    except Exception as e:
        return {"error": "invalid_json", "exc": str(e), "text": resp.text}

    if real_cache or force_refresh:
        try:
            cache.set_cached(cache_key, j)
        except Exception:
            logger.debug("failed to write whoisxml cache for %s", domain)

    return {"from_cache": False, "data": _normalize_whoisxml(j)}


def enrich_with_ipinfo(
    ip: str, api_key: Optional[str], use_cache: Optional[bool] = True, ttl: int = 3600, force_refresh: bool = False
) -> Dict:
    """Query ipinfo.io for IP intelligence. API token optional for elevated quota.
    Endpoint: https://ipinfo.io/{ip}/json?token={token}
    """
    if not ip:
        return {"error": "missing_ip"}

    endpoint = f"https://ipinfo.io/{quote_plus(ip)}/json"
    if api_key:
        endpoint = endpoint + f"?token={quote_plus(api_key)}"

    cache_key = f"ipinfo:{endpoint}"
    real_cache = _use_cache_override(use_cache)
    if real_cache and not force_refresh:
        cached = cache.get_cached(cache_key, max_age=ttl)
        if cached is not None:
            return {"from_cache": True, "data": cached}

    try:
        resp = requests.get(endpoint, timeout=10)
    except requests.RequestException as e:
        return {"error": "request_exception", "exc": str(e), "ip": ip}

    if resp.status_code != 200:
        return {"error": "non_200", "status_code": resp.status_code, "text": resp.text}

    try:
        j = resp.json()
    except Exception as e:
        return {"error": "invalid_json", "exc": str(e), "text": resp.text}

    if real_cache or force_refresh:
        try:
            cache.set_cached(cache_key, j)
        except Exception:
            logger.debug("failed to write ipinfo cache for %s", ip)

    return {"from_cache": False, "data": _normalize_ipinfo(j)}
