"""Censys provider module.

This provider queries the Censys API to gather certificate and host data,
including SSL/TLS information, HTTP headers, and historical data.
It uses environment variables `CENSYS_API_ID` and `CENSYS_API_SECRET`
and honors cache flags via `DARKRECONX_NO_CACHE` and `DARKRECONX_REFRESH_CACHE`.

Note: Censys API requires a valid account with API credentials.
"""

import os
from typing import Any, Dict

import httpx
from httpx import BasicAuth

from core.cache_utils import cache_aware_fetch
from core.module import BaseModule
from core.retry import retry


class CensysModule(BaseModule):
    """Censys host/certificate intelligence provider."""

    def __init__(self):
        super().__init__()
        self.provider = "censys"
        self.api_id = os.environ.get("CENSYS_API_ID")
        self.api_secret = os.environ.get("CENSYS_API_SECRET")
        self.base_url = "https://api.censys.io/v2"

    @retry(attempts=3, initial_backoff=1.0)
    def _call_api(self, target: str) -> Dict[str, Any]:
        """Call Censys API to fetch host information."""
        if not self.api_id or not self.api_secret:
            raise RuntimeError("Missing CENSYS_API_ID or CENSYS_API_SECRET")

        auth = BasicAuth(self.api_id, self.api_secret)

        # Determine if target is IP or domain
        if target.replace(".", "").isdigit():
            # Looks like an IP
            url = f"{self.base_url}/hosts/{target}"
            with httpx.Client(timeout=10.0, auth=auth) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.json()
        else:
            # Looks like a domain; search for it
            url = f"{self.base_url}/certificates"
            params = {"q": f"parsed.names: {target}"}
            with httpx.Client(timeout=10.0, auth=auth) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()

    def run(self, target: str) -> Dict[str, Any]:
        """Execute Censys lookup for the target."""
        key = f"censys:{target}"

        async def _fetch():
            return self._call_api(target)

        no_cache = os.environ.get("DARKRECONX_NO_CACHE", "0") == "1"
        refresh = os.environ.get("DARKRECONX_REFRESH_CACHE", "0") == "1"

        try:
            data, from_cache = __import__("asyncio").run(
                cache_aware_fetch(key, _fetch, refresh_cache=refresh, no_cache=no_cache, max_age=86400)
            )
        except Exception as e:
            return {"provider": self.provider, "success": False, "error": str(e)}

        # Normalize response based on whether it's host or certificate data
        if "services" in data:
            # Host data
            normalized = {
                "ip": data.get("ip"),
                "hostname": data.get("dns", {}).get("names", []),
                "ports": [svc.get("port") for svc in data.get("services", [])],
                "services": [
                    {
                        "port": svc.get("port"),
                        "service": svc.get("service_name", "unknown"),
                    }
                    for svc in data.get("services", [])
                ],
                "os": data.get("autonomous_system", {}).get("name", ""),
            }
        else:
            # Certificate data
            results = data.get("results", [])
            normalized = {
                "certificates": len(results),
                "names": data.get("names", []),
                "issuer": results[0].get("issuer") if results else None,
            }

        return {"provider": self.provider, "success": True, "data": normalized, "cached": from_cache}
