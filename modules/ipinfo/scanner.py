"""IPinfo provider scaffold.

Uses IPinfo API (IPINFO_API_TOKEN) to fetch geolocation and ASN info.
"""

import os
from typing import Any, Dict

import httpx

from core.cache_utils import cache_aware_fetch
from core.module import BaseModule
from core.output import standard_response
from core.retry import retry


class IPInfoModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.provider = "ipinfo"
        self.api_token = os.environ.get("IPINFO_API_TOKEN")

    @retry(attempts=3, initial_backoff=1.0)
    def _call_api(self, ip_or_host: str) -> Dict[str, Any]:
        if not self.api_token:
            raise RuntimeError("Missing IPINFO_API_TOKEN")
        url = f"https://ipinfo.io/{ip_or_host}/json?token={self.api_token}"
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.json()

    def run(self, target: str) -> Dict[str, Any]:
        key = f"ipinfo:{target}"

        async def _fetch():
            return self._call_api(target)

        no_cache = os.environ.get("DARKRECONX_NO_CACHE", "0") == "1"
        refresh = os.environ.get("DARKRECONX_REFRESH_CACHE", "0") == "1"

        try:
            data, from_cache = __import__("asyncio").run(
                cache_aware_fetch(key, _fetch, refresh_cache=refresh, no_cache=no_cache, max_age=86400)
            )
        except Exception as e:
            # Backwards-compatible error shape for callers/tests
            resp = standard_response("ipinfo", error=str(e))
            resp["provider"] = self.provider
            resp["success"] = False
            resp["error"] = str(e)
            return resp

        # Return normalized structure but keep legacy top-level keys for compatibility
        data_out = {"provider": self.provider, "data": data, "cached": from_cache}
        resp = standard_response("ipinfo", data=data_out)
        # legacy fields expected by older callers/tests
        resp["provider"] = self.provider
        resp["success"] = True
        resp["data"] = data
        resp["cached"] = from_cache
        return resp
