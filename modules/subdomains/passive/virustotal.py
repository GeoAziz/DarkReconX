from typing import Optional

import aiohttp

API_URL = "https://www.virustotal.com/api/v3/domains/{}/subdomains"
API_KEY = None  # Set your API key here or pass as arg


async def get_subdomains(domain: str, api_key: Optional[str] = None) -> list:
    key = api_key or API_KEY
    if not key:
        return []
    headers = {"x-apikey": key}
    url = API_URL.format(domain)
    subs = set()
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                for item in data.get("data", []):
                    sub = item.get("id")
                    if sub:
                        subs.add(sub)
    return list(subs)
