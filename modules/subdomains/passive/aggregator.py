import asyncio
from typing import Optional

from modules.subdomains.passive.commoncrawl import get_subdomains as cc_get_subs
from modules.subdomains.passive.crtsh import get_subdomains as crtsh_get_subs
from modules.subdomains.passive.otx import get_subdomains as otx_get_subs
from modules.subdomains.passive.urlscan import get_subdomains as urlscan_get_subs
from modules.subdomains.passive.virustotal import get_subdomains as vt_get_subs
from modules.subdomains.passive.wayback import get_subdomains as wayback_get_subs


async def gather_passive(domain: str, vt_api_key: Optional[str] = None):
    tasks = [
        vt_get_subs(domain, vt_api_key),
        cc_get_subs(domain),
        urlscan_get_subs(domain),
        otx_get_subs(domain),
        crtsh_get_subs(domain),
        wayback_get_subs(domain),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    merged = set()
    for r in results:
        if isinstance(r, list):
            merged |= set(r)
    return sorted(merged)
