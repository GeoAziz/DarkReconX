"""VirusTotal provider module.

This provider queries the VirusTotal API for threat intelligence, including
malware detections, IP/domain reputation, and file analysis results.
It uses environment variable `VT_API_KEY` and honors cache flags via
`DARKRECONX_NO_CACHE` and `DARKRECONX_REFRESH_CACHE`.

Note: VirusTotal v3 API requires a valid API key.
"""

import os
from typing import Any, Dict

import httpx

from core.cache_utils import cache_aware_fetch
from core.module import BaseModule
from core.retry import retry


class VirusTotalModule(BaseModule):
    """VirusTotal threat intelligence provider."""

    def __init__(self):
        super().__init__()
        self.provider = "virustotal"
        self.api_key = os.environ.get("VT_API_KEY")
        self.base_url = "https://www.virustotal.com/api/v3"

    @retry(attempts=3, initial_backoff=1.0)
    def _call_api(self, target: str) -> Dict[str, Any]:
        """Call VirusTotal API to fetch threat data."""
        if not self.api_key:
            raise RuntimeError("Missing VT_API_KEY")

        headers = {"x-apikey": self.api_key}

        # Determine if target is IP or domain
        if target.replace(".", "").isdigit():
            # Looks like an IP
            url = f"{self.base_url}/ip_addresses/{target}"
        else:
            # Looks like a domain
            url = f"{self.base_url}/domains/{target}"

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()

    def run(self, target: str) -> Dict[str, Any]:
        """Execute VirusTotal lookup for the target."""
        key = f"virustotal:{target}"

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

        # Normalize response
        attrs = data.get("data", {}).get("attributes", {})
        last_analysis = attrs.get("last_analysis_stats", {})

        normalized = {
            "reputation": attrs.get("reputation", 0),
            "last_analysis_date": attrs.get("last_analysis_date"),
            "threat_detections": last_analysis.get("malicious", 0),
            "categories": attrs.get("categories", {}),
            "dns_records": attrs.get("dns_records", []),
            "subdomains": attrs.get("subdomains", []) if "subdomains" in attrs else [],
        }

        return {"provider": self.provider, "success": True, "data": normalized, "cached": from_cache}
