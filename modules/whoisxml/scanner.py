"""WhoisXML provider scaffold.

Uses WHOISXML API (WHOISXML_API_KEY) and caches responses.
"""

import os
from typing import Any, Dict

import httpx

from core.cache_utils import cache_aware_fetch
from core.module import BaseModule
from core.retry import retry


class WhoisXMLModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.provider = "whoisxml"
        self.api_key = os.environ.get("WHOISXML_API_KEY")

    @retry(attempts=3, initial_backoff=1.0)
    def _call_api(self, domain: str) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Missing WHOISXML_API_KEY")
        url = (
            f"https://www.whoisxmlapi.com/whoisserver/WhoisService?apiKey={self.api_key}&domainName={domain}&outputFormat=json"
        )
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.json()

    def run(self, target: str) -> Dict[str, Any]:
        key = f"whoisxml:{target}"

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

        # Normalize to unified dict (simple pass-through here)
        return {"provider": self.provider, "success": True, "data": data, "cached": from_cache}
