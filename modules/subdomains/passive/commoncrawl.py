import json

import aiohttp

CC_INDEX = "https://index.commoncrawl.org/CC-MAIN-2023-50-index?url={}&output=json"


async def get_subdomains(domain: str) -> list:
    subs = set()
    url = CC_INDEX.format(f"*.{domain}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                text = await resp.text()
                for line in text.splitlines():
                    if domain in line:
                        try:
                            obj = json.loads(line)
                            host = obj.get("url", "").split("/")[2]
                            if host.endswith(domain):
                                subs.add(host)
                        except Exception:
                            continue
    return list(subs)
