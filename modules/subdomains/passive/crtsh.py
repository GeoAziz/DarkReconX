import aiohttp

API_URL = "https://crt.sh/?q=%25.{}&output=json"


async def get_subdomains(domain: str) -> list:
    subs = set()
    url = API_URL.format(domain)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                try:
                    data = await resp.json(content_type=None)
                    for r in data:
                        name = r.get("name_value")
                        if name and domain in name:
                            for sub in name.split("\n"):
                                if sub.endswith(domain):
                                    subs.add(sub.strip())
                except Exception:
                    pass
    return list(subs)
